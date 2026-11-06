#!/usr/bin/env python3
"""What a person can apply on their own site: the platform detected, instructions for it, and files ready to adapt.

  python3 fixes.py CRAWL_DIR OUT_DIR --url URL [--brand NAME] [--lang en|fr]

Also writes OUT_DIR/view.json, the site seen from outside, for audit.json. Writes, in OUT_DIR, only what the crawl shows is needed: the missing security headers in the format of the host, an llms.txt
drafted from the site's own titles and descriptions, an Organization block, and a table of the titles to fix.
Nothing here touches the site. These are drafts: a person reads them before using them, and what the crawl cannot know stays a TODO.
quick.py uses this module by itself; run this script for a full audit."""
import argparse, collections, csv, io, json, os, re
from common import ASSETS

RECIPES = os.path.join(ASSETS, "recipes.json")
HEADER_VALUES = {
    "strict-transport-security": ("Strict-Transport-Security", "max-age=31536000"),
    "x-content-type-options": ("X-Content-Type-Options", "nosniff"),
    "x-frame-options": ("X-Frame-Options", "SAMEORIGIN"),
    "referrer-policy": ("Referrer-Policy", "strict-origin-when-cross-origin"),
    "permissions-policy": ("Permissions-Policy", "camera=(), microphone=(), geolocation=()"),
}
# a policy that blocks too much breaks a site: this one only reports, until someone has read what it would block
CSP = ("Content-Security-Policy-Report-Only", "default-src 'self'; img-src 'self' data: https:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; frame-ancestors 'self'")
SOCIAL = re.compile(r"^https://(?:www\.)?(?:linkedin\.com/(?:in|company)/[^/]+|github\.com/[^/]+|x\.com/[^/]+|twitter\.com/[^/]+|instagram\.com/[^/]+|youtube\.com/@[^/]+|facebook\.com/[^/]+|malt\.fr/profile/[^/]+)/?$", re.I)
SEPARATORS = re.compile(r"\s+[·|–—-]\s+")


def detect_stack(html, headers):
    """Only what a page says openly. Anything else stays unknown, and the instructions stay general."""
    h = {k.lower(): str(v).lower() for k, v in (headers or {}).items()}
    gen = re.search(r'<meta[^>]+name=["\']generator["\'][^>]+content=["\']([^"\']+)', html or "", re.I)
    gen = gen.group(1).lower() if gen else ""
    framework, evidence = None, []
    for name, marks in (("next", ["/_next/", "__NEXT_DATA__"]), ("nuxt", ["/_nuxt/", "__NUXT__"]), ("astro", ["/_astro/", "astro-island"]), ("gatsby", ["___gatsby"]),
                        ("wordpress", ["/wp-content/", "/wp-includes/"]), ("webflow", ["data-wf-site"]), ("shopify", ["cdn.shopify.com", "Shopify.theme"]),
                        ("wix", ["static.wixstatic.com"]), ("squarespace", ["static1.squarespace.com"])):
        hit = next((m for m in marks if m in (html or "")), None)
        if hit or name in gen or (name == "next" and "next.js" in h.get("x-powered-by", "")):
            framework = name
            evidence.append(hit or gen or h.get("x-powered-by"))
            break
    server, host = h.get("server", ""), None
    if "netlify" in server or "x-nf-request-id" in h:
        host = "netlify"
    elif "vercel" in server or "x-vercel-id" in h:
        host = "vercel"
    elif "cloudflare" in server:
        host = "cloudflare"
    elif "github" in server:
        host = "github"
    elif "nginx" in server:
        host = "nginx"
    elif "apache" in server:
        host = "apache"
    if host:
        evidence.append("server: " + server if server else "header")
    return {"framework": framework, "host": host, "evidence": evidence}


def social_links(hrefs):
    return sorted({h.split("?")[0].rstrip("/") for h in hrefs if SOCIAL.match(h.split("?")[0])})


