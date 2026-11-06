#!/usr/bin/env python3
"""What changed between two audits of the same site.

  python3 compare.py OLD.json NEW.json [OUT_DIR] [--lang en|fr] [--force] [--fail-on-regression]

OLD and NEW are audit.json (full audit) or quick.json (quick audit) files. Writes, next to NEW unless OUT_DIR is given:
a single-file HTML page, a Markdown summary and a JSON result, all named "<new date> Comparison - <domain>".

- The score is compared like for like: only on the criteria checked both times. A criterion that became NV, or stopped
  being NV, is listed on its own and moves nothing.
- A full audit against a quick one uses different evidence: the published scores are not compared, and the report says so.
- Tools follow the noise rules of the method: under 5 PageSpeed points is noise, 5 to 9 is to confirm, 10 or more counts.
- An AI answer that changed only counts as confirmed when the new audit asked the question at least 3 times ("runs").
- A task that left the list is reported as no longer listed, not as done: only a new check proves it was fixed.

--force compares two different domains (after a move, for instance). --fail-on-regression exits with code 3 if a
criterion got worse or a tool clearly dropped, for use in a CI job."""
import argparse, json, os, re, sys
from common import ASSETS, date_label, defaults, fmt_score, font_faces, grid_scores, report_lang, score_value, soft_domain, theme_css, translator
from quick import GRID, LETTERS, build_tasks, esc, inline, pill, score_rows

PAGESPEED = {"01", "09", "a11y"}  # noise rules of the "remesure" block in the defaults
TREND_ONLY = {"18"}  # Similarweb: only a trend confirmed twice counts
FEU_RANK = {"r": 0, "o": 1, "v": 2}
ASSISTANT_ALIASES = {"Google Mode IA": "Google AI Mode"}
EXIT_REGRESSION = 3


class CompareError(Exception):
    pass


def normalize(data, lang):
    """One shape for both kinds of audit: rows, tools, reference values, panel and tasks."""
    S = data.get("site") or {}
    for k in ("domain", "date"):
        if not S.get(k):
            raise CompareError(f"site.{k} is missing")
    if "measures" in data:
        return normalize_quick(data, S, lang)
    if "criteres" in data:
        return normalize_full(data, S, lang)
    raise CompareError("this is neither an audit.json nor a quick.json")


def check_grid(rows):
    codes = sorted(r[0] for r in rows)
    if codes != sorted(GRID):
        raise CompareError(f"the file does not use the 30-criteria grid ({len(codes)} criteria found): compare the findings by hand")


def normalize_full(data, S, lang):
    rows = [[r[0], r[1], str(r[2]), r[3], "audit"] for r in data["criteres"]]
    check_grid(rows)
    names = {o["key"]: o["name"] for o in defaults(lang)["outils"]}
    tools = {}
    for key, (text, feu) in (data.get("resultats") or {}).items():
        if key not in names:  # the assistants are in the panel
            continue
        big = (data.get("fiches") or {}).get(key, {}).get("big")
        tools[key] = {"name": names[key], "text": text, "feu": feu, "num": score_value(big) if key in PAGESPEED else None}
    refs = {r[1]: {"value": r[2], "target": r[3]} for r in (data.get("reference") or {}).get("rows", []) if not r[1].lower().startswith(("score on", "note sur"))}
    tasks = {re.sub(r"\s+", " ", t["name"]).strip().lower(): {"name": t["name"], "code": c, "prio": t.get("prio", 2)} for c, t in (data.get("tasks") or {}).items()}
    return {"kind": "full", "site": S, "rows": rows, "tools": tools, "refs": refs, "panel": panel_of(data.get("ia")), "tasks": tasks}


