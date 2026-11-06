#!/usr/bin/env python3
"""Checks what selftest.sh built. Exits with 1 and lists the problems if anything is wrong."""
import csv, glob, json, os, re, sys, tempfile
import common
import compare as cmp
import fixes
import quick
from common import ASSETS

out = sys.argv[1]
rep_files = lambda d: glob.glob(os.path.join(d, "quick", "*.html")) + glob.glob(os.path.join(d, "compare", "*.html"))
err = []
names = {"en": ("*single page.html", "Code", "Lane", "Priority"), "fr": ("*page unique.html", "Code", "Voie", "Priorité")}
total = {}
for L, (single, *head) in names.items():
    d = os.path.join(out, L)
    for n in ["index.html", single, "*To-do SEO GEO*.md", "*To-do SEO GEO*.csv"]:
        if not glob.glob(os.path.join(d, n)):
            err.append(f"{L}: missing {n}")
    page = open(os.path.join(d, "index.html"), encoding="utf-8").read()
    if f'<html lang="{L}">' not in page:
        err.append(f"{L}: wrong html lang")
    for img in set(re.findall(r'src="(captures/[^"]+)"', page)):
        if not os.path.exists(os.path.join(d, img)):
            err.append(f"{L}: screenshot missing: {img}")
    rows = list(csv.reader(open(glob.glob(os.path.join(d, "*.csv"))[0], encoding="utf-8-sig")))
    total[L] = len(rows) - 1
    if len(rows) < 2 or rows[0][:3] != head:
        err.append(f"{L}: empty or malformed to-do CSV")
    if re.search(r"\b20\d\d-\d\d-\d\d\b", " ".join(r[4] for r in rows[1:])):
        err.append(f"{L}: a date in the to-do")
text = re.sub(r"<style.*?</style>|<[^>]+>", " ", open(os.path.join(out, "en", "index.html"), encoding="utf-8").read(), flags=re.S)
left = sorted(set(re.findall(r"\b\w*[éèêàùçîô]\w*\b", text)))
if left:
    err.append(f"en: French left in the report: {left[:10]}")
if "5.0" not in text:
    err.append("en: the score is not written with a decimal point")
if "5,0" not in open(os.path.join(out, "fr", "index.html"), encoding="utf-8").read():
    err.append("fr: the score is not written with a decimal comma")

# the quick audit: the rules, on a site whose defects are known
Q = json.load(open(os.path.join(out, "quick", "quick.json"), encoding="utf-8"))
rep = glob.glob(os.path.join(out, "quick", "*Quick audit*.html"))
if not rep or not glob.glob(os.path.join(out, "quick", "fr", "*Audit rapide*.html")):
    err.append("quick: report missing")
else:
    page = open(rep[0], encoding="utf-8").read()
    if "Provisional score" not in page:
        err.append("quick: the score is not labelled provisional")
    if "captures/" in page:
        err.append("quick: the report must stay a single file")
c = Q["measures"]["crawl"]
expected = {"pages_ok": 3, "errors": 1, "fake_404_status": 404, "js_pages": 1, "home_js": False, "no_viewport": 1, "llms": 404}
for k, v in expected.items():
    if c[k] != v:
        err.append(f"quick crawl: {k} = {c[k]}, expected {v}")
if c["ai_bots"]["OAI-SearchBot"] != "blocked" or c["ai_bots"]["PerplexityBot"] != "allowed" or "GPTBot" in c["ai_bots"]:
    err.append(f"quick crawl: AI crawlers read wrongly: {c['ai_bots']}")

# the scoring rules, on known inputs
wd = [{"id": "Q1", "label": "Mozilla Corporation", "match": {"text": "Mozilla Corporation"}}, {"id": "Q2", "label": "Mozillians"}]
if [h["id"] for h in quick.wikidata_hits(wd, "Mozilla")] != ["Q1"]:
    err.append("quick rules: Wikidata candidates read wrongly")
if quick.wikidata_hits(wd, "Zilla"):
    err.append("quick rules: Wikidata must not match inside a label")
