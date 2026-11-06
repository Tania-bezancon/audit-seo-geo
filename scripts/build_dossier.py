#!/usr/bin/env python3
"""The full audit report, from an audit.json.

  python3 build_dossier.py AUDIT.json OUT_DIR [--captures DIR] [--pdf] [--single] [--lang en|fr]

- OUT_DIR/index.html          the report in 5 parts + appendices, screenshots in OUT_DIR/captures/
- --pdf    OUT_DIR/<date> Full audit - <domain>.pdf     (headless Chrome, A4)
- --single OUT_DIR/<date> Full audit - <domain> - single page.html   (screenshots and font embedded)
- the to-do list as Markdown and CSV

Report language: --lang, then site.report_lang, then site.lang when supported, then English.
Fixed strings come from assets/ui.json, shared content (tools, roles, glossary, remeasure rules) from
assets/defaults.<lang>.json, colours and font from assets/themes.json (key site.theme)."""
import argparse, base64, html, json, os, re, shutil, subprocess, sys
from fixes import stack_name
from common import ASSETS, HOSTED, UI, asset_file, repair_block, repair_kind, repair_line, open_questions, task_questions, task_state, defaults, apply_recheck, date_label, first_html, fix_html, fix_script, font_faces, grid_gain, looks_html, md_details, progress_html, signed_gain, soft_domain, task_marks, view_html, who_html, fmt_score, grid_scores, plural, report_lang, score_value, theme_css, translator

CHROME = os.environ.get("CHROME") or next(
    (c for c in ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", shutil.which("google-chrome") or "",
                 shutil.which("chromium") or "", shutil.which("chromium-browser") or ""] if c and os.path.exists(c)), "")

ap = argparse.ArgumentParser()
ap.add_argument("audit"); ap.add_argument("out")
ap.add_argument("--captures"); ap.add_argument("--pdf", action="store_true"); ap.add_argument("--single", action="store_true")
ap.add_argument("--lang", choices=["en", "fr"])
args = ap.parse_args()

A = json.load(open(args.audit, encoding="utf-8"))
S = A["site"]
LANG = report_lang(S, args.lang)
T = translator(LANG)
SEP = T("sep")
DEF = defaults(LANG)
TH, css = theme_css(S.get("theme", "signature"))
CAPSRC = args.captures or os.path.join(os.path.dirname(os.path.abspath(args.audit)), "captures")
CAPS = sorted(f for f in os.listdir(CAPSRC) if f.lower().endswith((".jpg", ".jpeg", ".png")))
OUTILS = {o["key"]: o for o in DEF["outils"]}
ASSIST = {a["key"]: a for a in DEF["assistants"]}
DOMS = A.get("domain_order") or [d[0] for d in DEF["domaines"]]
DOMLAB = {k: (n, l) for k, n, l, _ in DEF["domaines"]}
DOMSHORT = {k: c for k, _, _, c in DEF["domaines"]}
VOIES = {k: (n, court, detail) for k, n, court, detail in DEF["voies"]}
WHO = {k: v[0] for k, v in VOIES.items()} | S.get("who", {})
PRIO = {n: (code_, label) for n, code_, label, _ in DEF["priorites"]}
LETTERS = [c[0] for c in DEF["categories"]]
N_CRIT = 5 * len(LETTERS)
# without a "todo" key, each lane is sorted by priority (P1, P2, P3)
if not A.get("todo"):
    A["todo"] = {L: [[f"{PRIO[n][0]} · {PRIO[n][1]}", [c for c, t in A["tasks"].items() if c[0] == L and t.get("prio", 2) == n]] for n in sorted(PRIO)] for L in VOIES}
    A["todo"] = {L: [g for g in gs if g[1]] for L, gs in A["todo"].items()}

# consistency checks before producing anything
cited = [c for D in A["domaines"].values() for c in D.get("tasks", [])] + A.get("reference", {}).get("tasks", [])
errs = [f"task cited but missing from tasks: {c}" for c in cited if c not in A["tasks"]]
errs += [f"task never cited in a domain: {c}" for c in A["tasks"] if c not in cited]
errs += [f"task missing from the to-do: {c}" for c in A["tasks"] if c not in [x for L in A["todo"].values() for _, cs in L for x in cs]]
errs += [f"tool without a card: {k}" for D in A["domaines"].values() for k in D.get("tools", []) if k not in A["fiches"]]
errs += [f"criteria: {n} instead of {N_CRIT}" for n in [len(A["criteres"])] if n != N_CRIT]
errs += [f"task in an unknown lane: {c} (lanes: {', '.join(VOIES)})" for c in A["tasks"] if c[0] not in VOIES]
errs += [f"unknown priority for {c}: {t.get('prio')}" for c, t in A["tasks"].items() if t.get("prio", 2) not in PRIO]
# the scores in "note" must be those of the grid; "5.1" and "5,1" are both accepted, then written for the report language
calc, calc_global = grid_scores(A["criteres"], LETTERS)
for L in LETTERS:
    if calc[L] is not None and score_value(A["note"]["categories"].get(L)) != calc[L]:
        errs.append(f"category {L} score: {A['note']['categories'].get(L)} written, {calc[L]} from the criteria")
