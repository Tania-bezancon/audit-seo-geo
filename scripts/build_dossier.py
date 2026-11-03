#!/usr/bin/env python3
"""Dossier « Comment se porte le site » à partir d'un audit.json.

  python3 build_dossier.py AUDIT.json OUT_DIR [--captures DIR] [--pdf] [--single]

- OUT_DIR/index.html          le dossier en 5 parties + annexes, captures dans OUT_DIR/captures/
- --pdf    OUT_DIR/<date> Audit complet - <domaine>.pdf     (Chrome headless, A4)
- --single OUT_DIR/<date> Audit complet - <domaine> - page unique.html   (captures et police intégrées)

Le contenu commun (outils, rôles, lexique, règles de remesure) vient de assets/defaults.json,
les couleurs et la police de assets/themes.json (clé site.theme)."""
import argparse, base64, html, json, os, re, shutil, subprocess, sys

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(SKILL, "assets")
CHROME = os.environ.get("CHROME") or next(
    (c for c in ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", shutil.which("google-chrome") or "",
                 shutil.which("chromium") or "", shutil.which("chromium-browser") or ""] if c and os.path.exists(c)), "")

ap = argparse.ArgumentParser()
ap.add_argument("audit"); ap.add_argument("out")
ap.add_argument("--captures"); ap.add_argument("--pdf", action="store_true"); ap.add_argument("--single", action="store_true")
args = ap.parse_args()

A = json.load(open(args.audit, encoding="utf-8"))
DEF = json.load(open(os.path.join(ASSETS, "defaults.json"), encoding="utf-8"))
THEMES = json.load(open(os.path.join(ASSETS, "themes.json"), encoding="utf-8"))
S = A["site"]
TH = THEMES[S.get("theme", "signature")]
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
# sans clé « todo », chaque voie est rangée par priorité (P1, P2, P3)
if not A.get("todo"):
    A["todo"] = {L: [[f"{PRIO[n][0]} · {PRIO[n][1]}", [c for c, t in A["tasks"].items() if c[0] == L and t.get("prio", 2) == n]] for n in sorted(PRIO)] for L in VOIES}
    A["todo"] = {L: [g for g in gs if g[1]] for L, gs in A["todo"].items()}

# contrôles de cohérence avant de produire quoi que ce soit
cited = [c for D in A["domaines"].values() for c in D.get("tasks", [])] + A.get("reference", {}).get("tasks", [])
errs = [f"tâche citée mais absente de tasks : {c}" for c in cited if c not in A["tasks"]]
errs += [f"tâche jamais citée dans un domaine : {c}" for c in A["tasks"] if c not in cited]
errs += [f"tâche absente de la to-do : {c}" for c in A["tasks"] if c not in [x for L in A["todo"].values() for _, cs in L for x in cs]]
errs += [f"outil sans fiche : {k}" for D in A["domaines"].values() for k in D.get("tools", []) if k not in A["fiches"]]
errs += [f"critères : {n} au lieu de {N_CRIT}" for n in [len(A["criteres"])] if n != N_CRIT]
errs += [f"tâche d'une voie inconnue : {c} (voies : {', '.join(VOIES)})" for c in A["tasks"] if c[0] not in VOIES]
errs += [f"priorité inconnue pour {c} : {t.get('prio')}" for c, t in A["tasks"].items() if t.get("prio", 2) not in PRIO]
# les notes de « note » doivent être celles de la grille : catégorie = points ÷ (2 × critères vérifiés) × 10,
# globale = moyenne des notes de catégorie arrondies, arrondie à une décimale, avec une virgule
fr = lambda x: f"{x:.1f}".replace(".", ",")
calc = {}
for L in LETTERS:
    v = [int(r[2]) for r in A["criteres"] if r[0][0] == L and r[2] != "NV"]
    calc[L] = round(sum(v) / (2 * len(v)) * 10 + 1e-9, 1) if v else None
    if calc[L] is not None and A["note"]["categories"].get(L) != fr(calc[L]):
        errs.append(f"note de la catégorie {L} : {A['note']['categories'].get(L)} écrit, {fr(calc[L])} d'après les critères")
ok = [x for x in calc.values() if x is not None]
if ok and A["note"]["global"] != fr(round(sum(ok) / len(ok) + 1e-9, 1)):
    errs.append(f"note globale : {A['note']['global']} écrit, {fr(round(sum(ok) / len(ok) + 1e-9, 1))} d'après les catégories")