sample = {"lighthouseResult": {"categories": {"performance": {"score": 0.42}, "accessibility": {"score": 0.91}}},
          "loadingExperience": {"metrics": {"LARGEST_CONTENTFUL_PAINT_MS": {"percentile": 3100}, "INTERACTION_TO_NEXT_PAINT": {"percentile": 150}, "CUMULATIVE_LAYOUT_SHIFT_SCORE": {"percentile": 5}}}}
psi = quick.parse_pagespeed(sample)
if psi != {"status": "ok", "source": "api", "perf": 42, "a11y": 91, "field": {"lcp": 3100, "inp": 150, "cls": 0.05}}:
    err.append(f"quick rules: PageSpeed read wrongly: {psi}")
QL = json.load(open(os.path.join(ASSETS, "quick.json"), encoding="utf-8"))["en"]
Q["measures"]["psi"] = psi
Q["judged"] = {"E1": ["1", "read on the page"]}
Q["panel"] = {"questions": {"1": "a", "2": "b"}, "brand_question": "2", "assistants": [
    {"name": "A", "kind": "assistant", "answers": [{"q": 1, "cited": True, "note": ""}, {"q": 2, "cited": True, "note": ""}]},
    {"name": "S", "kind": "search", "answers": [{"q": 1, "cited": False, "note": ""}]}]}
rows, problems = quick.score_rows(Q, QL)
err += problems
got = {r[0]: (r[2], r[4]) for r in rows}
if got["A2"][0] != "1":
    err.append(f"quick rules: A2 scored {got['A2'][0]}, expected 1")
multi = json.loads(json.dumps(Q)); multi["measures"]["crawl"].update(http={"url": "h", "status": 301, "location": "https://x/"}, other_host={"url": "https://w/", "status": "ERR"}, no_canonical=0, https=True)
if quick.score_rows(multi, QL)[0][1][2] != "2":
    err.append("quick rules: A2 must be 2 on a one-language site with redirects and canonicals")
multi["measures"]["crawl"].update(languages=2, no_hreflang=3)
if quick.score_rows(multi, QL)[0][1][2] != "1":
    err.append("quick rules: two languages without hreflang must cap A2 at 1")
want = {"A3": "1", "A4": "1", "B1": "1", "B2": "0", "B5": "0", "C1": "0", "E1": "1", "E5": "2", "F1": "1", "F2": "0", "F5": "2", "A5": "NV", "B3": "NV", "D4": "NV"}
for k, v in want.items():
    if got[k][0] != v:
        err.append(f"quick rules: {k} scored {got[k][0]}, expected {v}")
if (got["E1"][1], got["F5"][1], got["A5"][1]) != ("judged", "panel", "none"):
    err.append("quick rules: wrong source of a score")
if not quick.score_rows(dict(Q, judged={"E1": ["2", ""]}), QL)[1]:
    err.append("quick rules: an empty evidence must be refused")
tasks, _, problems = quick.build_tasks(dict(Q, task_overrides={"X1": {"lane": "Z", "name": "n", "what": "w", "check": "c"}}), rows, QL)
if not problems:
    err.append("quick rules: an unknown lane must be refused")

# the reports need no third party: fonts embedded or next to the page, nothing loaded from elsewhere
single_files = glob.glob(os.path.join(out, "en", "*single page.html")) + rep_files(out)
for f in single_files:
    page = open(f, encoding="utf-8").read()
    if "data:font/woff2" not in page:
        err.append(f"fonts not embedded in {os.path.basename(f)}")
    if re.search(r"""(?:src|href)=["']https?://(?!(?:www\.)?(?:pagespeed|developer\.mozilla|securityheaders|search\.google))[^"']*\.(?:css|js|woff2?)""", page) or "fonts.googleapis" in page:
        err.append(f"a third-party resource in {os.path.basename(f)}")
