#!/usr/bin/env python3
"""The quick audit: about 15 minutes, no browser and no API key required.

  python3 quick.py measure URL OUT_DIR [--brand NAME] [--lang en|fr] [--theme NAME] [--max 25] [--delay 1] [--offline]
  python3 quick.py build OUT_DIR/quick.json [OUT_DIR] [--lang en|fr]
  python3 quick.py check AUDIT.json [B1,F3] [--services]

measure  crawls at most --max pages with crawl.py, then asks three public services (PageSpeed, Mozilla Observatory,
         Wikidata; skipped with --offline). A service that does not answer is noted as unavailable, the audit goes on.
         Writes OUT_DIR/quick.json. Set PAGESPEED_API_KEY to avoid PageSpeed's shared quota.
build    scores the fixed grid from quick.json, then writes a single-file HTML report and the to-do as Markdown and CSV.
         It always recomputes the score, so quick.json can be edited and rebuilt at will.

check    reads the site again (quick.json or audit.json) and writes in the file, for each fix, what a machine can conclude. build shows it on the cards.
         It changes neither the measures nor the score: a new audit and compare.py measure progress.

Claude completes quick.json between the two steps: judged criteria, AI panel, task wording (references/quick-mode.md).
A criterion nobody could check is NV: excluded from the score, never guessed. The score is labelled provisional."""
import argparse, base64, collections, csv, datetime, html, io, tempfile, json, os, re, shutil, statistics, subprocess, sys, urllib.error, urllib.parse, urllib.request
import fixes
from common import ASSETS, HOSTED, UI, apply_recheck, repair_block, repair_kind, repair_line, open_questions, task_questions, task_state, date_label, find_chrome, first_html, fix_html, fix_script, font_faces, grid_gain, looks_html, md_details, progress_html, signed_gain, soft_domain, task_marks, view_html, who_html, fmt_score, grid_scores, plural, report_lang, theme_css, translator

HERE = os.path.dirname(os.path.abspath(__file__))
UA = "Mozilla/5.0 (compatible; audit-seo-geo; +https://github.com/Tania-bezancon/audit-seo-geo)"
LETTERS = "ABCDEF"
GRID = [f"{L}{i}" for L in LETTERS for i in range(1, 6)]
LIGHTHOUSE = "lighthouse@13.6.0"
ANSWER_BOTS = ["OAI-SearchBot", "ChatGPT-User", "Claude-SearchBot", "Claude-User", "PerplexityBot"]  # these decide citations; blocking training crawlers (GPTBot, ClaudeBot, CCBot) is a choice, not a defect
ABOUT_RE = re.compile(r"/(about|about-us|company|who-we-are|a-propos|qui-sommes-nous|societe)(/|\.html?)?$", re.I)


def fetch_json(url, data=None, timeout=120):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def unavailable(e):
    if isinstance(e, urllib.error.HTTPError):
        try:
            detail = json.load(e).get("message", e.reason)  # Observatory explains its refusals in the body
        except Exception:
            detail = e.reason
        return {"status": "unavailable", "reason": f"{e.code} {detail}"[:160]}
    return {"status": "unavailable", "reason": str(e)[:160]}


def pagespeed(url):
    """The API first: it alone has visitors' real data. Without a key it usually refuses, and Lighthouse then runs here."""
    q = {"url": url, "strategy": "mobile", "category": ["performance", "accessibility"]}
    if os.environ.get("PAGESPEED_API_KEY"):
        q["key"] = os.environ["PAGESPEED_API_KEY"]
    try:
        return parse_pagespeed(fetch_json("https://www.googleapis.com/pagespeedonline/v5/runPagespeed?" + urllib.parse.urlencode(q, doseq=True), timeout=90))
    except Exception as e:
        api = unavailable(e)
    print("PageSpeed refused, measuring here with Lighthouse (its first run downloads it with npx)...")
    local = lighthouse(url)
    return local if local["status"] == "ok" else {"status": "unavailable", "reason": f"PageSpeed: {api['reason']}; Lighthouse: {local['reason']}"[:200]}


def find_npx():
    return shutil.which("npx") or next((p for p in (os.path.expanduser("~/.local/node/bin/npx"), "/opt/homebrew/bin/npx", "/usr/local/bin/npx") if os.path.exists(p)), None)


def lighthouse(url):
    """The engine of PageSpeed, on this machine with the local Chrome: a simulated phone, no key, no real-user data."""
    chrome, npx = find_chrome(), find_npx()
    if not chrome or not npx:
        return {"status": "unavailable", "reason": "it needs Chrome and Node.js"}
    env = {**os.environ, "CHROME_PATH": chrome, "PATH": os.path.dirname(npx) + os.pathsep + os.environ.get("PATH", "")}
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "lh.json")
        try:
            r = subprocess.run([npx, "--yes", LIGHTHOUSE, url, "--quiet", "--output=json", f"--output-path={out}", "--only-categories=performance,accessibility", "--chrome-flags=--headless=new --disable-gpu"],
                               env=env, cwd=tmp, capture_output=True, text=True, timeout=300)
        except subprocess.TimeoutExpired:
            return {"status": "unavailable", "reason": "no result after 5 minutes"}
        if not os.path.exists(out):
            return {"status": "unavailable", "reason": (r.stderr.strip().splitlines() or ["no result"])[-1][:120]}
        report = json.load(open(out, encoding="utf-8"))
    if report.get("runtimeError"):
        return {"status": "unavailable", "reason": str(report["runtimeError"].get("message"))[:120]}
    return {**parse_pagespeed({"lighthouseResult": report}), "source": "lighthouse"}


def parse_pagespeed(j):
    cats = j.get("lighthouseResult", {}).get("categories", {})
    score = lambda k: round(cats[k]["score"] * 100) if cats.get(k, {}).get("score") is not None else None
    out = {"status": "ok", "source": "api", "perf": score("performance"), "a11y": score("accessibility")}
    m = j.get("loadingExperience", {}).get("metrics", {})
    pct = lambda k: m.get(k, {}).get("percentile")
    if pct("LARGEST_CONTENTFUL_PAINT_MS") is not None:
        cls = pct("CUMULATIVE_LAYOUT_SHIFT_SCORE")
        out["field"] = {"lcp": pct("LARGEST_CONTENTFUL_PAINT_MS"), "inp": pct("INTERACTION_TO_NEXT_PAINT"), "cls": cls / 100 if cls is not None else None}
    return out


