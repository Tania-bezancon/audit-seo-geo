#!/usr/bin/env python3
"""Fautes d'orthographe et de grammaire avec l'API publique de LanguageTool, sur ce que Google lit.

  python3 lt.py CRAWL_DIR [--lang fr] [--prefix https://exemple.com/fr]

Relit les titres, descriptions, H1 et H2 relevés par crawl.py (sans doublons), par paquets, avec une pause entre deux
appels (l'API publique limite le débit). Écrit CRAWL_DIR/lt-<lang>.json, avec l'adresse de la page de chaque alerte. Chaque alerte reste à relire : une préférence
de style n'est pas une faute, et les noms propres ou l'anglais technique sortent souvent en faux positifs.
"""
import argparse, json, os, time, urllib.parse, urllib.request

ap = argparse.ArgumentParser()
ap.add_argument("crawl"); ap.add_argument("--lang", default="fr"); ap.add_argument("--prefix", default="")
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
        print("API LanguageTool injoignable"); return
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
print(f"{len(segs)} textes relus, {len(out)} alertes à vérifier une par une")
for o in out:
    print(f"- « {o['erreur']} » → {o['propositions'][:2]} · {o['message'][:70]} · …{o['extrait']}… · {o['url']}")