for fn in ("archivo-latin.woff2", "inter-latin.woff2", "jetbrains-mono-latin.woff2"):
    if not os.path.exists(os.path.join(out, "en", "fonts", fn)):
        err.append(f"font missing next to the report: {fn}")
    if not os.path.exists(os.path.join(ASSETS, "fonts", "OFL-" + fn.replace("-latin.woff2", ".txt"))):
        err.append(f"licence missing for {fn}")

# what helps someone apply the fixes
s = fixes.detect_stack('<script src="/_next/static/a.js"></script>', {"Server": "Netlify"})
if (s["framework"], s["host"]) != ("next", "netlify"):
    err.append(f"fixes: platform read wrongly: {s}")
if fixes.detect_stack('<link href="/wp-content/x.css">', {"server": "nginx/1.2"})["framework"] != "wordpress":
    err.append("fixes: WordPress not detected")
if fixes.detect_stack("<p>hello</p>", {})["framework"] or fixes.detect_stack("<p>hello</p>", {})["host"]:
    err.append("fixes: a platform must never be guessed")
if fixes.dedupe_title("Ceremony · Creative · Ada Lovelace · Ada Lovelace") != "Ceremony · Creative · Ada Lovelace" or fixes.dedupe_title("Northwind · Ada Lovelace") is not None:
    err.append("fixes: repeated names read wrongly")
some = {"strict-transport-security": True, "x-content-type-options": True}
name, text = fixes.headers_file(some, "netlify", "en")
if name != "_headers" or "X-Content-Type-Options" in text or "X-Frame-Options" not in text or "Content-Security-Policy-Report-Only" not in text:
    err.append("fixes: the headers file must list only what is missing, with a CSP that only reports")
json.loads(fixes.headers_file(some, "vercel", "en")[1])
if fixes.headers_file(some, "nginx", "en")[0] != "security-headers.nginx.conf" or fixes.headers_file(some, None, "en")[0] != "security-headers.txt":
    err.append("fixes: wrong file for the host")
if "webflow" not in str(fixes.recipe("C2", "en", {"framework": "webflow", "host": "cloudflare"})).lower() and "platform" not in fixes.recipe("C2", "en", {"framework": "webflow", "host": "cloudflare"})["how"]:
    err.append("fixes: a hosted platform must come before its CDN")
if "_headers" not in fixes.recipe("C2", "fr", {"framework": "next", "host": "netlify"})["where"]:
    err.append("fixes: the host decides for headers")
if "metadata" not in fixes.recipe("D1", "en", {"framework": "next", "host": "netlify"})["where"]:
    err.append("fixes: the framework decides for titles")
if not fixes.recipe("F2", "en", {})["where"] or not fixes.recipe("F2", "fr", None)["where"]:
    err.append("fixes: an unknown platform needs general instructions")
R_ = json.load(open(fixes.RECIPES, encoding="utf-8"))
for k in R_["en"]:
    if not k.startswith("_") and set(R_["en"][k]) != set(R_["fr"][k]):
        err.append(f"fixes: {k} differs between languages")
for f in ("fixes/llms.txt", "fixes/security-headers.txt", "fixes/titles-to-fix.csv"):
    if not os.path.exists(os.path.join(out, "quick", f)):
        err.append(f"fixes: missing {f}")
page = open(glob.glob(os.path.join(out, "quick-example", "*.html"))[0], encoding="utf-8").read()
for piece in ('class="bas"', 'class="copy"', "fix-file", "Next.js"):
    if piece not in page:
        err.append(f"fixes: {piece} missing from the quick report")
full = open(os.path.join(out, "en", "index.html"), encoding="utf-8").read()
if 'class="bas"' not in full or 'class="copy"' not in full or "`" in re.sub(r"<(?:style|script).*?</(?:style|script)>", "", full, flags=re.S):
    err.append("fixes: cards missing from the full report, or raw markup left")

# the opening, the site seen from outside, who is cited instead
page = open(glob.glob(os.path.join(out, "quick-example", "*.html"))[0], encoding="utf-8").read()
for piece in ('class="looks"', 'class="first"', 'id="view"', 'class="robot', 'class="who"', 'class="qa"', "Competitor A"):
    if piece not in page:
        err.append(f"opening: {piece} missing from the quick report")