def observatory(host):
    try:
        j = fetch_json("https://observatory-api.mdn.mozilla.net/api/v2/scan?host=" + urllib.parse.quote(host), data=b"", timeout=60)
    except Exception as e:
        return unavailable(e)
    if j.get("error") or not j.get("grade"):
        return {"status": "unavailable", "reason": str(j.get("message") or j.get("error"))[:120]}
    return {"status": "ok", "grade": j["grade"], "score": j.get("score")}


def wikidata(brand, lang):
    q = urllib.parse.urlencode({"action": "wbsearchentities", "search": brand, "language": lang, "uselang": lang, "format": "json", "limit": 3})
    try:
        j = fetch_json("https://www.wikidata.org/w/api.php?" + q, timeout=30)
    except Exception as e:
        return unavailable(e)
    return {"status": "ok", "hits": wikidata_hits(j.get("search", []), brand)}


def wikidata_hits(results, brand):
    """Exact label or alias first, else a label that starts with the brand ("Mozilla Corporation"). Only candidates: a person checks them."""
    b = brand.lower()
    hit = lambda x: {"id": x["id"], "label": x.get("label", ""), "description": x.get("description", "")}
    exact = [hit(x) for x in results if b in (x.get("label", "").lower(), x.get("match", {}).get("text", "").lower())]
    return exact or [hit(x) for x in results if x.get("label", "").lower().startswith(b + " ")]


def resolve(url):
    """The address after redirects, because crawl.py does not follow them from its first page."""
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30) as r:
            return r.geturl()
    except Exception:
        return url


def measures_from_crawl(crawl_dir, start):
    S = json.load(open(os.path.join(crawl_dir, "summary.json"), encoding="utf-8"))
    pages = [json.loads(l) for l in open(os.path.join(crawl_dir, "crawl.jsonl"), encoding="utf-8")]
    ok = [p for p in pages if p.get("status") == 200 and "title" in p]
    C = S["checks"]
    home = next((p for p in ok if p["url"].rstrip("/") == start.rstrip("/")), ok[0] if ok else {})
    glued = {u for u, _ in S["mots_colles"]}
    h1_bad = {u for u, _ in S["h1_different_de_1"]}
    # a project name can stay the same in two languages: only a duplicate within one language is a defect
    per_lang = collections.Counter((p.get("lang"), p["title"]) for p in ok)
    titles_dup = {p["url"] for p in ok if per_lang[(p.get("lang"), p["title"])] > 1}
    repeated = {p["url"] for p in ok if fixes.dedupe_title(p["title"])}
    root = re.sub(r"^www\.", "", urllib.parse.urlparse(start).netloc)
    poorest = min((p for p in ok if p is not home), key=lambda p: p.get("words", 0), default=None)
    seen = [home] + ([poorest] if poorest and poorest.get("words", 0) < 300 else [])
    view = {"google": {"url": home.get("url", start), "title": home.get("title"), "desc": home.get("desc")},
            "share": {"domain": root, "title": home.get("og_title"), "desc": home.get("og_desc"), "image": home.get("og_image")},
            "pages": [{"url": p["url"], "words": p.get("words", 0), "excerpt": p.get("excerpt", "")} for p in seen]}
    d1_bad = set(S["sans_description"]) | set(S["titres_longs_65"]) | titles_dup | set(S["sans_open_graph"]) | repeated
    err = [p for p in pages if p.get("status") == "ERR" or (isinstance(p.get("status"), int) and p["status"] >= 400)]
    sec = C["accueil"]["securite"]
    return {
        "pages_ok": len(ok), "pages_total": len(pages), "errors": len(err), "error_urls": [p["url"] for p in err][:5],
        "robots_status": C["robots_txt"]["status"],
        "googlebot": C["robots_ia"]["Googlebot"], "sitemap": S["plan_du_site"], "noindex": sum("noindex" in (p.get("robots") or "").lower() for p in ok),
        "home_noindex": "noindex" in (home.get("robots") or "").lower(),
        "fake_404_status": C["fausse_404"]["status"], "http": C["http"], "other_host": C["autre_hote"], "no_canonical": S["sans_canonical"],
        "languages": len(S["lang"]), "no_hreflang": sum(not p.get("hreflang") for p in ok),
        "js_pages": len(S["rendu_js_probable"]), "home_js": bool(home.get("rendu_js_probable")), "mixed": len(S["contenu_mixte_http"]),
        "no_viewport": len(S["sans_viewport"]), "https": start.startswith("https://"), "hsts": sec["strict-transport-security"],
        "headers": sum([sec["content-security-policy"], sec["x-content-type-options"], sec["x-frame-options"], sec["referrer-policy"], sec["permissions-policy"]]),
        "server_version": S["version_serveur_affichee"], "compression": C["accueil"]["compression"], "home_cache": C["accueil"]["cache"],
        "ttfb_median": S["ttfb_median_ms"] if S["ttfb_median_ms"] is not None else (statistics.median([p["ttfb_ms"] for p in ok]) if ok else None),
        "d1_bad": len(d1_bad), "no_description": len(S["sans_description"]), "long_titles": len(S["titres_longs_65"]), "dup_titles": len(titles_dup), "repeated_titles": len(repeated), "no_og": len(S["sans_open_graph"]),
        "d2_bad": len(h1_bad | glued), "jsonld": sorted(S["jsonld_types"]), "ai_bots": {b: C["robots_ia"][b] for b in ANSWER_BOTS}, "llms": C["llms_txt"]["status"],
        "view": view, "headers_present": sec, "stack": C.get("stack") or {}, "social": home.get("social") or [],
        "pages": [{"url": p["url"], "title": p["title"], "desc": p.get("desc") or "", "lang": p.get("lang")} for p in ok],
        "root": C.get("racine"), "js_urls": S["rendu_js_probable"][:5],
        "about_page": next((p["url"] for p in ok if ABOUT_RE.search(urllib.parse.urlparse(p["url"]).path)), None),
    }