if errs:
    sys.exit("audit.json incohérent :\n- " + "\n- ".join(errs))
FEU = {"v": ("v", "Bien"), "o": ("o", "À améliorer"), "r": ("r", "À corriger")}
esc = lambda t: html.escape(str(t), quote=False)


def inline(t):
    """**gras**, `code`, [[surligné]] ; le reste est échappé."""
    t = esc(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
    return re.sub(r"\[\[(.+?)\]\]", r"<mark>\1</mark>", t)


def code(t):
    return "<pre>" + re.sub(r"\[\[(.+?)\]\]", r"<mark>\1</mark>", esc(t)) + "</pre>"


def cap(prefix):
    m = [c for c in CAPS if c.startswith(prefix)]
    if not m:
        sys.exit(f"capture introuvable : {prefix}* dans {CAPSRC}")
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
    return f'<div class="role"><p class="lbl">À quoi sert cet outil</p><p>{inline(r)}</p></div>'


def table(head, rows, cls="tbl"):
    h = "".join(f"<th>{esc(x)}</th>" for x in head)
    b = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="{cls}"><table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>'


# ---------- fiches outils ----------
def fiche(key):
    t = A["fiches"][key]
    score = ""
    if t.get("big") or t.get("pills"):
        score = '<div class="score">' + (f'<span class="big num">{esc(t["big"])}</span>' if t.get("big") else "") + "".join(pill(k, p) for k, p in t.get("pills", [])) + "</div>"
    ul = "<ul>" + "".join(f"<li>{inline(b)}</li>" for b in t.get("bullets", [])) + "</ul>" if t.get("bullets") else ""
    says = f'<p class="says">{inline(t["says"])}</p>' if t.get("says") else ""
    return (f'<article class="source"><div class="txt">{role_box(key)}<p class="who">{inline(t["who"])}</p>{score}{ul}{says}</div>'
            f'{fig(t["capture"].rsplit(".", 1)[0], t["caption"])}</article>')


# ---------- tâches ----------
def task(code_, with_who=True):
    t = A["tasks"][code_]
    who = f' · <span class="legend">{WHO[code_[0]]}</span>' if with_who else ""
    chk = f'<span class="check">{inline(t["check"])}</span>' if t.get("check") else ""
    pr = PRIO[t.get("prio", 2)][0]
    return (f'<div class="task"><span class="code">{code_}</span><div><span class="prio p{pr[1]}">{pr}</span><b>{inline(t["name"])}</b>{who}<br>'
            f'{inline(t["what"])}{chk}</div></div>')


def tasks(codes):
    return '<div class="tasks">' + "".join(task(c) for c in codes) + "</div>"


# ---------- blocs des domaines ----------
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
        items = "".join(f"<li><b>{esc(n)} {esc(a)}</b> : {esc(c)}</li>" for n, a, c, _ in b["tri"])
        return f'<div class="grid2">{t}<div class="card"><h3>{esc(b.get("tri_title", ""))}</h3><ul>{items}</ul><p class="prose">{inline(b.get("tri_note", ""))}</p></div></div>'
    if k == "note":
        return f'<div class="note">{inline(b["text"])}</div>'
    if k == "ia":
        return ia_block()
    sys.exit(f"type de bloc inconnu : {k}")


def ia_block():
    I = A["ia"]
    names = [a["name"] for a in I["assistants"]]
    qs = sorted(I["questions"], key=int)
    res = {a["name"]: {str(x["q"]): x for x in a["answers"]} for a in I["assistants"]}
    head = "<tr><th>Question posée</th>" + "".join(f'<th class="c">{esc(n)}</th>' for n in names) + "</tr>"
    rows = ""
    for q in qs:
        cells = ""
        for n in names:
            x = res[n].get(q)
            cells += '<td class="c">' + (pill("na", "—") if not x else pill("ok", "oui") if x["cited"] else pill("bad", "non")) + "</td>"
        rows += f"<tr><td>Q{q} · {esc(I['questions'][q])}</td>{cells}</tr>"
    out = [f'<h3 class="step">Le tableau des réponses</h3><div class="tbl"><table><thead>{head}</thead><tbody>{rows}</tbody></table></div>']
    if I.get("note"):
        out.append(f'<div class="note">{inline(I["note"])}</div>')
    out.append('<h3 class="step">Chaque IA, question par question</h3>')
    if I.get("intro"):
        out.append(f'<p class="prose">{inline(I["intro"])}</p>')
    bq = str(I.get("brand_question", qs[-1]))
    for a in I["assistants"]:
        cat = [x for x in a["answers"] if str(x["q"]) != bq]
        cited = sum(1 for x in cat if x["cited"])
        out.append(f'<div class="ai"><div class="ai-head"><h4>{esc(a["name"])}</h4><span>{esc(a["how"])} · cité dans {cited} réponse{"s" if cited > 1 else ""} sur {len(cat)} sur notre marché</span></div>{role_box(a["name"])}<div class="qgrid">')
        for x in a["answers"]:
            p = pill("ok", "cité") if x["cited"] else pill("bad", "pas cité")
            out.append(f'<div class="qcard"><p class="q">Q{x["q"]} · {esc(I["questions"][str(x["q"])])}</p><div class="r">{p}</div><p>{inline(x["note"])}</p>'
                       f'{fig(x["capture"] + "-", "Capture " + x["capture"] + " · " + a["name"] + ", Q" + str(x["q"]) + ", " + x.get("hour", ""))}</div>')
        out.append("</div></div>")
    return "\n".join(out)


def domain(key):
    D = A["domaines"][key]
    num, label = DOMLAB[key]
    what = (f'<div class="what"><div><p class="lbl">En une phrase</p><p>{inline(D["une"])}</p></div>'
            f'<div><p class="lbl">Pourquoi ça compte</p><p>{inline(D["pourquoi"])}</p></div>'
            f'<div><p class="lbl">Verdict</p>{feu(D["feu"])}<p>{inline(D["verdict"])}</p></div></div>')
    blocks = D.get("blocks", [])
    seen = [b for b in blocks if b["type"] != "ia"]
    out = [f'<section id="{key}"><div class="head"><p class="eyebrow">{num} · {esc(label)}</p><h2>{esc(D["title"])}</h2></div>', what]
    if seen:
        out.append('<h3 class="step">Ce qu\'on voit sur le site</h3>')
        out += [block(b) for b in seen]
    out += [block(b) for b in blocks if b["type"] == "ia"]
    if D.get("tools"):
        out.append(f'<h3 class="step">{esc(D.get("tools_label", "Ce que disent les outils"))}</h3><div class="sources">' + "".join(fiche(k) for k in D["tools"]) + "</div>")
    if D.get("tasks"):
        out.append('<h3 class="step">Ce qu\'on va faire</h3>' + tasks(D["tasks"]))
    return "\n".join(out) + "</section>"


# ---------- examinateurs ----------
def outil_cards():
    groups = {}
    for o in DEF["outils"]:
        groups.setdefault(o["group"], []).append((o["key"], o["name"], o["editor"], o["domain"]))
    groups.setdefault("Ce que savent les IA", [])
    for a in A["ia"]["assistants"]:
        groups["Ce que savent les IA"].append((a["name"], a["name"], ASSIST[a["name"]]["editor"], "d-ia"))
    out = []
    for g, items in groups.items():
        items = [i for i in items if i[0] in A["resultats"]]
        if not items:
            continue
        out.append(f'<p class="outil-group">{esc(g)}</p><div class="outils">')
        for k, n, e, dom in items:
            res, f = A["resultats"][k]
            out.append(f'<div class="outil"><div class="top"><h4>{esc(n)}</h4><span class="ed">{esc(e)}</span></div>{role_box(k)}'
                       f'<div class="res">{feu(f)}<span><b>Le {esc(S["date_label"].rsplit(" ", 1)[0])} :</b> {inline(res)}</span></div>'
                       f'<a href="#{dom}">Voir le détail et la capture →</a></div>')
        out.append("</div>")
    return "\n".join(out), sum(1 for k in A["resultats"])


# ---------- assemblage ----------
def todo_list(letter):
    out = [f'<div class="todo {letter.lower()}"><h3>{WHO[letter]} · {sum(len(c) for _, c in A["todo"][letter])} tâches</h3><p class="legend">{esc(VOIES[letter][1])}</p>']
    for g, codes in A["todo"][letter]:
        out.append(f'<p class="todo-group">{esc(g)}</p>' + "".join(task(c, False) for c in codes))
    return "\n".join(out) + "</div>"


css = open(os.path.join(ASSETS, "dossier.css"), encoding="utf-8").read()
fam = TH["font"].get("css") or f"'{TH['font']['family']}', {TH['font']['fallback']}"
css = re.sub(r"--font: [^;]+;", lambda m: f"--font: {fam};", css, count=1)
# mode clair : on remplace les variables du premier bloc :root ; mode sombre : les couleurs sombres restent celles de dossier.css
head, rest = css.split(":root {", 1)
block_, rest = rest.split("}", 1)
for k, v in TH["css"].items():
    block_ = re.sub(rf"{re.escape(k)}:\s*[^;]+;", f"{k}: {v};", block_)
css = head + ":root {" + block_ + "}" + rest.replace("#22D3BD", TH["css"]["--brand"]).replace("#000B28", TH["css"]["--band"])
# police de la marque : fichiers copiés dans OUT_DIR/fonts (aucun appel réseau)
fontlink = ""
if TH["font"]["files"]:
    fontlink = "<style>" + "".join(f"@font-face{{font-family:'{TH['font']['family']}';font-weight:{w};font-style:normal;font-display:swap;src:url(fonts/{fn}) format('truetype')}}"
                                   for w, fn in TH["font"]["files"]) + "</style>"

n_tasks = len(A["tasks"])
n_p1 = sum(1 for t in A["tasks"].values() if t.get("prio", 2) == 1)
cards, n_ex = outil_cards()
date_short = S["date_label"].rsplit(" ", 1)[0]
cats = {L: (n, short) for L, n, short in DEF["categories"]}
bul = "".join(f'<tr><td><a href="#{k}">{esc(DOMLAB[k][1])}</a></td><td>{feu(A["bulletin"][k][0], FEU[A["bulletin"][k][0]][1])}</td><td>{inline(A["bulletin"][k][1])}</td></tr>' for k in DOMS if k in A["bulletin"])
scores = f'<div class="score global"><span class="v num">{esc(A["note"]["global"])}</span><span class="l">Note globale sur 10</span></div>' + \
    "".join(f'<div class="score"><span class="v num">{esc(v)}</span><span class="l">{esc(cats[L][1])}</span></div>' for L, v in A["note"]["categories"].items())
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
docs = "".join(f'<li>{esc(a)} : ' + (f'<a href="{b}" target="_blank" rel="noopener">{esc(b.split("//", 1)[-1])}</a>' if b.startswith("http") else f"<code>{esc(b)}</code>") + "</li>" for a, b in A.get("documents", []))
ref = "".join(f"<tr><td>{esc(a)}</td><td>{inline(b)}</td><td><b>{esc(c)}</b></td><td>{esc(o)}</td><td></td></tr>" for a, b, c, o in A["reference"]["rows"])
seo = "".join(f'<div class="card"><h3>{esc(a)} : {esc(t.lower()[0] + t[1:])}</h3><p class="prose">{inline(p)}</p></div>' for a, t, p in DEF["seo_geo"])
R = A.get("remesure") or DEF["remesure"]
conc = A.get("concurrents")
evo = A.get("evolution")

page = f"""<!doctype html><html lang="{S.get('lang', 'fr')}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Audit complet {esc(S['domain'])}</title>
{fontlink}
<style>{css}</style></head><body>
<header class="band"><div class="wrap">
  <p class="eyebrow">Audit SEO et GEO · {esc(S['domain'])} · état au {esc(S['date_label'])}</p>
  <h1>Comment se porte le site {esc(S['domain'])}</h1>
  <p class="lead">{inline(A['lead'])}</p>
  <div class="meta"><span><b>Date de la mesure</b> {esc(S['date_long'])}</span><span><b>Note</b> {esc(A['note']['global'])} / 10</span><span><b>Périmètre</b> {esc(S['perimetre'])}</span><span><b>Préparé par</b> {esc(S['prepared_by'])}</span></div>
</div></header>
<div class="wrap layout">
<nav class="toc" aria-label="Sommaire"><p class="title">Sommaire</p><ol>
  <li><a href="#p1">Lire en 5 minutes</a></li>
  <li><a href="#p2">Comprendre la mesure</a><ol><li><a href="#seo-geo">Le SEO et le GEO en mots simples</a></li><li><a href="#examinateurs">Les {n_ex} examinateurs</a></li><li><a href="#conditions">Les conditions de la mesure</a></li></ol></li>
  <li><a href="#p3">L'état du site, domaine par domaine</a><ol>{toc_dom}</ol></li>
  <li><a href="#p4">Agir</a><ol><li><a href="#todo">La to-do</a></li>{'<li><a href="#comparaison">Face aux concurrents</a></li>' if conc else ''}</ol></li>
  <li><a href="#p5">Suivre</a><ol><li><a href="#reference">Le tableau de référence</a></li><li><a href="#remesure">Refaire la mesure</a></li></ol></li>
  <li><a href="#annexes">Annexes</a><ol><li><a href="#a-criteres">Les {N_CRIT} critères</a></li>{'<li><a href="#a-evolution">Depuis l’audit précédent</a></li>' if evo else ''}<li><a href="#a-fautes">Mots collés et fautes</a></li><li><a href="#a-captures">Index des captures</a></li><li><a href="#a-lexique">Lexique</a></li><li><a href="#a-docs">Documents</a></li></ol></li>
</ol></nav>
<main>
<div class="part" id="p1"><div class="part-title"><p class="eyebrow">Partie 1</p><h2>Lire en 5 minutes</h2><p>La note, l'état de chaque domaine en un coup d'œil, et ce qu'on propose.</p></div>
<section><div class="head"><h2>{esc(A['headline'])}</h2></div><div class="scores">{scores}</div>
<p class="prose">La note vient d'une grille fixe de {N_CRIT} critères (annexe A), notés à partir des preuves des {n_ex} examinateurs. Elle servira de point de départ pour mesurer les progrès.</p></section>
<section><div class="head"><h2>Le bulletin de santé, domaine par domaine</h2></div><div class="tbl bulletin"><table><thead><tr><th>Domaine</th><th>État</th><th>En une ligne</th></tr></thead><tbody>{bul}</tbody></table></div></section>
<section><div class="grid3"><div class="card good"><h3>Ce qui va bien</h3>{ul(A['good'])}</div><div class="card bad"><h3>Ce qui bloque</h3>{ul(A['bad'])}</div><div class="card"><h3>Les {len(A['decisions'])} décisions demandées</h3>{ul(A['decisions'])}</div></div></section>
</div>
<div class="part" id="p2"><div class="part-title"><p class="eyebrow">Partie 2</p><h2>Comprendre la mesure</h2><p>Ce qu'on a mesuré, qui l'a mesuré, et dans quelles conditions.</p></div>
<section id="seo-geo"><div class="head"><h2>Le SEO et le GEO en mots simples</h2></div><div class="grid2">{seo}</div></section>
<section id="examinateurs"><div class="head"><h2>Les {n_ex} examinateurs</h2></div><p class="prose">Tous sont gratuits, publics et indépendants de nous : n'importe qui peut refaire la mesure à la même adresse. Chaque carte explique à quoi sert l'outil, ce qu'il a trouvé le {esc(date_short)}, et renvoie au domaine où se trouvent sa capture et le détail.</p>{cards}</section>
<section id="conditions"><div class="head"><h2>Les conditions de la mesure</h2></div><dl class="kv">{''.join(f'<dt>{esc(k)}</dt><dd>{inline(v)}</dd>' for k, v in A['conditions'])}</dl>
<div class="warnbox"><b>Ce que la mesure ne dit pas.</b> {inline(A['limites'])}</div></section>
</div>
<div class="part" id="p3"><div class="part-title"><p class="eyebrow">Partie 3</p><h2>L'état du site, domaine par domaine</h2><p>Chaque domaine se lit de la même façon : ce que c'est, le verdict, ce qu'on voit sur le site, ce que disent les outils, et ce qu'on va faire.</p></div>
{''.join(domain(k) for k in DOMS if k in A['domaines'])}
</div>
<div class="part" id="p4"><div class="part-title"><p class="eyebrow">Partie 4</p><h2>Agir</h2><p>Toutes les tâches, sans dates, en trois to-do : {esc(", ".join(WHO[L] for L in VOIES))}. Chacune a sa priorité, de P1 (bloquant) à P3 (finition).</p></div>
<section id="todo"><div class="head"><h2>La to-do : {n_tasks} tâches, dont {n_p1} bloquantes</h2></div><p class="prose">{inline(A.get('todo_intro', ''))}</p>
<div class="grid3 todos">{''.join(todo_list(L) for L in VOIES if A['todo'].get(L))}</div><div class="card"><h3>Les validations</h3>{ul(A.get('validations', []))}</div></section>
{f'''<section id="comparaison"><div class="head"><h2>{esc(conc['title'])}</h2></div>{table(conc['head'], conc['rows'])}<p class="prose">{inline(conc.get('note', ''))}</p></section>''' if conc else ''}
</div>
<div class="part" id="p5"><div class="part-title"><p class="eyebrow">Partie 5</p><h2>Suivre</h2><p>Toutes les valeurs du {esc(date_short)} en un seul tableau, pour les comparer à chaque nouvelle mesure.</p></div>
<section id="reference"><div class="head"><h2>Le tableau de référence au {esc(S['date_label'])}</h2></div><p class="prose">La colonne « Prochaine mesure » est vide : on la remplit en refaisant les mêmes mesures, dans les mêmes conditions.</p>
<div class="tbl wide ref"><table><thead><tr><th>Domaine</th><th>Mesure</th><th>{esc(date_short)}</th><th>Objectif</th><th>Prochaine mesure</th></tr></thead><tbody>{ref}</tbody></table></div>
<p class="prose">{inline(A['reference'].get('missing', ''))}</p>{tasks(A['reference'].get('tasks', [])) if A['reference'].get('tasks') else ''}</section>
<section id="remesure"><div class="head"><h2>Refaire la mesure, avec les mêmes règles</h2></div><div class="grid2"><div class="card"><h3>Les règles</h3>{ul(R['regles'])}</div><div class="card"><h3>Un progrès ou du hasard ?</h3>{ul(R['bruit'])}</div></div><div class="warnbox">{inline(R['promesse'])}</div></section>
</div>
<div class="part" id="annexes"><div class="part-title"><p class="eyebrow">Annexes</p><h2>Le détail</h2><p>Pour vérifier une note, retrouver une capture ou comprendre un terme.</p></div>
<section id="a-criteres"><div class="head"><p class="eyebrow">Annexe A</p><h2>Les {N_CRIT} critères, avec leur preuve</h2></div><p class="legend">{pill('ok', '2')} correct · {pill('warn', '1')} partiel · {pill('bad', '0')} absent ou faux · {pill('na', 'NV')} non vérifiable, retiré du calcul</p>
<div class="tbl wide"><table><thead><tr><th>#</th><th>Critère</th><th class="c">Note</th><th>Preuve</th></tr></thead><tbody>{''.join(crit)}</tbody></table></div></section>
{f'''<section id="a-evolution"><div class="head"><p class="eyebrow">Annexe B</p><h2>{esc(evo['title'])}</h2></div><p class="prose">{inline(evo.get('intro', ''))}</p>{table(evo['head'], evo['rows'])}</section>''' if evo else ''}
<section id="a-fautes"><div class="head"><p class="eyebrow">Annexe C</p><h2>Mots collés et fautes relevés</h2></div><div class="card"><div class="prose">{fautes_html}</div></div></section>
<section id="a-captures"><div class="head"><p class="eyebrow">Annexe D</p><h2>Index des captures</h2></div><p class="prose">Toutes prises le {esc(S['date_label'])}. Les cadres rouges sont ajoutés pour montrer le défaut.</p>
<div class="tbl wide"><table><thead><tr><th>N°</th><th>Outil ou page</th><th>Ce qu'elle montre</th><th>Heure</th><th>Domaine</th></tr></thead><tbody>{idx}</tbody></table></div></section>
<section id="a-lexique"><div class="head"><p class="eyebrow">Annexe E</p><h2>Lexique</h2></div><dl class="def">{''.join(f'<dt>{esc(t)}</dt><dd>{inline(d)}</dd>' for t, d in (A.get('lexique') or DEF['lexique']))}</dl></section>
<section id="a-docs"><div class="head"><p class="eyebrow">Annexe F</p><h2>Les documents de travail</h2></div><div class="card"><ul>{docs}</ul></div></section>
</div>
</main></div>
<footer><div class="wrap"><p>{esc(S['brand'])} · Comment se porte le site {esc(S['domain'])} · état au {esc(S['date_label'])}</p><p>{inline(A.get('footer_note', ''))}</p></div></footer>
</body></html>"""

assert "{{" not in page
if A.get("competitors_regex"):
    found = re.findall(r".{40}(?:%s).{20}" % A["competitors_regex"], re.sub(r"<img[^>]*>", "", page))
    if found:
        print("ATTENTION : noms de concurrents dans le texte :", found[:3])
os.makedirs(os.path.join(args.out, "captures"), exist_ok=True)
if TH["font"]["files"]:
    os.makedirs(os.path.join(args.out, "fonts"), exist_ok=True)
    for _, fn in TH["font"]["files"]:
        shutil.copy2(os.path.join(ASSETS, "fonts", fn), os.path.join(args.out, "fonts", fn))
used = sorted(set(re.findall(r'captures/([^"]+\.(?:jpg|jpeg|png))', page)))
for c in used:
    shutil.copy2(os.path.join(CAPSRC, c), os.path.join(args.out, "captures", c))
idxf = os.path.join(args.out, "index.html")
open(idxf, "w", encoding="utf-8").write(page)
print("dossier :", idxf, f"({len(used)} captures, {n_tasks} tâches, dont {n_p1} P1)")

# la to-do, à part : une liste à cocher (Markdown) et un tableau à importer (Notion, Jira, Linear, GitHub…)
md = [f"# To-do SEO GEO · {S['domain']}", "", f"État au {S['date_label']} · note {A['note']['global']} / 10 · {n_tasks} tâches, sans dates", ""]
rows = [["Code", "Voie", "Priorité", "Tâche", "Correction", "Vérifié quand"]]
for L in VOIES:
    if not A["todo"].get(L):
        continue
    md += [f"## {WHO[L]}", "", f"_{VOIES[L][1]}_", ""]
    for g, codes in A["todo"][L]:
        md += [f"### {g}", ""]
        for c in codes:
            t = A["tasks"][c]; pr = PRIO[t.get("prio", 2)][0]
            md.append(f"- [ ] **{c} · {t['name']}** ({pr}) : {t['what']}" + (f". _{t['check']}_" if t.get("check") else ""))
            rows.append([c, WHO[L], pr, t["name"], t["what"], t.get("check", "")])
        md.append("")
if A.get("validations"):
    md += ["## Les validations", ""] + [f"- {v}" for v in A["validations"]] + [""]
base_todo = f"{S['date']} To-do SEO GEO - {S['domain']}"
open(os.path.join(args.out, base_todo + ".md"), "w", encoding="utf-8").write("\n".join(md))
import csv
with open(os.path.join(args.out, base_todo + ".csv"), "w", encoding="utf-8-sig", newline="") as f:
    csv.writer(f).writerows(rows)
print("to-do :", base_todo + ".md", "et .csv")
base = f"{S['date']} Audit complet - {S['domain']}"

if args.pdf and not CHROME:
    print("PDF : Chrome introuvable (donner son chemin dans la variable CHROME)")
elif args.pdf:
    prof = os.path.join(args.out, ".chrome")
    pdf = os.path.join(args.out, base + ".pdf")
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", f"--user-data-dir={prof}", "--virtual-time-budget=15000", "--no-pdf-header-footer",
                    f"--print-to-pdf={pdf}", "file://" + os.path.abspath(idxf)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    shutil.rmtree(prof, ignore_errors=True)
    print("PDF :", pdf if os.path.exists(pdf) else "ÉCHEC (vérifier Chrome)")

if args.single:
    h = page
    h = re.sub(r"<style>@font-face[^<]*</style>", "", h, count=1)
    faces = "".join(f"@font-face{{font-family:'{TH['font']['family']}';font-weight:{w};font-style:normal;font-display:swap;src:url(data:font/ttf;base64,"
                    f"{base64.b64encode(open(os.path.join(ASSETS, 'fonts', fn), 'rb').read()).decode()}) format('truetype')}}" for w, fn in TH["font"]["files"])
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
    single = os.path.join(args.out, base + " - page unique.html")
    open(single, "w", encoding="utf-8").write(h)
    print("page unique :", single, round(os.path.getsize(single) / 1e6, 1), "Mo")
