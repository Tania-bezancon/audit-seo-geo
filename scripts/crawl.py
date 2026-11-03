#!/usr/bin/env python3
"""Relevé automatique d'un site, lent et reprenable.

  python3 crawl.py https://exemple.com/fr OUT_DIR [--delay 3] [--max 400] [--jina] [--urls fichier.txt]

- Découvre les pages par robots.txt, le plan du site (index compris) puis les liens internes.
- Pour chaque page : code HTTP, redirection, temps de réponse (TTFB), poids du HTML, en-têtes de cache et de serveur,
  title, description, robots, lang, canonical, hreflang, H1, H2, mots collés (deux mots séparés par <br> sans espace),
  images et images sans alt, JSON-LD, Open Graph, viewport, nombre de mots, nombre de scripts, dates,
  et un indice de rendu par JavaScript (page presque vide sans JavaScript : les robots des IA n'y voient rien).
- Pour le site : robots des IA autorisés ou bloqués, llms.txt, compression, en-têtes de sécurité, fausse 404, www, http.
- Écrit OUT_DIR/crawl.jsonl (une ligne par page, reprise automatique), OUT_DIR/robots.txt, OUT_DIR/sitemap-urls.txt,
  OUT_DIR/summary.json (les compteurs du rapport) et OUT_DIR/checks.json (fausse 404, www, http).
- Prudence : une page toutes les --delay secondes. Certains serveurs bloquent l'adresse au-delà d'une centaine de
  requêtes rapides (35 min lors d'un audit réel). --jina passe par le lecteur r.jina.ai en cas de blocage.
"""
import argparse, collections, gzip, html, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request
from html.parser import HTMLParser

ap = argparse.ArgumentParser()
ap.add_argument("start"); ap.add_argument("out")
ap.add_argument("--delay", type=float, default=3); ap.add_argument("--max", type=int, default=400)
ap.add_argument("--jina", action="store_true"); ap.add_argument("--urls")
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
START = a.start.rstrip("/")
U = urllib.parse.urlparse(START)
ROOT = f"{U.scheme}://{U.netloc}"
HOST = U.netloc
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36 audit-seo"


class NoRedir(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *x, **k):
        return None


LAST = {}  # en-têtes et temps de la dernière réponse


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
            out.append("JSON invalide"); continue
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
        ld=ld_types(p.ld), words=len(re.findall(r"\w+", " ".join(p.text))), og_image=p.metas.get("og:image"),
        og_title=p.metas.get("og:title"), og_desc=p.metas.get("og:description"), twitter=p.metas.get("twitter:card"),
        viewport=p.metas.get("viewport"), scripts=p.scripts, published=p.metas.get("article:published_time"), times=[t for t in p.time if t],
        mixed=len(re.findall(r'(?:src|href)="http://', body)),
    )
    o["rendu_js_probable"] = o["words"] < 80 and o["scripts"] >= 5
    links = []
    for h in p.hrefs:
        u = urllib.parse.urljoin(url, h).split("#")[0]
        if urllib.parse.urlparse(u).netloc == HOST and not re.search(r"\.(pdf|jpe?g|png|gif|svg|webp|zip|mp4|docx?|xlsx?|pptx?)$", u, re.I):
            links.append(u)
    return o, links


# --- robots.txt et plan du site
code, robots, _ = get(ROOT + "/robots.txt", follow=True)
open(os.path.join(a.out, "robots.txt"), "w").write(robots if code == 200 else f"# {code}\n")
maps = re.findall(r"(?im)^sitemap:\s*(\S+)", robots) or [ROOT + "/sitemap.xml"]
seen_maps, sm_urls = set(), []
while maps:
    m = maps.pop(0)
    if m in seen_maps: continue
    seen_maps.add(m); time.sleep(a.delay / 2)
    c, x, _ = get(m, follow=True)
    if c != 200: continue
    locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", x)
    if "<sitemapindex" in x: maps += locs
    else: sm_urls += [html.unescape(l) for l in locs]
sm_urls = list(dict.fromkeys(sm_urls))
open(os.path.join(a.out, "sitemap-urls.txt"), "w").write("\n".join(sm_urls))
print(f"robots.txt {code}, plan du site : {len(sm_urls)} adresses")

# --- exploration
queue = [l.strip() for l in open(a.urls)] if a.urls else [START] + sm_urls
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
            print(f"  {o['status']} sur {u} : le serveur bloque peut-être l'adresse. Relancer plus tard ou avec --jina.")
        done[u] = o; f.write(json.dumps(o, ensure_ascii=False) + "\n"); f.flush()
        if not a.urls:
            queue += [l for l in links if l not in done and l not in queue]
        i += 1
        if i % 20 == 0: print(f"  {len(done)} pages…")

# --- contrôles d'ensemble
checks = {}
time.sleep(a.delay)
c, _, loc = get(ROOT + "/page-qui-n-existe-pas-audit-404")
checks["fausse_404"] = {"status": c, "location": loc, "verdict": "vraie 404" if c == 404 else "à vérifier : une adresse inconnue ne renvoie pas 404"}
alt = U.netloc[4:] if U.netloc.startswith("www.") else "www." + U.netloc
for name, u in [("autre_hote", f"{U.scheme}://{alt}/"), ("http", f"http://{U.netloc}/")]:
    time.sleep(a.delay)
    c, _, loc = get(u)
    checks[name] = {"url": u, "status": c, "location": loc}
# robots des IA : bloqués par robots.txt ?
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
checks["robots_ia"] = {b: ("bloqué" if blocked(b) else "autorisé") for b in
                       ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "PerplexityBot", "Google-Extended", "Applebot-Extended", "CCBot", "Bingbot", "Googlebot"]}
time.sleep(a.delay)
c, body, _ = get(ROOT + "/llms.txt", follow=True)
checks["llms_txt"] = {"status": c, "lignes": len(body.splitlines()) if c == 200 else 0}
time.sleep(a.delay)
get(START, follow=True, headers={"Accept-Encoding": "br, gzip"})
h = LAST.get("headers", {})
checks["accueil"] = {"compression": h.get("content-encoding", "aucune"), "cache": h.get("cache-control"), "server": h.get("server"), "ttfb_ms": LAST.get("ttfb"),
                     "securite": {k: (k in h) for k in ["strict-transport-security", "content-security-policy", "x-content-type-options",
                                                          "x-frame-options", "referrer-policy", "permissions-policy"]}}
json.dump(checks, open(os.path.join(a.out, "checks.json"), "w"), ensure_ascii=False, indent=1)

# --- compteurs pour le rapport
R = [r for r in done.values() if r.get("status") == 200]
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