for code in re.findall(r'class="first" href="#t-([A-Z0-9]+)"', page):
    if f'id="t-{code}"' not in page:
        err.append(f"opening: the card {code} leads nowhere")
full = open(os.path.join(out, "en", "index.html"), encoding="utf-8").read()
for piece in ('class="looks"', 'class="first"', 'id="view"', 'class="who"', 'captures/site-09'):
    if piece not in full:
        err.append(f"opening: {piece} missing from the full report")
if common.looks_html([["A1", "x", "NV", ""]] + [["F1", "y", "2", ""]], "1.0", common.translator("en"), "en", "z").count("not checked") != 4:
    err.append("opening: a look with no checked criterion must say so, not show a score")
if 'href="#t-' not in full or len(re.findall(r'class="first"', full)) != 3:
    err.append("opening: the full report must show three first tasks")
for w, want in ((30, "bad"), (200, "warn"), (800, "ok")):
    html_ = common.view_html({"pages": [{"url": "u", "words": w, "excerpt": "e"}]}, common.translator("en"), lambda t: t, lambda t: t, "en")
    if f'pill {want}' not in html_:
        err.append(f"view: {w} words should read {want}")
counted = common.who_html([{"name": "a", "answers": [{"q": 1, "cited_instead": ["X", "Y"]}, {"q": 2, "cited_instead": ["Z"]}]}, {"name": "b", "kind": "search", "answers": [{"q": 1, "cited_instead": ["Q"]}]}, {"name": "c", "answers": [{"q": 1, "cited_instead": ["X"]}]}], 2, common.translator("en"), lambda t: t)
if "Q" in re.sub(r"<[^>]+>", "", counted) or ">Z<" in counted or '>2</span>' not in counted:
    err.append("who: the brand question and search proxies must not count")

# the gain, the ticks and the recheck
rows = [[f"{L}{i}", "x", "2", ""] for L in "ABCDEF" for i in range(1, 6)]
rows[10][2] = "0"
if common.grid_gain(rows, "C1") != 0.3 or common.grid_gain(rows, "A1") != 0 or common.grid_gain(rows, "ZZ") != 0:
    err.append(f"gain: wrong on the grid ({common.grid_gain(rows, 'C1')})")
if common.grid_gain([["A1", "x", "NV", ""], ["A2", "x", "1", ""]], "A1", "A") != 0:
    err.append("gain: a criterion that could not be checked promises nothing")
after = common.apply_recheck(rows, {"C1": {"status": "better", "new": "1"}, "A1": {"status": "worse", "new": "0"}})
if after[10][2] != "1" or after[0][2] != "2":
    err.append("recheck: only what got better replaces what the audit measured")
d = json.load(open(os.path.join(out, "quick", "quick.json"), encoding="utf-8"))
was = json.load(open(os.path.join(out, "quick", "before.json"), encoding="utf-8"))
res = d["recheck"]["results"]
if d["measures"] != was["measures"]:
    err.append("recheck: the measures of the audit must not change")
if res.get("F2", {}).get("status") != "fixed" or res["F2"].get("old") != "0" or res["F2"].get("new") != "2":
    err.append(f"recheck: F2 really fixed on the test site, read {res.get('F2')}")
if res.get("B5", {}).get("status") != "fixed":
    err.append(f"recheck: the missing viewport was added on the test site, read {res.get('B5')}")
if res.get("A3", {}).get("status") != "same" or res.get("D2", {}).get("status") == "worse":
    err.append(f"recheck: the broken link is still there, read {res.get('A3')}")
first_run = open(os.path.join(out, "quick", "recheck-0.txt"), encoding="utf-8").read()
if not first_run.splitlines()[-1].startswith("0 fixed of"):
    err.append("recheck: nothing was fixed in the first run, read: " + first_run.splitlines()[-1][:60])
if not open(os.path.join(out, "quick", "recheck-1.txt"), encoding="utf-8").read().startswith("B2") or len(open(os.path.join(out, "quick", "recheck-1.txt"), encoding="utf-8").read().splitlines()) != 2:
    err.append("recheck: a single task must check that task only")