if calc_global is not None and score_value(A["note"]["global"]) != calc_global:
    errs.append(f"overall score: {A['note']['global']} written, {calc_global} from the categories")
if errs:
    sys.exit("inconsistent audit.json:\n- " + "\n- ".join(errs))
A["note"]["global"] = fmt_score(A["note"]["global"], LANG)
A["note"]["categories"] = {L: fmt_score(v, LANG) for L, v in A["note"]["categories"].items()}
FEU = {k: (k, T("feu_" + k)) for k in "vor"}
esc = lambda t: html.escape(str(t), quote=False)


def inline(t):
    """**bold**, `code`, [[highlight]]; the rest is escaped."""
    t = esc(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
    return re.sub(r"\[\[(.+?)\]\]", r"<mark>\1</mark>", t)


def code(t):
    return "<pre>" + re.sub(r"\[\[(.+?)\]\]", r"<mark>\1</mark>", esc(t)) + "</pre>"


def cap(prefix):
    m = [c for c in CAPS if c.startswith(prefix)]
    if not m:
        sys.exit(f"screenshot not found: {prefix}* in {CAPSRC}")
    return "captures/" + m[0]


def fig(prefix, caption):
    src = cap(prefix)
    return (f'<figure><a href="{src}" target="_blank" rel="noopener"><img src="{src}" alt="{html.escape(caption)}" loading="lazy"></a>'
            f"<figcaption>{esc(caption)}</figcaption></figure>")


def feu(f, label=None):
    c, l = FEU[f]
    return f'<span class="feu {c}">{esc(label or l)}</span>'


def pill(kind, t):
    return f'<span class="pill {kind}">{esc(t)}</span>'


def role_box(key):
    r = OUTILS.get(key, ASSIST.get(key))["role"]
    return f'<div class="role"><p class="lbl">{T("role_title")}</p><p>{inline(r)}</p></div>'


def table(head, rows, cls="tbl"):
    h = "".join(f"<th>{esc(x)}</th>" for x in head)
    b = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="{cls}"><table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>'


# ---------- tool cards ----------
def fiche(key):
    t = A["fiches"][key]
    score = ""
    if t.get("big") or t.get("pills"):
        score = '<div class="score">' + (f'<span class="big num">{esc(t["big"])}</span>' if t.get("big") else "") + "".join(pill(k, p) for k, p in t.get("pills", [])) + "</div>"
    ul = "<ul>" + "".join(f"<li>{inline(b)}</li>" for b in t.get("bullets", [])) + "</ul>" if t.get("bullets") else ""
    says = f'<p class="says">{inline(t["says"])}</p>' if t.get("says") else ""
    return (f'<article class="source"><div class="txt">{role_box(key)}<p class="who">{inline(t["who"])}</p>{score}{ul}{says}</div>'
            f'{fig(t["capture"].rsplit(".", 1)[0], t["caption"])}</article>')


# ---------- tasks ----------
def task(code_, with_who=True):
    t = A["tasks"][code_]
    who = f' · <span class="legend">{WHO[code_[0]]}</span>' if with_who else ""
    chk = f'<span class="check">{inline(t["check"])}</span>' if t.get("check") else ""
    pr = PRIO[t.get("prio", 2)][0]
    # the chapters give the whole card; the three narrow to-do columns stay a summary
    fix = fix_html({**t, "questions": open_questions({"questions": task_questions({**t, "key": code_, "lane": code_[0]}, LANG, T)}, REPAIR.get("tasks", {}).get(code_))}, T, inline, esc) if with_who else ""
    anchor = f' id="t-{code_}"' if with_who else ""
    result = RECHECK.get(t.get("criterion")) if t.get("criterion") else None
    entry = REPAIR.get("tasks", {}).get(code_)
    kind = None if (S.get("stack") or {}).get("framework") in HOSTED else repair_kind({**t, "key": code_, "lane": code_[0]})
    box, marks = task_marks(code_, t.get("criterion"), GAIN.get(code_), result, T, LANG, RC_DATE, entry, kind)
    if with_who:
        chk += repair_line(entry, REPAIR.get("branch"), T, inline)
    return (f'<div class="task"{anchor}><span class="code">{box}{code_}</span><div><span class="prio p{pr[1]}">{pr}</span><b>{inline(t["name"])}</b>{who}{marks}<br>'
            f'{inline(t["what"])}{fix}{chk}</div></div>')


def tasks(codes):
    return '<div class="tasks">' + "".join(task(c) for c in codes) + "</div>"


# ---------- domain blocks ----------
def block(b):
    k = b["type"]
    if k == "finding":
        txt = [f'<p class="where">{inline(b["where"])}</p>'] if b.get("where") else []
        txt += [f"<p>{inline(p)}</p>" for p in b.get("paras", [])]
        if b.get("list"):
            txt.append("<ul>" + "".join(f"<li>{inline(x)}</li>" for x in b["list"]) + "</ul>")
        if b.get("code"):
            txt.append(code(b["code"]))
        caps = b.get("captures", [])
        figs = "".join(fig(p, c) for p, c in caps)
        if b.get("note"):
            note = f'<div class="note">{inline(b["note"])}</div>'
            if caps:
                txt.append(note)
            else:
                figs = note
        cls = "figs pair" if len(caps) == 2 else "figs"
        return f'<div class="finding"><div class="txt">{"".join(txt)}</div><div class="{cls}">{figs}</div></div>'
    if k == "table":
        return table(b["head"], b["rows"], "tbl wide")
    if k == "stats":
        out = ""
        if b.get("role"):
            out += f'<div class="outil"><div class="top"><h4>{esc(b.get("role_title", ""))}</h4></div>{role_box(b["role"])}</div>'
        return out + f'<div class="tbl"><table><thead><tr>{"".join(f"<th>{esc(h)}</th>" for h in b["head"])}</tr></thead><tbody class="num">' + \
            "".join(f"<tr><td>{inline(a)}</td><td><b>{inline(v)}</b></td></tr>" for a, v in b["rows"]) + "</tbody></table></div>"
    if k == "tri":
        t = f'<div class="tbl"><table><thead><tr>{"".join(f"<th>{esc(h)}</th>" for h in b["head"])}</tr></thead><tbody class="num">' + \
            "".join(f"<tr><td>{inline(a)}</td><td><b>{inline(v)}</b></td></tr>" for a, v in b["rows"]) + "</tbody></table></div>"
        items = "".join(f"<li><b>{esc(n)} {esc(a)}</b>{SEP}{esc(c)}</li>" for n, a, c, _ in b["tri"])
        return f'<div class="grid2">{t}<div class="card"><h3>{esc(b.get("tri_title", ""))}</h3><ul>{items}</ul><p class="prose">{inline(b.get("tri_note", ""))}</p></div></div>'
    if k == "note":
        return f'<div class="note">{inline(b["text"])}</div>'
    if k == "ia":
        return ia_block()
    sys.exit(f"unknown block type: {k}")


def ia_block():
    I = A["ia"]
    names = [a["name"] for a in I["assistants"]]
    qs = sorted(I["questions"], key=int)
    res = {a["name"]: {str(x["q"]): x for x in a["answers"]} for a in I["assistants"]}
    head = f"<tr><th>{T('q_asked')}</th>" + "".join(f'<th class="c">{esc(n)}</th>' for n in names) + "</tr>"
    rows = ""
    for q in qs:
        cells = ""
        for n in names:
            x = res[n].get(q)
            cells += '<td class="c">' + (pill("na", "—") if not x else pill("ok", T("yes")) if x["cited"] else pill("bad", T("no"))) + "</td>"
        rows += f"<tr><td>Q{q} · {esc(I['questions'][q])}</td>{cells}</tr>"
    out = [f'<h3 class="step">{T("answers_table")}</h3><div class="tbl"><table><thead>{head}</thead><tbody>{rows}</tbody></table></div>']
    if I.get("note"):
        out.append(f'<div class="note">{inline(I["note"])}</div>')
    out.append(who_html(I["assistants"], I.get("brand_question", qs[-1]), T, esc))
    out.append(f'<h3 class="step">{T("each_ai")}</h3>')
    if I.get("intro"):
        out.append(f'<p class="prose">{inline(I["intro"])}</p>')
    bq = str(I.get("brand_question", qs[-1]))
    for a in I["assistants"]:
        cat = [x for x in a["answers"] if str(x["q"]) != bq]
        cited = sum(1 for x in cat if x["cited"])
        out.append(f'<div class="ai"><div class="ai-head"><h4>{esc(a["name"])}</h4><span>{esc(a["how"])} · {T("cited_in", n=cited, total=len(cat), word=plural(LANG, cited, "answer") if LANG == "fr" else "")}</span></div>{role_box(a["name"])}<div class="qgrid">')
        for x in a["answers"]:
            p = pill("ok", T("cited")) if x["cited"] else pill("bad", T("not_cited"))
            out.append(f'<div class="qcard"><p class="q">Q{x["q"]} · {esc(I["questions"][str(x["q"])])}</p><div class="r">{p}</div><p>{inline(x["note"])}</p>'
                       f'{fig(x["capture"] + "-", T("screenshot") + " " + x["capture"] + " · " + a["name"] + ", Q" + str(x["q"]) + ", " + x.get("hour", ""))}</div>')
        out.append("</div></div>")
    return "\n".join(out)


def domain(key):
    D = A["domaines"][key]
    num, label = DOMLAB[key]
    what = (f'<div class="what"><div><p class="lbl">{T("one_sentence")}</p><p>{inline(D["une"])}</p></div>'
            f'<div><p class="lbl">{T("why")}</p><p>{inline(D["pourquoi"])}</p></div>'
            f'<div><p class="lbl">{T("verdict")}</p>{feu(D["feu"])}<p>{inline(D["verdict"])}</p></div></div>')
    blocks = D.get("blocks", [])
    seen = [b for b in blocks if b["type"] != "ia"]
    out = [f'<section id="{key}"><div class="head"><p class="eyebrow">{num} · {esc(label)}</p><h2>{esc(D["title"])}</h2></div>', what]
    if seen:
        out.append(f'<h3 class="step">{T("seen")}</h3>')
        out += [block(b) for b in seen]
    out += [block(b) for b in blocks if b["type"] == "ia"]
    if D.get("tools"):
        out.append(f'<h3 class="step">{esc(D.get("tools_label", T("tools_say")))}</h3><div class="sources">' + "".join(fiche(k) for k in D["tools"]) + "</div>")
    if D.get("tasks"):
        out.append(f'<h3 class="step">{T("todo_do")}</h3>' + tasks(D["tasks"]))
    return "\n".join(out) + "</section>"


# ---------- examiners ----------
def outil_cards():
    groups = {}
    for o in DEF["outils"]:
        groups.setdefault(o["group"], []).append((o["key"], o["name"], o["editor"], o["domain"]))
    groups.setdefault(T("group_ai"), [])
    for a in A["ia"]["assistants"]:
        groups[T("group_ai")].append((a["name"], a["name"], ASSIST[a["name"]]["editor"], "d-ia"))
    out = []
    for g, items in groups.items():
        items = [i for i in items if i[0] in A["resultats"]]
        if not items:
            continue
        out.append(f'<p class="outil-group">{esc(g)}</p><div class="outils">')
        for k, n, e, dom in items:
            res, f = A["resultats"][k]
            out.append(f'<div class="outil"><div class="top"><h4>{esc(n)}</h4><span class="ed">{esc(e)}</span></div>{role_box(k)}'
                       f'<div class="res">{feu(f)}<span><b>{T("on_date", date=esc(S["date_label"].rsplit(" ", 1)[0]))}</b> {inline(res)}</span></div>'
                       f'<a href="#{dom}">{T("see_detail")}</a></div>')
        out.append("</div>")
    return "\n".join(out), sum(1 for k in A["resultats"])


# ---------- assembly ----------
def todo_list(letter):
    out = [f'<div class="todo {letter.lower()}"><h3>{T("todo_lane", who=WHO[letter], n=sum(len(c) for _, c in A["todo"][letter]))}</h3><p class="legend">{esc(VOIES[letter][1])}</p>']
    for g, codes in A["todo"][letter]:
        out.append(f'<p class="todo-group">{esc(g)}</p>' + "".join(task(c, False) for c in codes))
    return "\n".join(out) + "</div>"


# the brand font: files copied to OUT_DIR/fonts (no network call)
fontlink = ""
if TH["font"]["files"]:
    fontlink = "<style>" + font_faces(TH, "fonts/") + "</style>"

n_tasks = len(A["tasks"])
n_p1 = sum(1 for t in A["tasks"].values() if t.get("prio", 2) == 1)
cards, n_ex = outil_cards()
date_short = S["date_label"].rsplit(" ", 1)[0]
cats = {L: (n, short) for L, n, short in DEF["categories"]}
bul = "".join(f'<tr><td><a href="#{k}">{esc(DOMLAB[k][1])}</a></td><td>{feu(A["bulletin"][k][0], FEU[A["bulletin"][k][0]][1])}</td><td>{inline(A["bulletin"][k][1])}</td></tr>' for k in DOMS if k in A["bulletin"])
RC = A.get("recheck") or {}
REPAIR = A.get("repair") or {}
RECHECK = RC.get("results", {})
RC_DATE = date_label(RC["date"], LANG) if RC.get("date") else ""
ROWS_NOW = apply_recheck(A["criteres"], RECHECK)
GAIN = {c: grid_gain(ROWS_NOW, t["criterion"]) for c, t in A["tasks"].items() if t.get("criterion")}
scores = looks_html(A["criteres"], esc(A["note"]["global"]), T, LANG, "a-criteres")
first_list = [c for c in A.get("first", []) if c in A["tasks"]] or sorted(A["tasks"], key=lambda c: (A["tasks"][c].get("prio", 2), list(A["tasks"]).index(c)))[:3]
first_block = first_html([(c, A["tasks"][c]["name"], WHO[c[0]] + (" · " + signed_gain(GAIN[c], LANG) if GAIN.get(c) else "")) for c in first_list], T, inline)
progress_block = progress_html(ROWS_NOW, [(c, t.get("criterion")) for c, t in A["tasks"].items()], f"{S['domain']}:{S['date']}", fmt_score(grid_scores(ROWS_NOW, LETTERS)[1], LANG), T, LANG, T("rc_summary", n=sum(1 for v in RECHECK.values() if v["status"] == "fixed"), date=RC_DATE) if RC_DATE else "")
_all = [{**t, "code": c, "key": c, "lane": c[0], "kind": repair_kind({**t, "key": c, "lane": c[0]}), "questions": task_questions({**t, "key": c, "lane": c[0]}, LANG, T)} for c, t in A["tasks"].items()]
progress_block += repair_block([t["kind"] for t in _all], REPAIR, S.get("stack"), T, esc, _all)
view_block = view_html(A.get("view"), T, inline, esc, LANG, lambda p: cap(p + "-"))
ul = lambda xs: "<ul>" + "".join(f"<li>{inline(x)}</li>" for x in xs) + "</ul>"
toc_dom = "".join(f'<li><a href="#{k}">{esc(DOMLAB[k][1])}</a></li>' for k in DOMS if k in A["domaines"])
crit = []
for L, n, _ in DEF["categories"]:
    crit.append(f'<tr class="cat"><td colspan="4"><b>{L}. {esc(n)}</b> · {esc(A["note"]["categories"][L])} / 10</td></tr>')
    for c, k, note, p in [r for r in A["criteres"] if r[0][0] == L]:
        cls = {"0": "bad", "1": "warn", "2": "ok"}.get(note, "na")
        crit.append(f"<tr><td class='num'>{c}</td><td>{inline(k)}</td><td class='c'>{pill(cls, note)}</td><td>{inline(p)}</td></tr>")
fautes = []
for kind, t in A.get("fautes", []):
    fautes.append(f"<li>{inline(t)}</li>" if kind == "li" else f"<p><i>{inline(t)}</i></p>" if kind == "note" else f"<p><b>{inline(t)}</b></p>")
fautes_html = re.sub(r"(<li>.*?</li>)+", lambda m: "<ul>" + m.group(0) + "</ul>", "".join(fautes))
idx = "".join(f'<tr><td class="num"><a href="{cap(k + "-")}" target="_blank" rel="noopener">{k}</a></td><td>{esc(a)}</td><td>{esc(b)}</td><td>{esc(h)}</td><td><a href="#{d}">{esc(DOMSHORT[d])}</a></td></tr>'
              for k, (a, b, h, d) in A["captures"].items())
docs = "".join(f'<li>{esc(a)}{SEP}' + (f'<a href="{b}" target="_blank" rel="noopener">{esc(b.split("//", 1)[-1])}</a>' if b.startswith("http") else f"<code>{esc(b)}</code>") + "</li>" for a, b in A.get("documents", []))
ref = "".join(f"<tr><td>{esc(a)}</td><td>{inline(b)}</td><td><b>{esc(c)}</b></td><td>{esc(o)}</td><td></td></tr>" for a, b, c, o in A["reference"]["rows"])
seo = "".join(f'<div class="card"><h3>{esc(a)}{SEP}{esc(t.lower()[0] + t[1:])}</h3><p class="prose">{inline(p)}</p></div>' for a, t, p in DEF["seo_geo"])
R = A.get("remesure") or DEF["remesure"]
conc = A.get("concurrents")
evo = A.get("evolution")

stack_label = stack_name(S.get("stack"), LANG)
stack_line = f'<p class="stack"><span class="lbl">{T("stack_label")}</span> <b>{esc(stack_label)}</b></p>' if stack_label else ""
page = f"""<!doctype html><html lang="{LANG}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{T('doc_title', domain=esc(S['domain']))}</title>
{fontlink}
<style>{css}</style></head><body>
<header class="band"><div class="wrap">
  <p class="eyebrow">{T('eyebrow', domain=esc(S['domain']), date=esc(S['date_label']))}</p>
  <h1>{T('h1', domain=soft_domain(esc(S['domain'])))}</h1>
  <p class="lead">{inline(A['lead'])}</p>
  <div class="meta"><span><b>{T('meta_date')}</b> {esc(S['date_long'])}</span><span><b>{T('meta_score')}</b> {esc(A['note']['global'])} / 10</span><span><b>{T('meta_scope')}</b> {esc(S['perimetre'])}</span><span><b>{T('meta_by')}</b> {esc(S['prepared_by'])}</span></div>
</div></header>
<div class="wrap layout">
<nav class="toc" aria-label="{T('toc_aria')}"><p class="title">{T('toc')}</p><ol>
  <li><a href="#p1">{T('p1_title')}</a></li>
  <li><a href="#p2">{T('p2_title')}</a><ol><li><a href="#seo-geo">{T('seo_geo_title')}</a></li><li><a href="#examinateurs">{T('examiners_title', n=n_ex)}</a></li><li><a href="#conditions">{T('conditions_title')}</a></li></ol></li>
  <li><a href="#p3">{T('p3_title')}</a><ol>{toc_dom}</ol></li>
  <li><a href="#p4">{T('p4_title')}</a><ol><li><a href="#todo">{T('todo_title')}</a></li>{f'<li><a href="#comparaison">{T("versus_title")}</a></li>' if conc else ''}</ol></li>
  <li><a href="#p5">{T('p5_title')}</a><ol><li><a href="#reference">{T('reference_title')}</a></li><li><a href="#remesure">{T('remeasure_title')}</a></li></ol></li>
  <li><a href="#annexes">{T('annex_eyebrow')}</a><ol><li><a href="#a-criteres">{T('criteria_title', n=N_CRIT)}</a></li>{f'<li><a href="#a-evolution">{T("since_title")}</a></li>' if evo else ''}<li><a href="#a-fautes">{T('typos_title')}</a></li><li><a href="#a-captures">{T('index_title')}</a></li><li><a href="#a-lexique">{T('lexicon_title')}</a></li><li><a href="#a-docs">{T('docs_title')}</a></li></ol></li>
</ol></nav>
<main>
<div class="part" id="p1"><div class="part-title"><p class="eyebrow">{T('p1_eyebrow')}</p><h2>{T('p1_title')}</h2><p>{T('p1_sub')}</p></div>
<section><div class="head"><h2>{esc(A['headline'])}</h2></div>{scores}
<p class="prose">{T('score_intro', crit=N_CRIT, ex=n_ex)}</p></section>
<section><div class="head"><h2>{T('bulletin_title')}</h2></div><div class="tbl bulletin"><table><thead><tr><th>{T('bulletin_domain')}</th><th>{T('bulletin_state')}</th><th>{T('bulletin_line')}</th></tr></thead><tbody>{bul}</tbody></table></div></section>
<section><div class="grid3"><div class="card good"><h3>{T('good')}</h3>{ul(A['good'])}</div><div class="card bad"><h3>{T('bad')}</h3>{ul(A['bad'])}</div><div class="card"><h3>{T('decisions', n=len(A['decisions']))}</h3>{ul(A['decisions'])}</div></div></section>
{first_block}
{view_block}
</div>
<div class="part" id="p2"><div class="part-title"><p class="eyebrow">{T('p2_eyebrow')}</p><h2>{T('p2_title')}</h2><p>{T('p2_sub')}</p></div>
<section id="seo-geo"><div class="head"><h2>{T('seo_geo_title')}</h2></div><div class="grid2">{seo}</div></section>
<section id="examinateurs"><div class="head"><h2>{T('examiners_title', n=n_ex)}</h2></div><p class="prose">{T('examiners_intro', date=esc(date_short))}</p>{cards}</section>
<section id="conditions"><div class="head"><h2>{T('conditions_title')}</h2></div><dl class="kv">{''.join(f'<dt>{esc(k)}</dt><dd>{inline(v)}</dd>' for k, v in A['conditions'])}</dl>
<div class="warnbox"><b>{T('limits')}</b> {inline(A['limites'])}</div></section>
</div>
<div class="part" id="p3"><div class="part-title"><p class="eyebrow">{T('p3_eyebrow')}</p><h2>{T('p3_title')}</h2><p>{T('p3_sub')}</p></div>
{''.join(domain(k) for k in DOMS if k in A['domaines'])}
</div>
<div class="part" id="p4"><div class="part-title"><p class="eyebrow">{T('p4_eyebrow')}</p><h2>{T('p4_title')}</h2><p>{T('p4_sub', lanes=esc(", ".join(WHO[L] for L in VOIES)))}</p></div>
<section id="todo"><div class="head"><h2>{T('todo_heading', n=n_tasks, p1=n_p1)}</h2></div><p class="prose">{inline(A.get('todo_intro', ''))}</p>{stack_line}{progress_block}
<div class="grid3 todos">{''.join(todo_list(L) for L in VOIES if A['todo'].get(L))}</div><div class="card"><h3>{T('validations')}</h3>{ul(A.get('validations', []))}</div></section>
{f'''<section id="comparaison"><div class="head"><h2>{esc(conc['title'])}</h2></div>{table(conc['head'], conc['rows'])}<p class="prose">{inline(conc.get('note', ''))}</p></section>''' if conc else ''}
</div>
<div class="part" id="p5"><div class="part-title"><p class="eyebrow">{T('p5_eyebrow')}</p><h2>{T('p5_title')}</h2><p>{T('p5_sub', date=esc(date_short))}</p></div>
<section id="reference"><div class="head"><h2>{T('reference_heading', date=esc(S['date_label']))}</h2></div><p class="prose">{T('reference_intro')}</p>
<div class="tbl wide ref"><table><thead><tr><th>{T('ref_domain')}</th><th>{T('ref_measure')}</th><th>{esc(date_short)}</th><th>{T('ref_target')}</th><th>{T('ref_next')}</th></tr></thead><tbody>{ref}</tbody></table></div>
<p class="prose">{inline(A['reference'].get('missing', ''))}</p>{tasks(A['reference'].get('tasks', [])) if A['reference'].get('tasks') else ''}</section>
<section id="remesure"><div class="head"><h2>{T('remeasure_heading')}</h2></div><div class="grid2"><div class="card"><h3>{T('rules')}</h3>{ul(R['regles'])}</div><div class="card"><h3>{T('noise')}</h3>{ul(R['bruit'])}</div></div><div class="warnbox">{inline(R['promesse'])}</div></section>
</div>
<div class="part" id="annexes"><div class="part-title"><p class="eyebrow">{T('annex_eyebrow')}</p><h2>{T('annex_title')}</h2><p>{T('annex_sub')}</p></div>
<section id="a-criteres"><div class="head"><p class="eyebrow">{T('annex_a')}</p><h2>{T('criteria_heading', n=N_CRIT)}</h2></div><p class="legend">{pill('ok', '2')} {T('legend_2')} · {pill('warn', '1')} {T('legend_1')} · {pill('bad', '0')} {T('legend_0')} · {pill('na', 'NV')} {T('legend_nv')}</p>
<div class="tbl wide"><table><thead><tr><th>#</th><th>{T('crit_col')}</th><th class="c">{T('crit_score')}</th><th>{T('crit_proof')}</th></tr></thead><tbody>{''.join(crit)}</tbody></table></div></section>
{f'''<section id="a-evolution"><div class="head"><p class="eyebrow">{T('annex_b')}</p><h2>{esc(evo['title'])}</h2></div><p class="prose">{inline(evo.get('intro', ''))}</p>{table(evo['head'], evo['rows'])}</section>''' if evo else ''}
<section id="a-fautes"><div class="head"><p class="eyebrow">{T('annex_c')}</p><h2>{T('typos_heading')}</h2></div><div class="card"><div class="prose">{fautes_html}</div></div></section>
<section id="a-captures"><div class="head"><p class="eyebrow">{T('annex_d')}</p><h2>{T('index_title')}</h2></div><p class="prose">{T('index_intro', date=esc(S['date_label']))}</p>
<div class="tbl wide"><table><thead><tr><th>{T('idx_no')}</th><th>{T('idx_tool')}</th><th>{T('idx_what')}</th><th>{T('idx_hour')}</th><th>{T('idx_domain')}</th></tr></thead><tbody>{idx}</tbody></table></div></section>
<section id="a-lexique"><div class="head"><p class="eyebrow">{T('annex_e')}</p><h2>{T('lexicon_title')}</h2></div><dl class="def">{''.join(f'<dt>{esc(t)}</dt><dd>{inline(d)}</dd>' for t, d in (A.get('lexique') or DEF['lexique']))}</dl></section>
<section id="a-docs"><div class="head"><p class="eyebrow">{T('annex_f')}</p><h2>{T('docs_heading')}</h2></div><div class="card"><ul>{docs}</ul></div></section>
</div>
</main></div>
{fix_script()}
<footer><div class="wrap"><p>{T('footer', brand=esc(S['brand']), domain=esc(S['domain']), date=esc(S['date_label']))}</p><p>{inline(A.get('footer_note', ''))}</p></div></footer>
</body></html>"""

assert "{{" not in page
if A.get("competitors_regex"):
    found = re.findall(r".{40}(?:%s).{20}" % A["competitors_regex"], re.sub(r"<img[^>]*>", "", page))
    if found:
        print("WARNING: competitor names in the text:", found[:3])
os.makedirs(os.path.join(args.out, "captures"), exist_ok=True)
if TH["font"]["files"]:
    os.makedirs(os.path.join(args.out, "fonts"), exist_ok=True)
    for _, fn, *_ in TH["font"]["files"]:
        shutil.copy2(asset_file("fonts", fn), os.path.join(args.out, "fonts", fn))
used = sorted(set(re.findall(r'captures/([^"]+\.(?:jpg|jpeg|png))', page)))
for c in used:
    shutil.copy2(os.path.join(CAPSRC, c), os.path.join(args.out, "captures", c))
idxf = os.path.join(args.out, "index.html")
open(idxf, "w", encoding="utf-8").write(page)
print("report:", idxf, f"({len(used)} screenshots, {n_tasks} tasks, {n_p1} P1)")

# the to-do on its own: a checklist (Markdown) and a table to import (Notion, Jira, Linear, GitHub...)
md = ["# " + T("md_title", domain=S["domain"]), "", T("md_sub", date=S["date_label"], score=A["note"]["global"], n=n_tasks), ""]
rows = [list(UI[LANG]["csv_head"])]
for L in VOIES:
    if not A["todo"].get(L):
        continue
    md += [f"## {WHO[L]}", "", f"_{VOIES[L][1]}_", ""]
    for g, codes in A["todo"][L]:
        md += [f"### {g}", ""]
        for c in codes:
            t = A["tasks"][c]; pr = PRIO[t.get("prio", 2)][0]
            done, state = task_state(c, t.get("criterion"), RECHECK, REPAIR, T, RC_DATE)
            md.append(f"- [{'x' if done else ' '}] **{c} · {t['name']}** ({pr}){SEP}{t['what'].rstrip('. ')}" + (f". _{t['check'].rstrip('. ')}_" if t.get("check") else "") + (f" **{state}**" if state else ""))
            md += md_details({**t, "questions": open_questions({"questions": task_questions({**t, "key": c, "lane": c[0]}, LANG, T)}, REPAIR.get("tasks", {}).get(c))}, T)
            rows.append([c, WHO[L], pr, t["name"], t["what"], t.get("check", ""), t.get("where", ""), t.get("file", ""), state])
        md.append("")
if A.get("validations"):
    md += ["## " + T("validations"), ""] + [f"- {v}" for v in A["validations"]] + [""]
base_todo = f"{S['date']} {T('file_todo')} - {S['domain']}"
open(os.path.join(args.out, base_todo + ".md"), "w", encoding="utf-8").write("\n".join(md))
import csv
with open(os.path.join(args.out, base_todo + ".csv"), "w", encoding="utf-8-sig", newline="") as f:
    csv.writer(f).writerows(rows)
print("to-do:", base_todo + ".md", "and .csv")
base = f"{S['date']} {T('file_audit')} - {S['domain']}"

if args.pdf and not CHROME:
    print("PDF: Chrome not found (set its path in the CHROME variable)")
elif args.pdf:
    prof = os.path.join(args.out, ".chrome")
    pdf = os.path.join(args.out, base + ".pdf")
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", f"--user-data-dir={prof}", "--virtual-time-budget=15000", "--no-pdf-header-footer",
                    f"--print-to-pdf={pdf}", "file://" + os.path.abspath(idxf)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    shutil.rmtree(prof, ignore_errors=True)
    print("PDF:", pdf if os.path.exists(pdf) else "FAILED (check Chrome)")

if args.single:
    h = page
    h = re.sub(r"<style>@font-face[^<]*</style>", "", h, count=1)
    faces = font_faces(TH)
    h = h.replace("<style>", "<style>" + faces, 1)
    data = {}
    def uri(n):
        if n not in data:
            mime = "image/png" if n.lower().endswith(".png") else "image/jpeg"
            data[n] = f"data:{mime};base64," + base64.b64encode(open(os.path.join(CAPSRC, n), "rb").read()).decode()
        return data[n]
    h = re.sub(r'<a href="captures/([^"]+)" target="_blank" rel="noopener">(<img [^>]*>)</a>', r"\2", h)
    h = re.sub(r'<a href="captures/([^"]+)" target="_blank" rel="noopener">([^<]*)</a>', r'<a href="#" class="zoom" data-cap="\1">\2</a>', h)
    h = re.sub(r'src="captures/([^"]+)"', lambda m: f'src="{uri(m.group(1))}" class="zoomable" data-cap="{m.group(1)}"', h)
    store = "".join(f'<template id="cap-{n}"><img src="{uri(n)}" alt=""></template>' for n in sorted(set(re.findall(r'data-cap="([^"]+)"', h)) - set(data)))
    lb = open(os.path.join(ASSETS, "lightbox.html"), encoding="utf-8").read()
    h = h.replace("</body>", store + lb + "</body>")
    single = os.path.join(args.out, f"{base} - {T('file_single')}.html")
    open(single, "w", encoding="utf-8").write(h)
    print("single page:", single, round(os.path.getsize(single) / 1e6, 1), "MB")
