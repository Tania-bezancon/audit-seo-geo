#!/usr/bin/env python3
"""Automatic crawl of a site, slow and resumable.

  python3 crawl.py https://example.com/en OUT_DIR [--delay 3] [--max 400] [--jina] [--urls file.txt]

- Finds pages through robots.txt, the sitemap (index included), then internal links.
- For each page: HTTP code, redirect, response time (TTFB), HTML weight, cache and server headers,
  title, description, robots, lang, canonical, hreflang, H1, H2, glued words (two words split by <br> without a space),
  images and images without alt, JSON-LD, Open Graph, viewport, word count, script count, dates,
  and a JavaScript rendering hint (a page nearly empty without JavaScript: AI crawlers see nothing there).
- For the site: AI crawlers allowed or blocked, llms.txt, compression, security headers, fake 404, www, http.
- Writes OUT_DIR/crawl.jsonl (one line per page, resumes automatically), OUT_DIR/robots.txt, OUT_DIR/sitemap-urls.txt,
  OUT_DIR/summary.json (the report's counters) and OUT_DIR/checks.json (fake 404, www, http).
- Caution: one page every --delay seconds. Some servers block an address after about a hundred fast requests
  (35 min during a real audit). --jina goes through the r.jina.ai reader when blocked.
"""
import argparse, collections, gzip, html, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request
from html.parser import HTMLParser
from fixes import detect_stack, social_links

ap = argparse.ArgumentParser()
ap.add_argument("start"); ap.add_argument("out")
ap.add_argument("--delay", type=float, default=3); ap.add_argument("--max", type=int, default=400)
ap.add_argument("--jina", action="store_true"); ap.add_argument("--urls")
ap.add_argument("--map-host", help="addresses on this host are read here instead: a local copy of a live site lists the live addresses in its sitemap")
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
# the home page is one page: "https://site.com" and "https://site.com/" must not be read twice
START = a.start if urllib.parse.urlparse(a.start).path else a.start + "/"
U = urllib.parse.urlparse(START)
ROOT = f"{U.scheme}://{U.netloc}"
HOST = U.netloc


def here(u):
    p = urllib.parse.urlparse(u)
    return urllib.parse.urlunparse(p._replace(scheme=U.scheme, netloc=HOST)) if a.map_host and p.netloc == a.map_host else u


UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36 audit-seo"


class NoRedir(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *x, **k):
        return None


LAST = {}  # headers and timing of the last response


def get(url, follow=False, timeout=45, headers=None):
    req = urllib.request.Request(("https://r.jina.ai/" + url) if a.jina else url, headers={"User-Agent": UA, **({"X-Return-Format": "html"} if a.jina else {}), **(headers or {})})
    op = urllib.request.build_opener() if follow else urllib.request.build_opener(NoRedir)
    LAST.clear()
    try:
        t0 = time.time()
        r = op.open(req, timeout=timeout)
        LAST.update(ttfb=round((time.time() - t0) * 1000), headers={k.lower(): v for k, v in r.headers.items()})
        if headers and "Accept-Encoding" in headers:
            return r.status, "", None
        body = r.read()
        LAST["kb"] = round(len(body) / 1024)
        if r.headers.get("Content-Encoding") == "gzip" or body[:2] == b"\x1f\x8b":
            body = gzip.decompress(body)
        return r.status, body.decode("utf-8", "replace"), r.headers.get("Location")
    except urllib.error.HTTPError as e:
        return e.code, "", e.headers.get("Location")
    except Exception as e:
        return "ERR", "", str(e)