def normalize_quick(data, S, lang):
    QL = json.load(open(os.path.join(ASSETS, "quick.json"), encoding="utf-8"))[lang]
    T = translator(lang)
    rows, errs = score_rows(data, QL)
    if errs:
        raise CompareError("inconsistent quick.json: " + "; ".join(errs))
    m, names = data["measures"], {o["key"]: o["name"] for o in defaults(lang)["outils"]}
    c, tools = m["crawl"], {}
    if m["psi"]["status"] == "ok":
        if m["psi"].get("perf") is not None:
            tools["01"] = {"name": names["01"], "text": f"{m['psi']['perf']}/100", "feu": None, "num": m["psi"]["perf"]}
        if m["psi"].get("a11y") is not None:
            tools["a11y"] = {"name": T("cmp_tool_a11y"), "text": f"{m['psi']['a11y']}/100", "feu": None, "num": m["psi"]["a11y"]}
    if m["observatory"]["status"] == "ok":
        tools["08"] = {"name": names["08"], "text": f"{m['observatory'].get('grade')} · {m['observatory'].get('score')}/100", "feu": None, "num": None}
    pages = c["pages_ok"]
    refs = {T("cmp_q_pages"): {"value": str(pages), "target": ""},
            T("cmp_q_errors"): {"value": f"{c['errors']} / {c['pages_total']}", "target": "0"},
            T("cmp_q_js"): {"value": f"{c['js_pages']} / {pages}", "target": "0"},
            T("cmp_q_d1"): {"value": f"{c['d1_bad']} / {pages}", "target": "0"},
            T("cmp_q_d2"): {"value": f"{c['d2_bad']} / {pages}", "target": "0"},
            T("cmp_q_headers"): {"value": f"{c['headers']} / 5", "target": "5 / 5"},
            T("cmp_q_ttfb"): {"value": f"{c['ttfb_median']} ms", "target": "< 800 ms"}}
    shown, _, errs = build_tasks(data, rows, QL, limit=None)
    if errs:
        raise CompareError("inconsistent quick.json: " + "; ".join(errs))
    tasks = {t["key"]: {"name": t["name"], "code": t["code"], "prio": t["prio"]} for t in shown}
    return {"kind": "quick", "site": S, "rows": rows, "tools": tools, "refs": refs, "panel": panel_of(data.get("panel")), "tasks": tasks}


def panel_of(P):
    """{assistant: {question text: answer}}. Search-result proxies are not AI answers and are left out."""
    if not P or not P.get("assistants"):
        return None
    questions = {str(k): v for k, v in P.get("questions", {}).items()}
    brand = str(P.get("brand_question", ""))
    out = {"brand": questions.get(brand), "assistants": {}, "names": {}}
    for a in P["assistants"]:
        if a.get("kind", "assistant") != "assistant":
            continue
        key = ASSISTANT_ALIASES.get(a["name"], a["name"])
        out["names"][key] = a["name"]
        answers = {}
        for x in a.get("answers", []):
            q = questions.get(str(x.get("q")))
            if not q:
                continue
            runs = x.get("runs")
            cited = sum(1 for r in runs if r) * 2 > len(runs) if runs else bool(x.get("cited"))
            answers[q] = {"cited": cited, "runs": len(runs) if runs else 1, "hits": sum(1 for r in runs if r) if runs else None}
        out["assistants"][key] = answers
    return out if out["assistants"] else None


def tool_reading(key, old, new):
    if old["text"] == new["text"] and old.get("num") == new.get("num"):
        return "same"
    if key in TREND_ONLY:
        return "confirm"
    if key in PAGESPEED and old.get("num") is not None and new.get("num") is not None:
        gap = new["num"] - old["num"]
        if abs(gap) < 5:
            return "noise"
        if abs(gap) < 10:
            return "confirm"
        return "better" if gap > 0 else "worse"
    if old.get("feu") in FEU_RANK and new.get("feu") in FEU_RANK and old["feu"] != new["feu"]:
        return "better" if FEU_RANK[new["feu"]] > FEU_RANK[old["feu"]] else "worse"
    return "changed"


