#!/usr/bin/env python3
"""The defects fixed in 1.1, so that they do not come back.

  python3 tests/v11_test.py OUT_DIR"""
import json, os, re, shutil, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import fixes

out = os.path.join(sys.argv[1], "v11")
shutil.rmtree(out, ignore_errors=True)
os.makedirs(out)

# 1. the same page with and without a final slash is one entry of llms.txt
pages = [{"url": "https://site.example", "title": "Home", "desc": "d", "lang": "fr"}, {"url": "https://site.example/", "title": "Home", "desc": "d", "lang": "fr"},
         {"url": "https://site.example/about", "title": "About", "desc": "a", "lang": "fr"}]
_, llms = fixes.llms_file(pages, "https://site.example/", "Site", "fr")
assert llms.count("- [Home]") == 1, llms

# 2. the draft policy lets through the fonts, scripts and frames the pages load
csp = fixes.csp_value({"style": ["fonts.googleapis.com"], "script": ["js.example"], "frame": ["calendly.com"]})
for want in ("style-src 'self' 'unsafe-inline' https://fonts.googleapis.com", "font-src 'self' https://fonts.gstatic.com", "script-src 'self' 'unsafe-inline' https://js.example", "frame-src 'self' https://calendly.com"):
    assert want in csp, (want, csp)
name, body = fixes.headers_file({}, "netlify", "fr", {"style": ["fonts.googleapis.com"]})
assert name == "_headers" and "fonts.gstatic.com" in body, body

# a travel agency already says who runs the site: no Organization block to add
import re as _re
from common import ORG_TYPES
assert _re.search(ORG_TYPES, "TravelAgency") and not _re.search(ORG_TYPES, "FAQPage")

# 3. the full report takes a share image given as an address, and a tool without a screenshot cited in a domain
A = json.load(open(os.path.join(ROOT, "assets", "example", "audit.fr.json"), encoding="utf-8"))
A["view"]["share"]["image"] = "https://www.atelier-lumen.example/og.jpg"
A["resultats"]["lt"] = ["Aucune faute", "v"]
A["fiches"].pop("lt", None)
dom = next(iter(A["domaines"]))
A["domaines"][dom]["tools"] = A["domaines"][dom].get("tools", []) + ["lt"]
src = os.path.join(out, "audit.json")
json.dump(A, open(src, "w", encoding="utf-8"), ensure_ascii=False)
r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "build_dossier.py"), src, os.path.join(out, "report"), "--captures", os.path.join(ROOT, "assets", "example", "captures-fr")], capture_output=True, text=True)
assert r.returncode == 0, r.stdout + r.stderr
page = open(os.path.join(out, "report", "index.html"), encoding="utf-8").read()
assert "https://www.atelier-lumen.example/og.jpg" in page
assert re.search(r"LanguageTool", page)
print("v11 checked: one home page in llms.txt, organisation kinds recognised, a policy open to the site's own hosts, a share image as an address, a tool without a screenshot")