class P(HTMLParser):
    def __init__(s):
        super().__init__(convert_charrefs=True)
        s.title = ""; s.in_title = False; s.metas = {}; s.links = []; s.hn = []; s.cur = None; s.buf = ""
        s.imgs = []; s.ld = []; s.in_ld = False; s.ldb = ""; s.hrefs = []; s.lang = None; s.text = []; s.skip = 0; s.time = []; s.scripts = 0
        s.ext = {"script": set(), "style": set(), "frame": set()}  # the other hosts the page loads code, styles or frames from

    def handle_starttag(s, t, at):
        at = dict(at)
        if t == "html": s.lang = at.get("lang")
        if t == "title": s.in_title = True
        if t == "meta":
            k = (at.get("name") or at.get("property") or "").lower()
            if k: s.metas[k] = at.get("content", "")
        if t == "link": s.links.append(at)
        if t in ("h1", "h2", "h3"): s.cur = t; s.buf = ""
        if t == "br" and s.cur: s.buf += "<BR>"
        if t == "img": s.imgs.append(at)
        if t == "script" and at.get("type") != "application/ld+json": s.scripts += 1
        src = at.get("src") if t in ("script", "iframe") else at.get("href") if t == "link" and "stylesheet" in (at.get("rel") or "") else None
        if src and src.startswith(("http://", "https://", "//")):
            s.ext["script" if t == "script" else "frame" if t == "iframe" else "style"].add(urllib.parse.urlparse(src if not src.startswith("//") else "https:" + src).netloc)
        if t == "script" and at.get("type") == "application/ld+json": s.in_ld = True; s.ldb = ""
        elif t in ("script", "style", "noscript"): s.skip += 1
        if t == "a" and at.get("href"): s.hrefs.append(at["href"])
        if t == "time": s.time.append(at.get("datetime"))

    def handle_startendtag(s, t, at):
        s.handle_starttag(t, at)

    def handle_endtag(s, t):
        if t == "title": s.in_title = False
        if t == s.cur: s.hn.append((t, re.sub(r"\s+", " ", s.buf).strip())); s.cur = None
        if t == "script" and s.in_ld: s.in_ld = False; s.ld.append(s.ldb)
        elif t in ("script", "style", "noscript") and s.skip: s.skip -= 1

    def handle_data(s, d):
        if s.in_title: s.title += d
        if s.cur: s.buf += d
        if s.in_ld: s.ldb += d
        elif not s.skip: s.text.append(d)


def ld_types(blobs):
    out = []
    for b in blobs:
        try:
            j = json.loads(b)
        except Exception:
            out.append("invalid JSON"); continue
        stack = [j]
        while stack:
            x = stack.pop()
            if isinstance(x, list): stack += x
            elif isinstance(x, dict):
                t = x.get("@type")
                if t: out += t if isinstance(t, list) else [t]
                stack += [v for v in x.values() if isinstance(v, (dict, list))]
    return sorted(set(out))


def page(url):
    code, body, loc = get(url)
    o = {"url": url, "status": code, "location": loc, "ttfb_ms": LAST.get("ttfb"), "html_kb": LAST.get("kb")}
    h = LAST.get("headers", {})
    o.update(cache=h.get("cache-control"), server=h.get("server"), powered_by=h.get("x-powered-by"))
    if code != 200 or not body:
        return o, []
    p = P(); p.feed(body)
    hn = p.hn
    o.update(
        title=html.unescape(p.title.strip()), desc=p.metas.get("description"), robots=p.metas.get("robots"), lang=p.lang,
        canonical=[l.get("href") for l in p.links if "canonical" in (l.get("rel") or "")],
        hreflang=[[l.get("hreflang"), l.get("href")] for l in p.links if l.get("hreflang")],
        h1=[h for t, h in hn if t == "h1"], h2=[h for t, h in hn if t == "h2"][:20],
        glued=[h for _, h in hn if re.search(r"[^\s>]<BR>[^\s<]", h)],
        imgs=len(p.imgs), imgs_noalt=sum(1 for i in p.imgs if not (i.get("alt") or "").strip()),
        ld=ld_types(p.ld), words=len(re.findall(r"\w+", " ".join(p.text))), excerpt=re.sub(r"\s+", " ", html.unescape(" ".join(p.text))).strip()[:420], og_image=p.metas.get("og:image"),
        og_title=p.metas.get("og:title"), og_desc=p.metas.get("og:description"), twitter=p.metas.get("twitter:card"),
        viewport=p.metas.get("viewport"), scripts=p.scripts, published=p.metas.get("article:published_time"), times=[t for t in p.time if t],
        mixed=len(re.findall(r'(?:src|href)="http://', body)),
    )
    # an empty shell has no H1 in its HTML: a short page that has one, such as a legal notice, is simply short
    o["rendu_js_probable"] = o["words"] < 80 and o["scripts"] >= 1 and not o["h1"]
    o["social"] = social_links(p.hrefs)
    o["third_party"] = {k: sorted(h for h in v if h and h != HOST) for k, v in p.ext.items()}
    links = []
    for h in p.hrefs:
        u = here(urllib.parse.urljoin(url, h).split("#")[0])
        if urllib.parse.urlparse(u).netloc == HOST and not re.search(r"\.(pdf|jpe?g|png|gif|svg|webp|zip|mp4|docx?|xlsx?|pptx?)$", u, re.I):
            links.append(u)
    return o, links