def compare_panels(old, new):
    if not old or not new:
        return None
    rows, not_compared, market = {}, set(), {"old": [0, 0], "new": [0, 0], "to_confirm": 0}
    shared = [a for a in new["assistants"] if a in old["assistants"]]
    for a in shared:
        o, n = old["assistants"][a], new["assistants"][a]
        not_compared |= set(o) ^ set(n)
        for q in [q for q in n if q in o]:
            changed = o[q]["cited"] != n[q]["cited"]
            status = "same" if not changed else "gained" if n[q]["cited"] else "lost"
            rows.setdefault(q, {})[a] = {"status": status, "cited": n[q]["cited"], "confirmed": n[q]["runs"] >= 3,
                                         "hits": n[q]["hits"], "runs": n[q]["runs"]}
            if q != new["brand"]:
                market["old"][1] += 1; market["new"][1] += 1
                market["old"][0] += o[q]["cited"]; market["new"][0] += n[q]["cited"]
                market["to_confirm"] += n[q]["cited"] and n[q]["runs"] < 3
    if not rows:
        return None
    return {"assistants": shared, "names": new["names"], "rows": rows, "market": market, "not_compared": sorted(not_compared)}


def compare(old, new, force=False):
    if old["site"]["date"] > new["site"]["date"]:
        old, new = new, old
    dom = lambda x: re.sub(r"^www\.", "", x["site"]["domain"].lower())
    if dom(old) != dom(new) and not force:
        raise CompareError(f"these audits are about two different sites ({dom(old)}, {dom(new)}). Use --force after a domain change.")
    a, b = {r[0]: r for r in old["rows"]}, {r[0]: r for r in new["rows"]}
    common = [c for c in GRID if a[c][2] != "NV" and b[c][2] != "NV"]
    if not common:
        raise CompareError("no criterion was checked in both audits: nothing to compare")
    entry = lambda c: {"code": c, "label": b[c][1], "old": a[c][2], "new": b[c][2], "old_evidence": a[c][3], "new_evidence": b[c][3]}
    improved = [entry(c) for c in common if int(b[c][2]) > int(a[c][2])]
    worse = [entry(c) for c in common if int(b[c][2]) < int(a[c][2])]
    only_new = [entry(c) for c in GRID if a[c][2] == "NV" and b[c][2] != "NV"]
    only_old = [entry(c) for c in GRID if a[c][2] != "NV" and b[c][2] == "NV"]
    like = lambda rows: grid_scores([r if r[0] in common else [r[0], r[1], "NV"] for r in rows], LETTERS)
    old_cats, old_all = like(old["rows"])
    new_cats, new_all = like(new["rows"])
    tools = []
    for key, n in new["tools"].items():
        if key in old["tools"]:
            tools.append({"key": key, "name": n["name"], "old": old["tools"][key]["text"], "new": n["text"], "reading": tool_reading(key, old["tools"][key], n)})
    refs = [{"label": k, "old": old["refs"][k]["value"], "new": v["value"], "target": v["target"]} for k, v in new["refs"].items() if k in old["refs"]]
    same_kind = old["kind"] == new["kind"]
    tasks = None
    if same_kind:
        tasks = {"gone": [old["tasks"][k] for k in old["tasks"] if k not in new["tasks"]],
                 "open": [new["tasks"][k] for k in new["tasks"] if k in old["tasks"]],
                 "new": [new["tasks"][k] for k in new["tasks"] if k not in old["tasks"]]}
    tool_worse = [t for t in tools if t["reading"] == "worse"]
    return {"site": {"domain": new["site"]["domain"], "url": new["site"].get("url", ""), "brand": new["site"].get("brand", new["site"]["domain"]), "theme": new["site"].get("theme", "signature")},
            "old": {"date": old["site"]["date"], "kind": old["kind"], "published": grid_scores(old["rows"], LETTERS)[1]},
            "new": {"date": new["site"]["date"], "kind": new["kind"], "published": grid_scores(new["rows"], LETTERS)[1]},
            "same_kind": same_kind, "common": len(common), "old_cats": old_cats, "new_cats": new_cats, "old_score": old_all, "new_score": new_all,
            "gap": round(new_all - old_all + 1e-9, 1), "improved": improved, "worse": worse, "only_new": only_new, "only_old": only_old,
            "unchanged": len(common) - len(improved) - len(worse), "tools": tools, "refs": refs, "panel": compare_panels(old["panel"], new["panel"]),
            "tasks": tasks, "regressions": len(worse) + len(tool_worse)}


def signed(x, lang):
    return ("+" if x > 0 else "") + fmt_score(x, lang).replace("-", "−")


