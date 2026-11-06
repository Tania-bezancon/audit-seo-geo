#!/usr/bin/env python3
"""Spelling and grammar with the public LanguageTool API, on what Google reads.

  python3 lt.py CRAWL_DIR [--lang en-GB] [--prefix https://example.com/en]

Reads the titles, descriptions, H1 and H2 collected by crawl.py (no duplicates), in batches, with a pause between two
calls (the public API limits the rate). Writes CRAWL_DIR/lt-<lang>.json, with the page address of each alert. Each alert
still has to be read: a style preference is not a mistake, and proper nouns or technical terms often come out as false positives.
"""
import argparse, json, os, time, urllib.parse, urllib.request

ap = argparse.ArgumentParser()
ap.add_argument("crawl"); ap.add_argument("--lang", default="en-US"); ap.add_argument("--prefix", default="")
a = ap.parse_args()
R = [json.loads(l) for l in open(os.path.join(a.crawl, "crawl.jsonl"))]
R = [r for r in R if r.get("status") == 200 and r["url"].startswith(a.prefix)]
segs, seen = [], set()
for r in R:
    for s in [r.get("title") or "", r.get("desc") or ""] + r.get("h1", []) + r.get("h2", [])[:10]:
        s = s.replace("<BR>", " ").strip()
        if s and s not in seen:
            seen.add(s); segs.append((r["url"], s))
out = []


def check(chunk):
    txt = "\n\n".join(s for _, s in chunk)
    data = urllib.parse.urlencode({"text": txt, "language": a.lang, "disabledRules": "WHITESPACE_RULE,FRENCH_WHITESPACE,UPPERCASE_SENTENCE_START"}).encode()
    for i in range(3):
        try:
            res = json.load(urllib.request.urlopen("https://api.languagetool.org/v2/check", data, timeout=60)); break
        except Exception:
            time.sleep(10)
    else:
        print("LanguageTool API unreachable"); return
    starts, pos = [], 0
    for u, seg in chunk:
        starts.append((pos, u)); pos += len(seg) + 2
    for m in res["matches"]:
        c = m["context"]; t = c["text"]; o = c["offset"]
        url = [u for st, u in starts if st <= m["offset"]][-1]
        out.append({"url": url, "regle": m["rule"]["id"], "message": m["message"], "extrait": t[max(0, o - 25): o + c["length"] + 25],
                    "erreur": t[o: o + c["length"]], "propositions": [x["value"] for x in m["replacements"][:3]]})


chunk, size = [], 0
for u, s in segs:
    chunk.append((u, s)); size += len(s)
    if size > 12000:
        check(chunk); chunk, size = [], 0; time.sleep(4)
if chunk:
    check(chunk)
json.dump(out, open(os.path.join(a.crawl, f"lt-{a.lang}.json"), "w"), ensure_ascii=False, indent=1)
print(f"{len(segs)} texts read, {len(out)} alerts to check one by one")
for o in out:
    print(f"- \"{o['erreur']}\" -> {o['propositions'][:2]} · {o['message'][:70]} · …{o['extrait']}… · {o['url']}")