page = open(glob.glob(os.path.join(out, "quick", "after", "*.html"))[0], encoding="utf-8").read()
if not re.search(r'data-crit="F2" data-verified="1"', page) or "Fixed, rechecked on" not in page or "Not yet, rechecked on" not in page:
    err.append("recheck: the result must show on the cards")
page = open(glob.glob(os.path.join(out, "quick-example", "*.html"))[0], encoding="utf-8").read()
if 'id="progress"' not in page or 'id="audit-grid"' not in page or "up to +" not in page or 'class="done"' not in page or "Fixed, rechecked" in page:
    err.append("ticks: progress, gain or tick boxes missing from the quick report")
full = open(os.path.join(out, "en", "index.html"), encoding="utf-8").read()
if 'id="progress"' not in full or "up to +" not in full or 'data-crit="A4"' not in full:
    err.append("ticks: progress or gain missing from the full report")
fa = json.load(open(os.path.join(out, "quick", "full-audit.json"), encoding="utf-8"))
if not fa.get("recheck", {}).get("results") or fa["note"] != json.load(open(os.path.join(ASSETS, "example", "audit.en.json"), encoding="utf-8"))["note"]:
    err.append("recheck: must work on a full audit without changing its score")

# the plugin's manifests, and the user's files outside the skill's folder
plugin = json.load(open(os.path.join(ASSETS, "..", ".claude-plugin", "plugin.json"), encoding="utf-8"))
market = json.load(open(os.path.join(ASSETS, "..", ".claude-plugin", "marketplace.json"), encoding="utf-8"))
if market["plugins"][0]["name"] != plugin["name"] or market["plugins"][0]["source"] != "./":
    err.append("plugin: the marketplace entry must name the plugin at the repository root")
if f"## {plugin['version']}" not in open(os.path.join(ASSETS, "..", "CHANGELOG.md"), encoding="utf-8").read():
    err.append(f"plugin: version {plugin['version']} is missing from the changelog")
with tempfile.TemporaryDirectory() as home:
    os.makedirs(os.path.join(home, "fonts"))
    open(os.path.join(home, "fonts", "mine.ttf"), "w").close()
    json.dump({"mine": dict(common.load_themes()["signature"], label="Mine")}, open(os.path.join(home, "themes.json"), "w"))
    saved = common.USER_DIR
    common.USER_DIR = home
    themes = common.load_themes()
    if "mine" not in themes or "signature" not in themes or common.asset_file("fonts", "mine.ttf") != os.path.join(home, "fonts", "mine.ttf"):
        err.append("plugin: the user's themes and fonts are not read")
    common.USER_DIR = saved

# the comparison of two audits
load = lambda p: json.load(open(os.path.join(ASSETS, "example", p), encoding="utf-8"))
old, new, qk = load("audit.en.json"), load("remeasure.en.json"), load("quick.en.json")
norm = lambda d: cmp.normalize(d, "en")
R = cmp.compare(norm(old), norm(new))
facts = {"common": 28, "gap": 1.7, "old_score": 4.9, "new_score": 6.6, "same_kind": True, "regressions": 2}
for k, v in facts.items():
    if R[k] != v:
        err.append(f"compare: {k} = {R[k]}, expected {v}")
if ([e["code"] for e in R["worse"]], [e["code"] for e in R["only_new"]], [e["code"] for e in R["only_old"]]) != (["E3"], ["B1"], ["C5"]):
    err.append("compare: criteria sorted wrongly")
if R["panel"]["market"] != {"old": [0, 16], "new": [3, 16], "to_confirm": 1}:
    err.append(f"compare: panel counted wrongly: {R['panel']['market']}")
if {k: len(v) for k, v in R["tasks"].items()} != {"gone": 8, "open": 13, "new": 1}:
    err.append("compare: tasks sorted wrongly")
if cmp.compare(norm(new), norm(old))["gap"] != 1.7:
    err.append("compare: the older audit must always come first")