def headline(R, T, lang):
    gap = R["gap"]
    key = "cmp_up" if gap > 0 else "cmp_down" if gap < 0 else "cmp_flat"
    return T(key, d=fmt_score(abs(gap), lang), n=R["common"])


def write_report(R, out_dir, lang):
    T = translator(lang)
    DEF = defaults(lang)
    TH, css = theme_css(R["site"].get("theme", "signature"))
    domain, od, nd = R["site"]["domain"], date_label(R["old"]["date"], lang), date_label(R["new"]["date"], lang)
    fs = lambda x: fmt_score(x, lang) if x is not None else "NV"
    ul = lambda xs: "<ul>" + "".join(f"<li>{inline(x)}</li>" for x in xs) + "</ul>"
    kind = lambda k: T("kind_" + k)
    # the score, like for like
    rows = []
    for L, name, _ in DEF["categories"]:
        o, n = R["old_cats"][L], R["new_cats"][L]
        gap = signed(round(n - o + 1e-9, 1), lang) if o is not None and n is not None else "—"
        rows.append(f"<tr><td>{L}. {esc(name)}</td><td class='num'>{fs(o)}</td><td class='num'>{fs(n)}</td><td class='num'><b>{gap}</b></td></tr>")
    scores = (f'<div class="scores"><div class="score global"><span class="v num">{signed(R["gap"], lang)}</span><span class="l">{T("cmp_gap")}</span></div>'
              f'<div class="score"><span class="v num">{fs(R["old_score"])}</span><span class="l">{esc(od)}</span></div>'
              f'<div class="score"><span class="v num">{fs(R["new_score"])}</span><span class="l">{esc(nd)}</span></div></div>')
    table = (f'<div class="tbl"><table><thead><tr><th>{T("cmp_category")}</th><th>{esc(od)}</th><th>{esc(nd)}</th><th>{T("cmp_gap")}</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>')
    notes = [T("cmp_like_note", n=R["common"], total=len(GRID))]
    if R["same_kind"] and (R["only_new"] or R["only_old"]):
        notes.append(T("cmp_published", old=fs(R["old"]["published"]), new=fs(R["new"]["published"])))
    warn = f'<div class="warnbox">{T("cmp_mixed")}</div>' if not R["same_kind"] else ""
    if R["same_kind"] and R["new"]["kind"] == "quick":
        warn = f'<div class="warnbox">{T("cmp_quick_note")}</div>'

    def crit(items, title, cls):
        if not items:
            return ""
        lines = "".join(
            f'<div class="task"><span class="code">{e["code"]}</span><div>{pill("na" if e["old"] == "NV" else "ok" if e["old"] == "2" else "warn" if e["old"] == "1" else "bad", e["old"])} → '
            f'{pill("na" if e["new"] == "NV" else "ok" if e["new"] == "2" else "warn" if e["new"] == "1" else "bad", e["new"])} <b>{esc(e["label"])}</b><br>{inline(e["new_evidence"] or e["old_evidence"])}</div></div>' for e in items)
        return f'<section class="{cls}"><div class="head"><h2>{title}</h2></div><div class="tasks">{lines}</div></section>'
    criteria = crit(R["improved"], T("cmp_better", n=len(R["improved"])), "up") + crit(R["worse"], T("cmp_worse", n=len(R["worse"])), "down") + \
        crit(R["only_new"], T("cmp_only_new", n=len(R["only_new"])), "") + crit(R["only_old"], T("cmp_only_old", n=len(R["only_old"])), "")
    # tools and reference values
    kinds = {"same": "na", "noise": "na", "confirm": "warn", "better": "ok", "worse": "bad", "changed": "warn"}
    tools = ""
    if R["tools"]:
        moved = sorted(R["tools"], key=lambda t: ["worse", "better", "confirm", "changed", "noise", "same"].index(t["reading"]))
        tools = (f'<section><div class="head"><h2>{T("cmp_tools_title")}</h2></div><div class="tbl"><table><thead><tr><th>{T("idx_tool")}</th><th>{esc(od)}</th><th>{esc(nd)}</th><th>{T("cmp_reading")}</th></tr></thead><tbody>'
                 + "".join(f"<tr><td>{esc(t['name'])}</td><td>{inline(t['old'])}</td><td>{inline(t['new'])}</td><td>{pill(kinds[t['reading']], T('cmp_read_' + t['reading']))}</td></tr>" for t in moved)
                 + "</tbody></table></div></section>")
    changed_refs = [r for r in R["refs"] if r["old"] != r["new"]]
    refs = ""
    if changed_refs:
        refs = (f'<section><div class="head"><h2>{T("cmp_refs_title")}</h2></div><div class="tbl"><table><thead><tr><th>{T("ref_measure")}</th><th>{esc(od)}</th><th>{esc(nd)}</th><th>{T("ref_target")}</th></tr></thead><tbody>'
                + "".join(f"<tr><td>{esc(r['label'])}</td><td>{esc(r['old'])}</td><td><b>{esc(r['new'])}</b></td><td>{esc(r['target'])}</td></tr>" for r in changed_refs) + "</tbody></table></div></section>")
    # AI panel
    P = R["panel"]
    if P:
        def cell(x):
            if not x:
                return pill("na", "—")
            hits = f" {x['hits']}/{x['runs']}" if x["hits"] is not None else ""
            if x["status"] == "same":
                return pill("ok" if x["cited"] else "bad", (T("yes") if x["cited"] else T("no")) + hits)
            label = (T("cmp_gained") if x["status"] == "gained" else T("cmp_lost")) + hits
            return pill("ok" if x["status"] == "gained" else "bad", label) + ("" if x["confirmed"] else f' <span class="legend">{T("cmp_read_confirm")}</span>')
        head = f"<tr><th>{T('q_asked')}</th>" + "".join(f'<th class="c">{esc(P["names"][a])}</th>' for a in P["assistants"]) + "</tr>"
        body = "".join(f"<tr><td>{esc(q)}</td>" + "".join(f'<td class="c">{cell(cs.get(a))}</td>' for a in P["assistants"]) + "</tr>" for q, cs in P["rows"].items())
        mk = P["market"]
        panel = (f'<section><div class="head"><h2>{T("quick_panel_title")}</h2></div><p class="prose">{T("cmp_panel_score", o=mk["old"][0], ot=mk["old"][1], n=mk["new"][0], nt=mk["new"][1], extra=T("cmp_panel_extra", n=mk["to_confirm"]) if mk["to_confirm"] else "")}</p>'
                 f'<div class="tbl"><table><thead>{head}</thead><tbody>{body}</tbody></table></div><p class="prose">{T("cmp_panel_runs")}</p>'
                 + (f'<p class="prose">{T("cmp_panel_other", n=len(P["not_compared"]))}</p>' if P["not_compared"] else "") + "</section>")
    else:
        panel = f'<section><div class="head"><h2>{T("quick_panel_title")}</h2></div><p class="prose">{T("cmp_panel_none")}</p></section>'
    # tasks
    tasks = ""
    if R["tasks"]:
        tl = lambda xs: ul([f"**{x['code']}** · {x['name']}" for x in xs]) if xs else f"<p>{T('cmp_none')}</p>"
        tasks = (f'<section><div class="head"><h2>{T("cmp_tasks_title")}</h2></div><div class="grid3">'
                 f'<div class="card good"><h3>{T("cmp_tasks_gone", n=len(R["tasks"]["gone"]))}</h3>{tl(R["tasks"]["gone"])}</div>'
                 f'<div class="card"><h3>{T("cmp_tasks_open", n=len(R["tasks"]["open"]))}</h3>{tl(R["tasks"]["open"])}</div>'
                 f'<div class="card bad"><h3>{T("cmp_tasks_new", n=len(R["tasks"]["new"]))}</h3>{tl(R["tasks"]["new"])}</div></div>'
                 f'<p class="prose">{T("cmp_tasks_note")}</p></section>')
    Rm = DEF["remesure"]
    title = T("cmp_h1", domain=soft_domain(esc(domain)))
    page = f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{T('cmp_doc_title', domain=esc(domain))}</title>