def load_recipes(lang):
    return json.load(open(RECIPES, encoding="utf-8"))[lang]


def recipe(key, lang, stack, brand=""):
    """The instructions of a fix for this platform. Keys may group platforms: "webflow|shopify". Hosted platforms come first, as they decide everything."""
    R = load_recipes(lang).get(key)
    if not R:
        return {}
    stack = stack or {}
    table = {name: v for k, v in R.items() for name in k.split("|")}
    by_host = key in ("C2", "A2")
    hosted = stack.get("framework") if stack.get("framework") in ("wordpress", "webflow", "shopify", "wix", "squarespace") else None
    order = [hosted, stack.get("host"), stack.get("framework")] if by_host else [stack.get("framework"), stack.get("host")]
    found = next((table[n] for n in order if n and n in table), table.get("default", {}))
    return {k: v.replace("{brand}", brand) if isinstance(v, str) else v for k, v in found.items()}


def stack_name(stack, lang):
    names = load_recipes(lang)["_names"]
    parts = [names.get(stack.get(k)) for k in ("framework", "host") if stack and stack.get(k)]
    return " · ".join(p for p in parts if p)


def headers_file(present, host, lang):
    C = load_recipes(lang)["_files"]
    lines = [(n, v) for k, (n, v) in HEADER_VALUES.items() if not (present or {}).get(k)]
    if not (present or {}).get("content-security-policy"):
        lines.append(CSP)
    if not lines:
        return None
    note = C["headers_note"]
    if host in ("netlify", "cloudflare"):
        return "_headers", f"# {note}\n/*\n" + "".join(f"  {n}: {v}\n" for n, v in lines)
    if host == "vercel":
        body = {"headers": [{"source": "/(.*)", "headers": [{"key": n, "value": v} for n, v in lines]}]}
        return "vercel.json", json.dumps(body, indent=2) + "\n"
    if host == "nginx":
        return "security-headers.nginx.conf", f"# {note}\n" + "".join(f'add_header {n} "{v}" always;\n' for n, v in lines)
    if host == "apache":
        return "htaccess-security-headers.txt", f"# {note}\n" + "".join(f'Header always set {n} "{v}"\n' for n, v in lines)
    return "security-headers.txt", f"# {note}\n" + "".join(f"{n}: {v}\n" for n, v in lines)


def home_page(pages, url):
    return next((p for p in pages if p["url"].rstrip("/") == url.rstrip("/")), pages[0] if pages else {})


def llms_file(pages, url, brand, lang):
    home = home_page(pages, url)
    site_lang = (home.get("lang") or "")[:2].lower()
    C = load_recipes(site_lang if site_lang in ("en", "fr") else lang)["_files"]
    same = [p for p in pages if p.get("lang") == home.get("lang")] or pages
    out = [f"# {brand}", "", f"> {home.get('desc') or C['todo_description']}", "", "## " + C["llms_pages"], ""]
    for p in same:
        title = re.sub(r"\s+", " ", p.get("title") or p["url"]).strip()
        title = dedupe_title(title) or title
        out.append(f"- [{title}]({p['url']})" + (f": {p['desc']}" if p.get("desc") else ""))
    return "llms.txt", "\n".join(out) + "\n"


def organization_file(url, brand, desc, social, lang):
    C = load_recipes(lang)["_files"]
    root = re.match(r"https?://[^/]+", url).group(0)
    block = {"@context": "https://schema.org", "@type": "Organization", "name": brand, "url": root, "description": desc or C["todo_description"], "logo": root + "/" + C["todo_logo"], "sameAs": social or [C["todo_profiles"]]}
    return "organization-jsonld.html", '<script type="application/ld+json">\n' + json.dumps(block, ensure_ascii=False, indent=2) + "\n</script>\n"