def capture_view(view, out):
    """What a visitor sees, next to what a robot reads, and the image the site shows when shared. Optional: without Chrome or Pillow the report does without."""
    os.makedirs(os.path.join(out, "crawl"), exist_ok=True)
    try:
        from PIL import Image
    except ImportError:
        return
    chrome = find_chrome()
    for i, p in enumerate(view["pages"]):
        if not chrome:
            break
        png = os.path.join(out, "crawl", f"shot-{i}.png")
        with tempfile.TemporaryDirectory() as prof:
            try:
                subprocess.run([chrome, "--headless=new", "--disable-gpu", f"--user-data-dir={prof}", "--window-size=1280,800", "--hide-scrollbars", "--virtual-time-budget=8000", f"--screenshot={png}", p["url"]],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
            except (subprocess.SubprocessError, OSError):
                continue
        if os.path.exists(png):
            name = os.path.join("crawl", f"shot-{i}.jpg")
            Image.open(png).convert("RGB").resize((900, 562)).save(os.path.join(out, name), quality=72, optimize=True)
            os.remove(png)
            p["image"] = name
    share = view["share"]
    if share.get("image"):
        try:
            url = urllib.parse.urljoin(view["google"]["url"], share["image"])
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=20) as r:
                raw = r.read(6_000_000)
            path = os.path.join(out, "crawl", "share.jpg")
            img = Image.open(io.BytesIO(raw)).convert("RGB")
            share["width"], share["height"] = img.size
            img.thumbnail((800, 800))
            img.save(path, quality=74, optimize=True)
            share["image"] = os.path.join("crawl", "share.jpg")
        except Exception:
            share["image"] = None