<style>{font_faces(TH)}{css}</style></head><body>
<header class="band"><div class="wrap">
  <p class="eyebrow">{T('cmp_eyebrow', domain=esc(domain), old=esc(od), new=esc(nd))}</p>
  <h1>{title}</h1>
  <p class="lead">{T('cmp_lead')}</p>
  <div class="meta"><span><b>{esc(od)}</b> {kind(R['old']['kind'])}</span><span><b>{esc(nd)}</b> {kind(R['new']['kind'])}</span><span><b>{T('quick_coverage')}</b> {R['common']} / {len(GRID)}</span></div>
</div></header>
<div class="wrap"><main style="padding-block:48px 96px">
<section><div class="head"><h2>{headline(R, T, lang)}</h2></div>{scores}{warn}{table}<p class="prose">{' '.join(notes)} {T('cmp_unchanged', n=R['unchanged'])}</p></section>
{criteria}{tools}{refs}{panel}{tasks}
<section><div class="head"><h2>{T('noise')}</h2></div><div class="card">{ul(Rm['bruit'])}</div><div class="warnbox">{inline(Rm['promesse'])}</div></section>
</main></div>
<footer><div class="wrap"><p>{T('cmp_footer', brand=esc(R['site']['brand']), domain=esc(domain), old=esc(od), new=esc(nd))}</p></div></footer>
</body></html>"""
    os.makedirs(out_dir, exist_ok=True)
    base = f"{R['new']['date']} {T('cmp_file')} - {domain.replace(':', '-')}"
    paths = {x: os.path.join(out_dir, f"{base}.{x}") for x in ("html", "md", "json")}
    open(paths["html"], "w", encoding="utf-8").write(page)
    json.dump(R, open(paths["json"], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    md = [f"# {T('cmp_h1', domain=domain)}", "", f"{od} → {nd} · {headline(R, T, lang)}", ""]
    if not R["same_kind"]:
        md += [T("cmp_mixed"), ""]
    for items, title_ in ((R["improved"], T("cmp_better", n=len(R["improved"]))), (R["worse"], T("cmp_worse", n=len(R["worse"]))),
                          (R["only_new"], T("cmp_only_new", n=len(R["only_new"]))), (R["only_old"], T("cmp_only_old", n=len(R["only_old"])))):
        if items:
            md += [f"## {title_}", ""] + [f"- **{e['code']} {e['label']}** {e['old']} → {e['new']}" for e in items] + [""]
    if R["tasks"]:
        for key, label in (("gone", "cmp_tasks_gone"), ("open", "cmp_tasks_open"), ("new", "cmp_tasks_new")):
            if R["tasks"][key]:
                md += [f"## {T(label, n=len(R['tasks'][key]))}", ""] + [f"- {x['code']} · {x['name']}" for x in R["tasks"][key]] + [""]
    open(paths["md"], "w", encoding="utf-8").write("\n".join(md))
    return paths


def main():
    ap = argparse.ArgumentParser(description="What changed between two audits of the same site")
    ap.add_argument("old"); ap.add_argument("new"); ap.add_argument("out", nargs="?")
    ap.add_argument("--lang", choices=["en", "fr"]); ap.add_argument("--force", action="store_true"); ap.add_argument("--fail-on-regression", action="store_true")
    a = ap.parse_args()
    try:
        data = [json.load(open(p, encoding="utf-8")) for p in (a.old, a.new)]
    except (OSError, ValueError) as e:
        sys.exit(f"cannot read the two audits, which must be audit.json or quick.json files: {e}")
    lang = report_lang(data[1].get("site") or {}, a.lang)
    try:
        R = compare(normalize(data[0], lang), normalize(data[1], lang), force=a.force)
    except CompareError as e:
        sys.exit(f"cannot compare: {e}")
    paths = write_report(R, a.out or os.path.dirname(os.path.abspath(a.new)), lang)
    print(f"{R['old']['date']} → {R['new']['date']}: {signed(R['gap'], 'en')} on {R['common']} criteria checked both times, {len(R['improved'])} better, {len(R['worse'])} worse")
    print("report:", paths["html"])
    if a.fail_on_regression and R["regressions"]:
        print(f"{R['regressions']} regressions")
        sys.exit(EXIT_REGRESSION)


if __name__ == "__main__":
    main()