if cmp.compare(norm(qk), norm(new))["same_kind"] or cmp.compare(norm(qk), norm(new))["tasks"] is not None:
    err.append("compare: a quick audit against a full one must be flagged, without comparing tasks")
pts = lambda a, b: cmp.tool_reading("01", {"text": str(a), "num": a}, {"text": str(b), "num": b})
if (pts(58, 61), pts(58, 65), pts(58, 70), pts(91, 79), pts(50, 50)) != ("noise", "confirm", "better", "worse", "same"):
    err.append("compare: PageSpeed noise rules not applied")
for label, bad in (("another domain", dict(new, site=dict(new["site"], domain="other.example"))),
                   ("another grid", dict(new, criteres=new["criteres"][:25])),
                   ("nothing in common", dict(new, criteres=[[r[0], r[1], "NV", ""] for r in new["criteres"]]))):
    try:
        cmp.compare(norm(old), norm(bad))
        err.append(f"compare: {label} must be refused")
    except cmp.CompareError:
        pass
if cmp.compare(norm(old), norm(dict(new, site=dict(new["site"], domain="www.ATELIER-lumen.example"))))["common"] != 28:
    err.append("compare: www and case must not make two sites")
if cmp.compare(norm(old), norm(dict(new, site=dict(new["site"], domain="other.example"))), force=True)["common"] != 28:
    err.append("compare: --force must allow a domain change")
one = {"questions": {"1": "q"}, "assistants": [{"name": "Google Mode IA", "answers": [{"q": 1, "cited": True, "runs": [True, False, False]}]}, {"name": "S", "kind": "search", "answers": [{"q": 1, "cited": True}]}]}
p = cmp.panel_of(one)
if list(p["assistants"]) != ["Google AI Mode"] or p["assistants"]["Google AI Mode"]["q"]["cited"]:
    err.append("compare: 1 run out of 3 is not a citation, and search results are not an AI answer")
for n in ("compare/*Comparison*.html", "compare/*Comparison*.md", "compare/*Comparison*.json", "compare/fr/*Comparaison*.html"):
    if not glob.glob(os.path.join(out, n)):
        err.append(f"compare: missing {n}")

# what the user test found
E_ = json.load(open(os.path.join(ASSETS, "quick.json"), encoding="utf-8"))
Tfr = common.translator("fr")
for L_ in ("en", "fr"):
    for k_ in ("D3", "D4", "E1", "E2", "E4", "F3", "F4"):
        if not E_[L_]["tasks"][k_].get("questions"):
            err.append(f"questions: {k_} has none in {L_}")
    for k_, v_ in E_[L_]["ev"].items():
        if re.search(r"\{(n|err|bad|js|nc)\} (pages|en-têtes)", v_):
            err.append(f"strings: {k_} depends on a plural: {v_}")
qq = json.load(open(glob.glob(os.path.join(out, "quick", "quick.json"))[0], encoding="utf-8"))
mm = json.loads(json.dumps(qq["measures"]))
good = quick.auto_scores(mm, None, E_["fr"]["ev"])
mm["crawl"].update(errors=0, fake_404_status=404, root={"status": 307, "location": None})
bad_root = quick.auto_scores(mm, None, E_["fr"]["ev"])["A3"]
if bad_root[0] != "1" or "sans dire où aller" not in bad_root[1]:
    err.append(f"root: a redirect that says nowhere to go must not score 2: {bad_root}")
mm["crawl"]["root"] = {"status": 307, "location": "/en"}
if quick.auto_scores(mm, None, E_["fr"]["ev"])["A3"][0] != "2":
    err.append("root: a real redirect is fine")
mm["crawl"]["root"] = {"status": 500, "location": None}
if quick.auto_scores(mm, None, E_["fr"]["ev"])["A3"][0] != "1":
    err.append("root: an error at the root must not score 2")
mm["psi"] = {"status": "ok", "source": "lighthouse", "perf": 91, "a11y": 60}
lh = quick.auto_scores(mm, None, E_["fr"]["ev"])
if lh["B2"][0] != "2" or "Lighthouse" not in lh["B2"][1] or lh["E5"][0] != "0" or "B1" in lh:
    err.append(f"lighthouse: scored wrongly: {lh.get('B2')}, {lh.get('E5')}")