def dedupe_title(title):
    """"Ceremony · Creative · Ada · Ada" -> "Ceremony · Creative · Ada". Only a name repeated in a row, which cannot be a choice."""
    seps = SEPARATORS.findall(title)
    parts = SEPARATORS.split(title)
    if len(parts) < 2 or not any(a.strip().lower() == b.strip().lower() for a, b in zip(parts, parts[1:])):
        return None
    out, kept = [parts[0]], []
    for sep, part in zip(seps, parts[1:]):
        if part.strip().lower() != out[-1].strip().lower():
            out.append(part)
            kept.append(sep)
    return "".join(a + b for a, b in zip(out, kept + [""]))


def title_problems(pages, lang):
    """[(page, problems, suggestion)] for the pages whose title or description has a defect. The duplicates count within one language."""
    P = load_recipes(lang)["_files"]["problems"]
    seen = collections.Counter((p.get("lang"), p.get("title")) for p in pages)
    rows = []
    for p in pages:
        title, desc, pb = p.get("title") or "", p.get("desc") or "", []
        fixed = dedupe_title(title)
        if not title:
            pb.append(P["no_title"])
        if fixed:
            pb.append(P["repeated"])
        if len(fixed or title) > 65:
            pb.append(P["long"])
        if title and seen[(p.get("lang"), title)] > 1:
            pb.append(P["duplicate"])
        if not desc:
            pb.append(P["no_description"])
        elif len(desc) > 165:
            pb.append(P["long_description"])
        if pb:
            rows.append((p, pb, fixed or ""))
    return rows


def titles_file(pages, lang):
    rows = title_problems(pages, lang)
    if not rows:
        return None, rows
    head = load_recipes(lang)["_files"]["titles_head"]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(head)
    for p, pb, fixed in rows:
        w.writerow([p["url"], p.get("title") or "", len(p.get("title") or ""), "; ".join(pb), fixed, len(p.get("desc") or "")])
    return ("titles-to-fix.csv", buf.getvalue()), rows


def write_fixes(crawl, url, brand, lang, out_dir):
    """{criterion: {"file", "content"}} for what the measures show is missing, also written to OUT_DIR/fixes."""
    pages, stack, files = crawl.get("pages") or [], crawl.get("stack") or {}, {}
    made = headers_file(crawl.get("headers_present"), stack.get("host"), lang) if crawl.get("headers_present") is not None else None
    if made:
        files["C2"] = made
    if pages and crawl.get("llms") != 200:
        files["F2"] = llms_file(pages, url, brand, lang)
    if pages and not any(re.search(r"Organization|Corporation|LocalBusiness", t) for t in crawl.get("jsonld", [])):
        files["F1"] = organization_file(url, brand, home_page(pages, url).get("desc"), crawl.get("social"), lang)
    if pages:
        made, _ = titles_file(pages, lang)
        if made:
            files["D1"] = made
    folder = os.path.join(out_dir, "fixes")
    if files:
        os.makedirs(folder, exist_ok=True)
    result = {}
    for key, (name, content) in files.items():
        open(os.path.join(folder, name), "w", encoding="utf-8-sig" if name.endswith(".csv") else "utf-8", newline="").write(content)
        result[key] = {"file": "fixes/" + name, "content": content}
    return result


if __name__ == "__main__":
    from quick import measures_from_crawl
    ap = argparse.ArgumentParser(description="Files ready to adapt, from a crawl")
    ap.add_argument("crawl"); ap.add_argument("out"); ap.add_argument("--url", required=True); ap.add_argument("--brand", default=""); ap.add_argument("--lang", choices=["en", "fr"], default="en")
    a = ap.parse_args()
    crawl = measures_from_crawl(a.crawl, a.url)
    made = write_fixes(crawl, a.url, a.brand or re.sub(r"^www\.", "", a.url.split("/")[2]), a.lang, a.out)
    os.makedirs(a.out, exist_ok=True)
    json.dump({"stack": crawl.get("stack"), "view": crawl.get("view")}, open(os.path.join(a.out, "view.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n".join([v["file"] for v in made.values()] + ["view.json: copy stack to site.stack and view to the view key of audit.json"]))