def cmd_measure(a):
    start = resolve(a.url)
    if start != a.url:
        print(f"{a.url} redirects to {start}: using that address")
    crawl_dir = os.path.join(a.out, "crawl")
    subprocess.run([sys.executable, os.path.join(HERE, "crawl.py"), start, crawl_dir, "--delay", str(a.delay), "--max", str(a.max)], check=True, stdout=subprocess.DEVNULL)
    m = {"crawl": measures_from_crawl(crawl_dir, start)}
    if not a.offline and m["crawl"]["pages_ok"]:
        capture_view(m["crawl"]["view"], a.out)
    if not m["crawl"]["pages_ok"]:
        sys.exit(f"no page could be read at {start}: the server may block automatic requests. Try the full audit with a browser, or crawl.py --jina.")
    U = urllib.parse.urlparse(start)
    today = datetime.date.today().isoformat()
    brand = a.brand or ""
    lang = a.lang or "en"
    if a.offline:
        m["psi"] = m["observatory"] = m["wikidata"] = {"status": "unavailable", "reason": "--offline"}
    else:
        print("asking PageSpeed, Mozilla Observatory and Wikidata...")
        m["psi"] = pagespeed(start)
        m["observatory"] = observatory(U.hostname)
        m["wikidata"] = wikidata(brand, lang) if brand else {"status": "unavailable", "reason": "no --brand"}
    domain = re.sub(r"^www\.", "", U.netloc)
    Q = {"site": {"url": start, "domain": domain, "brand": brand or domain, "date": today, "report_lang": lang, "theme": a.theme, "max_pages": a.max},
         "measures": m, "judged": {}, "panel": None, "task_overrides": {}, "drop_tasks": [], "headline": "", "good": [], "bad": []}
    path = os.path.join(a.out, "quick.json")
    json.dump(Q, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if not brand:
        print(f"no brand given: read the first page, then run: quick.py brand {path} \"The exact name\"")
    print(f"{m['crawl']['pages_ok']} pages read. PageSpeed: {m['psi']['status']}. Observatory: {m['observatory']['status']}. Wikidata: {m['wikidata']['status']}.")
    print("written:", path)


def share(n, total):
    return n / total if total else 0


def tier(ratio):
    return "2" if ratio <= 0.1 else "1" if ratio <= 0.5 else "0"


def root_problem(c):
    """The address of the site itself: a redirect that says nowhere to go stops every robot, and only a browser carries on."""
    r = c.get("root") or {}
    st = r.get("status")
    if st in (301, 302, 303, 307, 308) and not r.get("location"):
        return "redirect", st
    if st == "ERR" or (isinstance(st, int) and st >= 400):
        return "error", st
    return None


def auto_scores(m, panel, E):
    """{criterion: (score, evidence, source)} from the measures. Only what a machine can really conclude: B4 and B5 can
    fail automatically but cannot pass (a viewport tag does not prove the page fits a phone), so a pass there stays NV."""
    c, psi, obs, wd = m["crawl"], m["psi"], m["observatory"], m["wikidata"]
    pages = c["pages_ok"]
    out = {}

    def put(code, score, key, **kw):
        s = E[key]
        for k, v in kw.items():
            s = s.replace("{" + k + "}", str(v))
        out[code] = (score, s, "auto")

    gb_ok = c["googlebot"] != "blocked"
    put("A1", "0" if not gb_ok or c["home_noindex"] else "1" if not c["sitemap"] or c["noindex"] else "2", "A1",
        robots=c["robots_status"], gb=E.get("bot_" + str(c["googlebot"]), c["googlebot"]), sm=c["sitemap"], ni=c["noindex"])
    h, o = c["http"], c["other_host"]
    http_ok = h["status"] in (301, 308) and str(h.get("location") or "").startswith("https://")
    http_soft = h["status"] in (302, 307)
    other_ok = o["status"] == "ERR" or o["status"] in (301, 308)
    served_twice = h["status"] == 200 and c["https"] or o["status"] == 200
    # several languages without hreflang: Google and AI cannot tell that the pages are translations of each other
    no_hreflang = c.get("languages", 1) > 1 and share(c.get("no_hreflang", 0), pages) > 0.1
    put("A2", "2" if http_ok and other_ok and share(c["no_canonical"], pages) <= 0.1 and not no_hreflang else "0" if served_twice and share(c["no_canonical"], pages) > 0.5 else "1", "A2",
        http=h["status"], alt=urllib.parse.urlparse(o["url"]).netloc, alth=E["no_answer"] if o["status"] == "ERR" else o["status"], nc=c["no_canonical"], pages=pages,
        hl=E["A2_hreflang"].replace("{n}", str(c.get("no_hreflang", 0))).replace("{langs}", str(c.get("languages", 1))) if no_hreflang else "")
    real_404 = c["fake_404_status"] == 404
    err_ratio = share(c["errors"], c["pages_total"])
    root = root_problem(c)
    a3 = "2" if real_404 and not c["errors"] else "0" if not real_404 and err_ratio > 0.1 else "1"
    put("A3", "1" if root and a3 == "2" else a3, "A3", err=c["errors"], total=c["pages_total"], fake=c["fake_404_status"],
        root=E["A3_root_" + root[0]].replace("{s}", str(root[1])) if root else "")
    put("A4", "0" if c["home_js"] else "2" if not c["js_pages"] else "1", "A4", js=c["js_pages"], pages=pages, home=E["A4_bad"] if c["home_js"] else E["A4_ok"])
    if psi["status"] == "ok":
        f = psi.get("field")
        if f and f.get("lcp") is not None and f.get("inp") is not None and f.get("cls") is not None:
            poor = f["lcp"] > 4000 or f["inp"] > 500 or f["cls"] > 0.25
            good = f["lcp"] < 2500 and f["inp"] < 200 and f["cls"] < 0.1
            put("B1", "2" if good else "0" if poor else "1", "B1", lcp=f["lcp"], inp=f["inp"], cls=f["cls"])
        if psi.get("perf") is not None:
            put("B2", "2" if psi["perf"] >= 90 else "1" if psi["perf"] >= 50 else "0", "B2_local" if psi.get("source") == "lighthouse" else "B2", perf=psi["perf"])
        if psi.get("a11y") is not None:
            put("E5", "2" if psi["a11y"] >= 90 else "1" if psi["a11y"] >= 70 else "0", "E5_local" if psi.get("source") == "lighthouse" else "E5", a11y=psi["a11y"])
    if c["mixed"]:
        put("B4", "0", "B4", n=c["mixed"])
    if c["no_viewport"]:
        put("B5", "0", "B5", n=c["no_viewport"])
    put("C1", "0" if not c["https"] else "2" if c["hsts"] else "1", "C1", scheme="https" if c["https"] else "http", hsts=E["C1_yes"] if c["hsts"] else E["C1_no"])
    obs_txt = ""
    if obs["status"] == "ok":
        obs_txt = E["C2_obs"].replace("{grade}", str(obs["grade"])).replace("{score}", str(obs.get("score")))
    put("C2", "2" if c["headers"] >= 4 and not c["server_version"] else "1" if c["headers"] >= 2 else "0", "C2",
        n=c["headers"], ver=", ".join(c["server_version"]) or E["C2_none"], obs=obs_txt)
    compressed = c["compression"] not in ("aucune", "none", None)
    put("C3", "2" if compressed and c["home_cache"] else "1" if compressed or c["home_cache"] else "0", "C3",
        comp=c["compression"] if compressed else E["C3_none"], cache=c["home_cache"] or E["C3_none"])
    if c["ttfb_median"] is not None:
        put("C4", "2" if c["ttfb_median"] < 800 else "1" if c["ttfb_median"] < 1800 else "0", "C4", ms=c["ttfb_median"])
    put("D1", tier(share(c["d1_bad"], pages)), "D1", bad=c["d1_bad"], pages=pages, nd=c["no_description"], rt=c.get("repeated_titles", 0), lt=c["long_titles"], dt=c["dup_titles"], og=c["no_og"])
    put("D2", tier(share(c["d2_bad"], pages)), "D2", bad=c["d2_bad"], pages=pages)
    types = [t for t in c["jsonld"] if t != "invalid JSON"]
    org = any(re.search(r"Organization|Corporation|LocalBusiness", t) for t in types)
    if types:
        put("F1", "2" if org and len(types) > 1 else "1", "F1", types=", ".join(types[:8]))
    else:
        put("F1", "0", "F1_none")
    blocked = [b for b, v in c["ai_bots"].items() if v == "blocked"]
    put("F2", "0" if blocked else "2" if c["llms"] == 200 else "1", "F2", blocked=", ".join(blocked) or E["F2_none"], llms=c["llms"])
    if wd["status"] == "ok":
        hit = wd["hits"][0] if wd["hits"] else None
        wd_txt = E["F3_candidates"].replace("{label}", hit["label"]).replace("{id}", hit["id"]) if hit else E["F3_missing"]
        put("F3", "2" if hit and c["about_page"] else "1" if hit or c["about_page"] else "0", "F3", about=E["F3_found"] if c["about_page"] else E["F3_missing"], wd=wd_txt)
    else:
        put("F3", "1" if c["about_page"] else "0", "F3", about=E["F3_found"] if c["about_page"] else E["F3_missing"], wd=E["F3_noquery"])
    if panel:
        bq = str(panel.get("brand_question", ""))
        ans = [x for a in panel.get("assistants", []) if a.get("kind", "assistant") == "assistant" for x in a["answers"] if str(x["q"]) != bq]
        if ans:
            n = sum(1 for x in ans if x["cited"])
            put("F5", "2" if share(n, len(ans)) >= 0.5 else "1" if n else "0", "F5", n=n, total=len(ans))
            out["F5"] = (*out["F5"][:2], "panel")
    return out


def score_rows(Q, QL):
    auto = auto_scores(Q["measures"], Q.get("panel"), QL["ev"])
    rows, errs = [], []
    for code in Q.get("judged", {}):
        if code not in GRID:
            errs.append(f"judged: unknown criterion {code}")
    for code in GRID:
        j = Q.get("judged", {}).get(code)
        if j:
            score, evidence = j
            if str(score) not in ("0", "1", "2", "NV"):
                errs.append(f"judged {code}: the score must be 0, 1, 2 or NV")
            if not str(evidence).strip():
                errs.append(f"judged {code}: the evidence is empty")
            rows.append([code, QL["criteria"][code], str(score), evidence, "judged"])
        elif code in auto:
            rows.append([code, QL["criteria"][code], *auto[code]])
        else:
            rows.append([code, QL["criteria"][code], "NV", "", "none"])
    return rows, errs


def build_tasks(Q, rows, QL, limit=10):
    """The fixes for the criteria scored 0 or 1, most urgent first. task_overrides rewrites one for the site, or adds one (key outside the grid)."""
    over, drop = Q.get("task_overrides", {}), set(Q.get("drop_tasks", []))
    cands, errs = [], []
    for code, _, score, _, _ in rows:
        if score not in ("0", "1") or code in drop or (code not in QL["tasks"] and code not in over):
            continue
        t = {**QL["tasks"].get(code, {}), **over.get(code, {})}
        # a broken address of the site itself stays urgent, whatever the rest of the site does
        if score == "1" and t.get("prio") == 1 and "prio" not in over.get(code, {}) and not (code == "A3" and root_problem(Q.get("measures", {}).get("crawl", {}))):
            t["prio"] = 2
        cands.append((t.get("prio", 2), int(score), code, t))
    for key, t in over.items():
        if key not in GRID:
            cands.append((t.get("prio", 2), 0, key, t))
    for _, _, key, t in cands:
        for f in ("lane", "name", "what", "check"):
            if not t.get(f):
                errs.append(f"task {key}: {f} is missing")
        if t.get("lane") not in ("C", "F", "B"):
            errs.append(f"task {key}: the lane must be C, F or B")
        if t.get("prio", 2) not in (1, 2, 3):
            errs.append(f"task {key}: the priority must be 1, 2 or 3")
    if errs:
        return [], 0, errs
    cands.sort(key=lambda x: x[:3])
    counts, shown = {}, []
    for prio, _, key, t in cands[:limit]:
        counts[t["lane"]] = counts.get(t["lane"], 0) + 1
        shown.append({**t, "prio": prio, "key": key, "code": f"{t['lane']}{counts[t['lane']]}"})
    return shown, max(0, len(cands) - len(shown)), []


def enrich_tasks(tasks, Q, files, lang):
    """Instructions for the platform, the ready file and a real before and after. What task_overrides says wins."""
    S, crawl = Q["site"], Q["measures"]["crawl"]
    stack = S.get("stack") or crawl.get("stack") or {}
    E = json.load(open(os.path.join(ASSETS, "quick.json"), encoding="utf-8"))[lang]["ev"]
    for t in tasks:
        for k, v in fixes.recipe(t["key"], lang, stack, S.get("brand", "")).items():
            t.setdefault(k, v)
        root = root_problem(crawl) if t["key"] == "A3" else None
        if root and "what" not in Q.get("task_overrides", {}).get("A3", {}):
            only_root = not crawl.get("errors") and crawl.get("fake_404_status") == 404
            t["what"] = E["A3_what_" + root[0]].replace("{s}", str(root[1])) + ("" if only_root else " " + t["what"])
            if only_root:
                t["name"], t["check"] = E["A3_root_name"], E["A3_root_check"]
            for k, v in fixes.recipe("A3_root", lang, stack, S.get("brand", "")).items():
                t.setdefault(k, v)
        if t["key"] in files:
            t.setdefault("file", files[t["key"]]["file"])
            t.setdefault("file_content", files[t["key"]]["content"])
        if t["key"] == "D1" and not t.get("before"):
            for p, _, fixed in fixes.title_problems(crawl.get("pages") or [], lang):
                if fixed:
                    t["before"], t["after"] = {"url": p["url"], "title": p["title"]}, {"url": p["url"], "title": fixed}
                    break
    return stack


def esc(t):
    return html.escape(str(t), quote=False)


def inline(t):
    t = esc(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    return re.sub(r"`(.+?)`", r"<code>\1</code>", t)


def pill(kind, t):
    return f'<span class="pill {kind}">{esc(t)}</span>'


def cmd_build(a):
    Q = json.load(open(a.quick, encoding="utf-8"))
    out_dir = a.out or os.path.dirname(os.path.abspath(a.quick))
    S = Q["site"]
    LANG = report_lang(S, a.lang)
    T = translator(LANG)
    SEP = T("sep")
    QL = json.load(open(os.path.join(ASSETS, "quick.json"), encoding="utf-8"))[LANG]
    DEF = json.load(open(os.path.join(ASSETS, f"defaults.{LANG}.json"), encoding="utf-8"))
    rows, errs = score_rows(Q, QL)
    tasks, _, terrs = build_tasks(Q, rows, QL, limit=None)
    errs += terrs
    if errs:
        sys.exit("inconsistent quick.json:\n- " + "\n- ".join(errs))
    files = fixes.write_fixes(Q["measures"]["crawl"], S["url"], S.get("brand", S["domain"]), LANG, out_dir)
    stack = enrich_tasks(tasks, Q, files, LANG)
    cats, overall = grid_scores(rows, LETTERS)
    checked = sum(1 for r in rows if r[2] != "NV")
    if overall is None:
        sys.exit("no criterion could be checked: nothing to report")
    score = fmt_score(overall, LANG)
    date = date_label(S["date"], LANG)
    n_p1 = sum(1 for t in tasks if t["prio"] == 1)
    TH, css = theme_css(S.get("theme", "signature"))
    fonts = font_faces(TH)
    lanes = {k: n for k, n, _, _ in DEF["voies"]}
    prio_label = {n: (c, l) for n, c, l, _ in DEF["priorites"]}
    scores = looks_html(rows, score, T, LANG, "criteres")
    base_dir = os.path.dirname(os.path.abspath(a.quick))

    def embed(path):
        """The report stays one file: stored images go inside it."""
        full = os.path.join(base_dir, path) if path else ""
        if not os.path.isfile(full):
            return None
        return "data:image/jpeg;base64," + base64.b64encode(open(full, "rb").read()).decode()
    view = view_html(Q["measures"]["crawl"].get("view"), T, inline, esc, LANG, embed)
    rc_block = Q.get("recheck") or {}
    recheck = rc_block.get("results", {})
    rc_date = date_label(rc_block["date"], LANG) if rc_block.get("date") else ""
    rows_now = apply_recheck(rows, recheck)
    for t in tasks:
        t["criterion"] = t.get("criterion") or (t["key"] if t["key"] in GRID else None)
        t["gain"] = grid_gain(rows_now, t["criterion"]) if t["criterion"] else 0
    # Claude can choose them; otherwise the most urgent
    chosen = [t for key in Q.get("first", []) for t in tasks if t["key"] == key]
    first_codes = chosen or tasks[:3]
    headline = Q.get("headline") or QL["headline"].replace("{score}", score).replace("{n}", str(checked)).replace("{p1}", str(n_p1))
    good = Q.get("good") or [r[1] for r in rows if r[2] == "2"][:4]
    bad = Q.get("bad") or [r[1] for r in rows if r[2] == "0"][:4]
    ul = lambda xs: "<ul>" + "".join(f"<li>{inline(x)}</li>" for x in xs) + "</ul>"
    summary = ""
    if good or bad:
        summary = f'<section><div class="head"><h2>{T("quick_summary_title")}</h2></div><div class="grid2">' + \
            (f'<div class="card good"><h3>{T("good")}</h3>{ul(good)}</div>' if good else "") + (f'<div class="card bad"><h3>{T("bad")}</h3>{ul(bad)}</div>' if bad else "") + "</div></section>"

    repair = Q.get("repair") or {}
    for t in tasks:
        t["kind"] = repair_kind(t)
        t["questions"] = open_questions({**t, "questions": task_questions(t, LANG, T)}, repair.get("tasks", {}).get(t["code"]))
    top, rest = tasks[:10], tasks[10:]

    def task_html(t):
        pr = prio_label[t["prio"]][0]
        result = recheck.get(t["criterion"]) if t.get("criterion") else None
        entry = repair.get("tasks", {}).get(t["code"])
        box, marks = task_marks(t["code"], t.get("criterion"), t.get("gain"), result, T, LANG, rc_date, entry, None if stack.get("framework") in HOSTED else t["kind"])
        rc = f'<span class="rc-line">{inline(result["evidence"])}</span>' if result and result.get("evidence") else ""
        rc += repair_line(entry, repair.get("branch"), T, inline)
        return (f'<div class="task" id="t-{t["code"]}"><span class="code">{box}{t["code"]}</span><div><span class="prio p{pr[1]}">{pr}</span><b>{inline(t["name"])}</b> · <span class="legend">{esc(lanes[t["lane"]])}</span>{marks}<br>'
                f'{inline(t["what"])}{fix_html(t, T, inline, esc)}<span class="check">{inline(t["check"])}</span>{rc}</div></div>')
    label = fixes.stack_name(stack, LANG)
    stack_html = f'<p class="stack"><span class="lbl">{T("stack_label")}</span> <b>{esc(label)}</b></p>' if label else f'<p class="prose">{T("stack_none")}</p>'
    if files and not any(e["status"] == "applied" for e in repair.get("tasks", {}).values()):
        stack_html += f'<p class="prose">{inline(T("fix_files_note", n=len(files)))}</p>'
    if tasks:
        fixed_n = sum(1 for v in recheck.values() if v["status"] == "fixed")
        tasks_html = stack_html + progress_html(rows_now, [(t["code"], t.get("criterion")) for t in tasks], f"{S['domain']}:{S['date']}", fmt_score(grid_scores(rows_now, LETTERS)[1], LANG), T, LANG, T("rc_summary", n=fixed_n, date=rc_date) if rc_date else "") + repair_block([t["kind"] for t in tasks], repair, stack, T, esc, tasks) + f'<div class="tasks">{"".join(task_html(t) for t in top)}</div>' + (f'<details class="more-tasks"><summary>{T("quick_tasks_rest", n=len(rest))}</summary><div class="tasks">{"".join(task_html(t) for t in rest)}</div></details>' if rest else "")
    else:
        tasks_html = f'<p class="prose">{T("quick_no_tasks")}</p>'
    # the AI panel
    P = Q.get("panel")
    if P and P.get("assistants"):
        res = {a_["name"]: {str(x["q"]): x for x in a_["answers"]} for a_ in P["assistants"]}
        proxy = any(a_.get("kind") == "search" for a_ in P["assistants"])
        bq = str(P.get("brand_question", ""))
        market = [x for a_ in P["assistants"] if a_.get("kind", "assistant") == "assistant" for x in a_["answers"] if str(x["q"]) != bq]
        stat = f'<p class="panel-stat">{T("panel_stat", n=sum(1 for x in market if x["cited"]), total=len(market))}</p>' if market else ""
        qas = []
        for q in sorted(P["questions"], key=int):
            cards = []
            for a_ in P["assistants"]:
                x = res[a_["name"]].get(q)
                if not x:
                    continue
                proxy_tag = f' <span class="legend">{T("quick_panel_proxy")}</span>' if a_.get("kind") == "search" else ""
                cards.append(f'<div class="qa-a"><div class="top">{esc(a_["name"])}{proxy_tag} {pill("ok", T("cited")) if x["cited"] else pill("bad", T("not_cited"))}</div><p>{inline(x.get("note", ""))}</p></div>')
            qas.append(f'<div class="qa"><p class="qa-q"><span>Q{q}</span>{esc(P["questions"][q])}</p><div class="qa-as">{"".join(cards)}</div></div>')
        panel_html = stat + who_html(P["assistants"], bq, T, esc) + f'<div class="qas">{"".join(qas)}</div>' + (f'<p class="prose">{T("quick_panel_proxy_note")}</p>' if proxy else "")
    else:
        panel_html = f'<div class="warnbox">{T("quick_panel_none")}</div>'
    # the measures anyone can repeat
    m = Q["measures"]
    enc = urllib.parse.quote(S["url"], safe="")
    host = urllib.parse.urlparse(S["url"]).hostname
    na = lambda s: T("quick_unavailable_why", reason=s.get("reason") or "?")
    psi_txt = T("quick_psi_local" if m["psi"].get("source") == "lighthouse" else "quick_psi_api", perf=m["psi"].get("perf"), a11y=m["psi"].get("a11y")) if m["psi"]["status"] == "ok" else na(m["psi"])
    obs_txt = f'{m["observatory"].get("grade")} · {m["observatory"].get("score")} / 100' if m["observatory"]["status"] == "ok" else na(m["observatory"])
    links = [("PageSpeed Insights", f"https://pagespeed.web.dev/analysis?url={enc}&form_factor=mobile", psi_txt),
             ("Mozilla HTTP Observatory", f"https://developer.mozilla.org/en-US/observatory/analyze?host={host}", obs_txt),
             ("Security Headers", f"https://securityheaders.com/?q={enc}&followRedirects=on&hide=on", ""),
             ("Rich Results Test", f"https://search.google.com/test/rich-results?url={enc}", "")]
    links_html = "<ul>" + "".join(f'<li><a href="{html.escape(u)}" target="_blank" rel="noopener">{esc(n)}</a>' + (f"{SEP}{esc(r)}" if r else "") + "</li>" for n, u, r in links) + "</ul>"
    src = {"auto": T("quick_src_auto"), "judged": T("quick_src_judged"), "panel": T("quick_src_panel"), "none": T("quick_src_none")}
    crit = []
    for L, name, _ in DEF["categories"]:
        crit.append(f'<tr class="cat"><td colspan="5"><b>{L}. {esc(name)}</b> · {fmt_score(cats[L], LANG) if cats[L] is not None else "NV"} / 10</td></tr>')
        for code, label, sc, ev, so in [r for r in rows if r[0][0] == L]:
            cls = {"0": "bad", "1": "warn", "2": "ok"}.get(sc, "na")
            crit.append(f"<tr><td class='num'>{code}</td><td>{esc(label)}</td><td class='c'>{pill(cls, sc)}</td><td>{inline(ev)}</td><td>{esc(src[so])}</td></tr>")
    page = f"""<!doctype html><html lang="{LANG}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{T('quick_doc_title', domain=esc(S['domain']))}</title>
<style>{fonts}{css}</style></head><body>
<header class="band"><div class="wrap">
  <p class="eyebrow">{T('quick_eyebrow', domain=esc(S['domain']), date=esc(date))}</p>
  <h1>{T('quick_h1', domain=soft_domain(esc(S['domain'])))}</h1>
  <p class="lead">{T('quick_lead')}</p>
  <div class="meta"><span><b>{T('meta_score')}</b> {score} / 10</span><span><b>{T('quick_coverage')}</b> {checked} / {len(GRID)}</span><span><b>{T('quick_pages')}</b> {m['crawl']['pages_ok']}{" / " + str(m['crawl']['sitemap']) if m['crawl'].get('sitemap', 0) > m['crawl']['pages_ok'] else ""}</span></div>
</div></header>
<div class="wrap"><main style="padding-block:48px 96px">
<section><div class="head"><h2>{inline(headline)}</h2></div>{scores}
<div class="warnbox"><b>{T('quick_provisional_title')}</b> {T('quick_provisional', n=checked, total=len(GRID))}</div></section>
{first_html([(t["code"], t["name"], lanes[t["lane"]] + (" · " + signed_gain(t["gain"], LANG) if t.get("gain") else "")) for t in first_codes], T, inline)}
{summary}
{view}
<section id="panel"><div class="head"><h2>{T('quick_panel_title')}</h2></div>{panel_html}</section>
<section id="todo"><div class="head"><h2>{T('quick_tasks_title', n=len(top))}</h2></div>{tasks_html}</section>
<section id="criteres"><div class="head"><h2>{T('quick_criteria_title', n=len(GRID))}</h2></div><p class="legend">{pill('ok', '2')} {T('legend_2')} · {pill('warn', '1')} {T('legend_1')} · {pill('bad', '0')} {T('legend_0')} · {pill('na', 'NV')} {T('legend_nv')}</p>
<div class="tbl wide"><table><thead><tr><th>#</th><th>{T('crit_col')}</th><th class="c">{T('crit_score')}</th><th>{T('crit_proof')}</th><th>{T('quick_crit_source')}</th></tr></thead><tbody>{''.join(crit)}</tbody></table></div></section>
<section><div class="head"><h2>{T('quick_examiners_title')}</h2></div><div class="card">{links_html}</div></section>
<section><div class="head"><h2>{T('quick_limits_title')}</h2></div><p class="prose">{T('quick_limits', max=S.get('max_pages', 25), speed=T("quick_speed_local" if Q["measures"]["psi"].get("source") == "lighthouse" else "quick_speed_api" if Q["measures"]["psi"]["status"] == "ok" else "quick_speed_none"))}</p></section>
<section><div class="head"><h2>{T('quick_next_title')}</h2></div><p class="prose">{inline(T('quick_next', url=S['url']))}</p></section>
</main></div>
{fix_script()}
<footer><div class="wrap"><p>{T('quick_footer', brand=esc(S['brand']), domain=esc(S['domain']), date=esc(date))}</p></div></footer>
</body></html>"""
    os.makedirs(out_dir, exist_ok=True)
    base = f"{S['date']} {T('file_quick')} - {S['domain'].replace(':', '-')}"
    report = os.path.join(out_dir, base + ".html")
    open(report, "w", encoding="utf-8").write(page)
    md = ["# " + T("quick_md_title", domain=S["domain"]), "", T("quick_md_sub", date=date, score=score, n=checked, total=len(GRID)), ""]
    table = [list(UI[LANG]["csv_head"])]
    for L, name in lanes.items():
        lt = [t for t in tasks if t["lane"] == L]
        if not lt:
            continue
        md += [f"## {name}", ""]
        for t in lt:
            pr = prio_label[t["prio"]][0]
            done, state = task_state(t["code"], t.get("criterion"), recheck, repair, T, rc_date)
            md.append(f"- [{'x' if done else ' '}] **{t['code']} · {t['name']}** ({pr}){SEP}{t['what'].rstrip('. ')}. _{t['check'].rstrip('. ')}_" + (f" **{state}**" if state else ""))
            md += md_details(t, T)
            table.append([t["code"], name, pr, t["name"], t["what"], t["check"], t.get("where", ""), t.get("file", ""), state])
        md.append("")
    open(os.path.join(out_dir, base + ".md"), "w", encoding="utf-8").write("\n".join(md))
    with open(os.path.join(out_dir, base + ".csv"), "w", encoding="utf-8-sig", newline="") as f:
        csv.writer(f).writerows(table)
    print(f"score {score} / 10 on {checked} of {len(GRID)} criteria, {len(tasks)} tasks ({n_p1} P1)" + (f", {len(rest)} of them after the first 10" if rest else ""))
    print("report:", report)
    print("to-do:", base + ".md", "and .csv")


SITE_LEVEL = {"C1", "C2", "F2"}  # one page is enough to check these
FAIL_ONLY = {"B4", "B5"}  # no automatic score when they pass: see auto_scores


def read_site(url, delay, max_pages, partial=False, map_host=None):
    """The same walk as the audit, links included: reading only the pages known to work would hide a broken link still there."""
    with tempfile.TemporaryDirectory() as tmp:
        cmd = [sys.executable, os.path.join(HERE, "crawl.py"), url, os.path.join(tmp, "crawl"), "--delay", str(delay), "--max", str(max_pages)]
        if partial:
            os.makedirs(os.path.join(tmp, "crawl"), exist_ok=True)
            with open(os.path.join(tmp, "urls.txt"), "w") as f:
                f.write(url)
            cmd += ["--urls", os.path.join(tmp, "urls.txt")]
        if map_host:
            cmd += ["--map-host", map_host]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
        return measures_from_crawl(os.path.join(tmp, "crawl"), url)


def cmd_check(a):
    """Reads the site again and says, for each fix, what a machine can conclude. The audit's own measures and score stay as they were."""
    data = json.load(open(a.audit, encoding="utf-8"))
    S = data["site"]
    lang = report_lang(S, a.lang)
    QL = json.load(open(os.path.join(ASSETS, "quick.json"), encoding="utf-8"))[lang]
    is_quick = "measures" in data
    if is_quick:
        rows, _ = score_rows(data, QL)
        wanted = {t["key"]: t for t in build_tasks(data, rows, QL, limit=None)[0]}
        tasks = {(t.get("criterion") or k): t["code"] for k, t in wanted.items() if (t.get("criterion") or k) in GRID}
        before = auto_scores(data["measures"], None, QL["ev"])
        old = {k: v[0] for k, v in before.items()}
    else:
        tasks = {t["criterion"]: c for c, t in data.get("tasks", {}).items() if t.get("criterion")}
        old = {r[0]: str(r[2]) for r in data["criteres"]}
    if a.only:
        # the codes shown on the cards: a task code can look like a criterion (F2), so only task codes are accepted
        codes = {x.strip() for x in a.only.split(",")}
        unknown = codes - set(tasks.values())
        if unknown:
            sys.exit(f"unknown task: {', '.join(sorted(unknown))}. Known: {', '.join(sorted(tasks.values()))}")
        tasks = {k: v for k, v in tasks.items() if v in codes}
    partial = bool(a.only) and set(tasks) <= SITE_LEVEL
    crawl = read_site(S["url"], a.delay, a.max or S.get("max_pages") or 25, partial)
    if not crawl["pages_ok"]:
        sys.exit(f"no page could be read at {S['url']}: nothing can be concluded. Try again later.")
    gone = {"status": "unavailable", "reason": "not rechecked"}
    stored = data.get("measures", {})
    fresh = {"crawl": crawl, "psi": stored.get("psi", gone), "observatory": stored.get("observatory", gone), "wikidata": stored.get("wikidata", gone)}
    if a.services:
        fresh["psi"] = pagespeed(S["url"])
        fresh["observatory"] = observatory(urllib.parse.urlparse(S["url"]).hostname)
    now = auto_scores(fresh, None, QL["ev"])
    results, manual = {}, []
    for crit, code in sorted(tasks.items(), key=lambda kv: kv[1]):
        was = old.get(crit)
        if crit in FAIL_ONLY and crit not in now and was == "0":
            score, ev = "2", ""
        elif crit in now:
            score, ev = now[crit][0], now[crit][1]
        else:
            manual.append(code)
            continue
        if was in (None, "NV"):
            status = "fixed" if score == "2" else "same"
        else:
            status = "fixed" if score == "2" else "better" if int(score) > int(was) else "worse" if int(score) < int(was) else "same"
        results[crit] = {"status": status, "old": was, "new": score, "evidence": ev, "code": code}
    prev = (data.get("recheck") or {}).get("results", {}) if a.only else {}
    data["recheck"] = {"date": datetime.date.today().isoformat(), "results": {**prev, **results}}
    json.dump(data, open(a.audit, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for crit, r in results.items():
        print(f"{r['code']:<4} {crit:<3} {r['status']:<7} {r['old']} -> {r['new']}  {r['evidence']}")
    if manual:
        print("not checkable by machine, use their \"Verified when\":", ", ".join(manual))
    print(f"{sum(1 for r in results.values() if r['status'] == 'fixed')} fixed of {len(results)} checked. The score of the audit does not change: run a new audit, then compare, to measure progress.")


def cmd_brand(a):
    """The name is often not in the request, and a domain has no accents: set it once the site has been read."""
    data = json.load(open(a.quick, encoding="utf-8"))
    data["site"]["brand"] = a.name
    data["measures"]["wikidata"] = wikidata(a.name, report_lang(data["site"]))
    json.dump(data, open(a.quick, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"brand: {a.name}. Wikidata: {data['measures']['wikidata']['status']}.")


def main():
    ap = argparse.ArgumentParser(description="Quick SEO and GEO audit")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("measure")
    p.add_argument("url"); p.add_argument("out")
    p.add_argument("--brand"); p.add_argument("--lang", choices=["en", "fr"]); p.add_argument("--theme", default="signature")
    p.add_argument("--max", type=int, default=25); p.add_argument("--delay", type=float, default=1); p.add_argument("--offline", action="store_true")
    p.set_defaults(fn=cmd_measure)
    p = sub.add_parser("build")
    p.add_argument("quick"); p.add_argument("out", nargs="?"); p.add_argument("--lang", choices=["en", "fr"])
    p.set_defaults(fn=cmd_build)
    p = sub.add_parser("brand", help="set the exact name of the site, and search Wikidata for it")
    p.add_argument("quick"); p.add_argument("name"); p.set_defaults(fn=cmd_brand)

    p = sub.add_parser("check", help="read the site again and say which fixes hold")
    p.add_argument("audit"); p.add_argument("only", nargs="?", help="task codes shown on the cards, separated by commas: B1,F3. All by default")
    p.add_argument("--lang", choices=["en", "fr"]); p.add_argument("--delay", type=float, default=1); p.add_argument("--max", type=int); p.add_argument("--services", action="store_true", help="also ask PageSpeed and Observatory again")
    p.set_defaults(fn=cmd_check)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