mm2 = json.loads(json.dumps(qq["measures"]))
mm2["crawl"].update(errors=0, fake_404_status=404, root={"status": 307, "location": None})
tt = [{"key": "A3", "name": "x", "what": "y", "check": "z", "lane": "B", "prio": 1, "code": "B1"}]
quick.enrich_tasks(tt, {"site": qq["site"], "measures": mm2, "task_overrides": {}}, {}, "fr")
if tt[0]["name"] != "Faire rediriger l'adresse du site" or "Réparer" in tt[0]["what"] or "redirection" not in tt[0]["what"]:
    err.append(f"root: the task must say what it is about: {tt[0]}")
if common.soft_domain("adalovelace.netlify.app") != "adalovelace.<wbr>netlify.app" or common.soft_domain("site.fr") != "site.fr":
    err.append("domain: it must break once, near its middle")
for doc_ in ("quick-mode.md", "ai-panel.md"):
    if "Look before you ask" not in open(os.path.join(os.path.dirname(ASSETS), "references", doc_), encoding="utf-8").read():
        err.append(f"panel: {doc_} must look for an account before any question")
if common.task_state("B1", "C2", {}, {"tasks": {"B1": {"status": "applied"}}}, Tfr) != (False, "Dans le code, pas encore en ligne"):
    err.append("state: a fix in the code is not done")
if common.task_state("B1", "C2", {"C2": {"status": "fixed"}}, {"tasks": {"B1": {"status": "applied"}}}, Tfr, "1 mai")[0] is not True:
    err.append("state: only a recheck makes a task done")
form = common.answers_form([{"code": "C1", "name": "Mentions", "questions": ["Qui ?"]}], Tfr)
if "C1 · Mentions" not in form or "- Qui ?" not in form:
    err.append(f"form: {form}")
crawl_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "crawl.py"), encoding="utf-8").read()
if 'o["scripts"] >= 5' in crawl_src:
    err.append("rendering: an empty page built by a single script must count as empty")
# a placeholder left in a string reads as a bug
for f_ in glob.glob(os.path.join(out, "quick", "*.html")) + glob.glob(os.path.join(out, "quick", "fr", "*.html")) + glob.glob(os.path.join(out, "quick", "after", "*.html")) + [os.path.join(out, "en", "index.html"), os.path.join(out, "fr", "index.html")]:
    text_ = re.sub(r"<(style|script)\b.*?</\1>", "", open(f_, encoding="utf-8").read(), flags=re.S)
    # the attributes hold the templates of fix.js: only the text a person reads counts
    left_ = re.findall(r"\{[a-z_]+\}", re.sub(r"<[^>]+>", " ", text_))
    if left_:
        err.append(f"placeholders left in {os.path.basename(f_)}: {sorted(set(left_))}")
over = dict(qq, task_overrides={f"X{i}": {"lane": "C", "prio": 3, "name": f"Task {i}", "what": "w", "check": "c"} for i in range(1, 15)})
os.makedirs(os.path.join(out, "many"), exist_ok=True)
json.dump(over, open(os.path.join(out, "many", "quick.json"), "w", encoding="utf-8"))
sub_ = __import__("subprocess").run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "quick.py"), "build", os.path.join(out, "many", "quick.json")], capture_output=True, text=True)
page_ = open(glob.glob(os.path.join(out, "many", "*.html"))[0], encoding="utf-8").read()
if sub_.returncode or 'class="more-tasks"' not in page_ or "Task 14" not in page_ or "Task 14" not in open(glob.glob(os.path.join(out, "many", "*.md"))[0], encoding="utf-8").read():
    err.append("tasks: none may disappear after the first 10")

print("\n".join(err) if err else f"selftest passed: {total['en']} tasks in English, {total['fr']} in French, quick audit rules and comparison checked, outputs in {out}")
sys.exit(1 if err else 0)