# --- robots.txt and sitemap
code, robots, _ = get(ROOT + "/robots.txt", follow=True)
open(os.path.join(a.out, "robots.txt"), "w").write(robots if code == 200 else f"# {code}\n")
maps = [here(m) for m in re.findall(r"(?im)^sitemap:\s*(\S+)", robots)] or [ROOT + "/sitemap.xml"]
seen_maps, sm_urls = set(), []
while maps:
    m = maps.pop(0)
    if m in seen_maps: continue
    seen_maps.add(m); time.sleep(a.delay / 2)
    c, x, _ = get(m, follow=True)
    if c != 200: continue
    locs = [here(l) for l in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", x)]
    if "<sitemapindex" in x: maps += locs
    else: sm_urls += [html.unescape(l) for l in locs]
sm_urls = list(dict.fromkeys(sm_urls))
open(os.path.join(a.out, "sitemap-urls.txt"), "w").write("\n".join(sm_urls))
print(f"robots.txt {code}, sitemap: {len(sm_urls)} addresses")

# --- crawl
# when the cap is reached, the pages in the language asked for come first
lang_path = re.match(r"/[a-z]{2}(-[a-zA-Z]{2})?(/|$)", U.path)
first = lang_path.group(0).rstrip("/") if lang_path else ""
in_lang = lambda u: urllib.parse.urlparse(u).path == first or urllib.parse.urlparse(u).path.startswith(first + "/")
queue = [l.strip() for l in open(a.urls)] if a.urls else [START] + sorted(sm_urls, key=lambda u: bool(first) and not in_lang(u))
done = {}
JL = os.path.join(a.out, "crawl.jsonl")
if os.path.exists(JL):
    for l in open(JL):
        r = json.loads(l); done[r["url"]] = r
with open(JL, "a") as f:
    i = 0
    while queue and len(done) < a.max:
        u = queue.pop(0)
        if u in done: continue
        time.sleep(a.delay)
        o, links = page(u)
        if o["status"] in (403, 429, "ERR") and not a.jina:
            print(f"  {o['status']} on {u}: the server may be blocking this address. Run again later or with --jina.")
        done[u] = o; f.write(json.dumps(o, ensure_ascii=False) + "\n"); f.flush()
        if not a.urls:
            queue += [l for l in links if l not in done and l not in queue]
        i += 1
        if i % 20 == 0: print(f"  {len(done)} pages...")

# --- site-wide checks
checks = {"robots_txt": {"status": code}}
time.sleep(a.delay)
c, _, loc = get(ROOT + "/page-qui-n-existe-pas-audit-404")
checks["fausse_404"] = {"status": c, "location": loc, "verdict": "real 404" if c == 404 else "to check: an unknown address does not return 404"}
alt = U.netloc[4:] if U.netloc.startswith("www.") else "www." + U.netloc
for name, u in [("autre_hote", f"{U.scheme}://{alt}/"), ("http", f"http://{U.netloc}/")]:
    time.sleep(a.delay)
    c, _, loc = get(u)
    checks[name] = {"url": u, "status": c, "location": loc}
# the address people share: the sitemap never lists it when it only redirects
time.sleep(a.delay)
c, _, loc = get(ROOT + "/")
checks["racine"] = {"status": c, "location": loc}
# AI crawlers: blocked by robots.txt?
def blocked(agent):
    groups, cur, take = {}, [], False
    for line in robots.splitlines():
        line = line.split("#")[0].strip()
        if not line: continue
        k, _, v = line.partition(":"); k = k.strip().lower(); v = v.strip()
        if k == "user-agent":
            if take: cur = []
            cur.append(v.lower()); take = False
        elif k in ("disallow", "allow"):
            take = True
            for ua in cur: groups.setdefault(ua, []).append((k, v))
    rules = groups.get(agent.lower(), groups.get("*", []))
    return any(k == "disallow" and v == "/" for k, v in rules) and not any(k == "allow" and v == "/" for k, v in rules)
checks["robots_ia"] = {b: ("blocked" if blocked(b) else "allowed") for b in
                       ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-SearchBot", "Claude-User", "PerplexityBot", "Google-Extended", "Applebot-Extended", "CCBot", "Bingbot", "Googlebot"]}
time.sleep(a.delay)
c, body, _ = get(ROOT + "/llms.txt", follow=True)
checks["llms_txt"] = {"status": c, "lignes": len(body.splitlines()) if c == 200 else 0}
time.sleep(a.delay)
c, body, _ = get(START, follow=True)
checks["stack"] = detect_stack(body, LAST.get("headers"))
time.sleep(a.delay)
get(START, follow=True, headers={"Accept-Encoding": "br, gzip"})
h = LAST.get("headers", {})
checks["accueil"] = {"compression": h.get("content-encoding", "aucune"), "cache": h.get("cache-control"), "server": h.get("server"), "ttfb_ms": LAST.get("ttfb"),
                     "securite": {k: (k in h) for k in ["strict-transport-security", "content-security-policy", "x-content-type-options",
                                                          "x-frame-options", "referrer-policy", "permissions-policy"]}}
json.dump(checks, open(os.path.join(a.out, "checks.json"), "w"), ensure_ascii=False, indent=1)

# --- the report's counters
R = [r for r in done.values() if r.get("status") == 200 and "title" in r]  # a 200 with an empty body has no fields
titles = collections.Counter(r["title"] for r in R)
summary = {
    "pages_ok": len(R), "pages_total": len(done),
    "codes": dict(collections.Counter(str(r["status"]) for r in done.values())),
    "plan_du_site": len(sm_urls), "pages_hors_plan": len([r for r in R if r["url"] not in sm_urls]),
    "titres_longs_65": [r["url"] for r in R if len(r["title"]) > 65],
    "titres_doublons": {t: n for t, n in titles.items() if n > 1},
    "sans_description": [r["url"] for r in R if not (r.get("desc") or "").strip()],
    "h1_different_de_1": [[r["url"], len(r["h1"])] for r in R if len(r["h1"]) != 1],
    "mots_colles": [[r["url"], g] for r in R for g in r["glued"]],
    "images": sum(r["imgs"] for r in R), "images_sans_alt": sum(r["imgs_noalt"] for r in R),
    "lang": dict(collections.Counter(r.get("lang") or "absent" for r in R)),
    "sans_canonical": len([r for r in R if not r["canonical"]]),
    "jsonld_types": dict(collections.Counter(t for r in R for t in r["ld"])),
    "pages_datees": len([r for r in R if r.get("published") or r.get("times")]),
    "pages_maigres_300_mots": [r["url"] for r in R if r["words"] < 300],
    "robots_bloque": re.findall(r"(?im)^disallow:\s*(\S+)", robots),
    "ttfb_median_ms": sorted(r["ttfb_ms"] for r in R if r.get("ttfb_ms") is not None)[len(R) // 2] if R else None,
    "html_lourd_100ko": [r["url"] for r in R if (r.get("html_kb") or 0) > 100],
    "sans_cache": len([r for r in R if not r.get("cache")]),
    "sans_open_graph": [r["url"] for r in R if not r.get("og_image") or not r.get("og_title")],
    "sans_viewport": [r["url"] for r in R if not r.get("viewport")],
    "rendu_js_probable": [r["url"] for r in R if r.get("rendu_js_probable")],
    "contenu_mixte_http": [r["url"] for r in R if r.get("mixed")],
    "version_serveur_affichee": sorted({x for r in R for x in [r.get("server"), r.get("powered_by")] if x and re.search(r"\d", x)}),
    "checks": checks,
}
json.dump(summary, open(os.path.join(a.out, "summary.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: (len(v) if isinstance(v, (list, dict)) and k not in ("codes", "lang", "jsonld_types", "checks", "version_serveur_affichee") else v) for k, v in summary.items()}, ensure_ascii=False, indent=1))
