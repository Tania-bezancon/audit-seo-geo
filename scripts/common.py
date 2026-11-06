"""What build_dossier.py and quick.py share: report language, strings, scores and theme CSS."""
import base64, json, os, re, shutil

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(SKILL, "assets")
# what belongs to the user: the skill's own folder is replaced at each plugin update
USER_DIR = os.environ.get("AUDIT_SEO_GEO_HOME") or os.path.join(os.path.expanduser("~"), ".claude", "audit-seo-geo")
LANGS = ("en", "fr")
UI = json.load(open(os.path.join(ASSETS, "ui.json"), encoding="utf-8"))


# what Claude can do in a site's code, what needs the person's own facts, what happens off the code. task.repair overrides it
REPAIR_KIND = {"A1": "code", "A2": "code", "A3": "code", "A4": "code", "A5": "code", "B1": "code", "B2": "code", "B3": "code", "B4": "code", "B5": "code",
               "C1": "outside", "C2": "file", "C3": "outside", "C4": "outside", "C5": "facts", "D1": "code", "D2": "code", "D3": "facts", "D4": "facts", "D5": "facts",
               "E1": "facts", "E2": "facts", "E3": "code", "E4": "facts", "E5": "code", "F1": "code", "F2": "file", "F3": "facts", "F4": "facts", "F5": "outside"}
PLACEABLE = ("_headers", "vercel.json", "llms.txt")
HOSTED = ("wordpress", "webflow", "shopify", "wix", "squarespace")  # fixed in the platform's admin, not in a folder of code


def task_questions(t, lang, T):
    """What only the person can say, for a task that needs it. Nothing for the others."""
    if repair_kind(t) != "facts":
        return []
    base = json.load(open(os.path.join(ASSETS, "quick.json"), encoding="utf-8"))[lang]["tasks"].get(t.get("criterion") or t.get("key"), {})
    return t.get("questions") or base.get("questions") or [T("repair_questions_default")]


def open_questions(t, entry):
    """What is still unanswered: once a task is in the code, only what its commit left open."""
    return (entry.get("open") or []) if entry and entry.get("status") == "applied" else t.get("questions") or []


def waiting_tasks(tasks, done):
    """The tasks that still need something from the person, with only what is still open."""
    out = []
    for t in tasks:
        qs = open_questions(t, done.get(t["code"]))
        if t.get("kind") == "facts" and qs:
            out.append({**t, "questions": qs})
    return out


def answers_form(tasks, T, audit=None, site=None):
    """The form a person fills in and pastes to have Claude carry on. tasks: those that still need their facts."""
    out = [T("repair_answers_intro", audit=audit or T("repair_folder_audit"), site=site or T("repair_folder_site")), ""]
    for t in tasks:
        out.append(f"{t['code']} · {t['name']}")
        out += [f"- {q}\n  → " for q in t.get("questions", [])]
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def task_state(code, criterion, recheck, repair, T, date_text=""):
    """(done, words) for a to-do: only a recheck of the live site makes a task done."""
    result = recheck.get(criterion) if criterion else None
    if result and result["status"] == "fixed":
        return True, T("rc_fixed", date=date_text)
    entry = (repair or {}).get("tasks", {}).get(code)
    if entry and entry["status"] == "applied":
        return False, T("repair_applied")
    if entry and entry["status"] == "blocked":
        return False, T("repair_blocked")
    return False, T("rc_" + result["status"], date=date_text) if result else ""


def repair_kind(t):
    crit = t.get("criterion") or t.get("key")
    kind = t.get("repair") or REPAIR_KIND.get(crit) or ("facts" if t.get("lane") == "C" else "code")
    if kind == "file" and os.path.basename(t.get("file") or "") not in PLACEABLE:
        return "code" if crit == "F2" else "outside"
    return kind


def find_chrome():
    return os.environ.get("CHROME") or next((c for c in ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", shutil.which("google-chrome") or "",
                                                         shutil.which("chromium") or "", shutil.which("chromium-browser") or ""] if c and os.path.exists(c)), "")


def report_lang(site, override=None):
    """--lang, then site.report_lang, then site.lang when it is supported, then English."""
    for c in (override, site.get("report_lang"), site.get("lang")):
        if c and c[:2].lower() in LANGS:
            return c[:2].lower()
    return "en"


def translator(lang):
    strings = UI[lang]

    def T(key, **kw):
        s = strings[key]
        for k, v in kw.items():
            s = s.replace("{" + k + "}", str(v))
        return s
    return T


def plural(lang, n, key):
    one = n <= 1 if lang == "fr" else n == 1
    return UI[lang][key + ("_one" if one else "_other")]


def defaults(lang):
    return json.load(open(os.path.join(ASSETS, f"defaults.{lang}.json"), encoding="utf-8"))


def score_value(s):
    """5.1 from "5,1" or "5.1"; None for anything else (NV, empty)."""
    try:
        return float(str(s).replace(",", "."))
    except ValueError:
        return None


def fmt_score(x, lang):
    v = score_value(x)
    if v is None:
        return x
    s = f"{v:.1f}"
    return s.replace(".", ",") if lang == "fr" else s


def grid_scores(rows, letters):
    """rows = [[code, label, "0"|"1"|"2"|"NV", ...]]. Category = points / (2 x checked criteria) x 10,
    overall = mean of the rounded category scores, rounded to one decimal."""
    cats = {}
    for L in letters:
        v = [int(r[2]) for r in rows if r[0][0] == L and r[2] != "NV"]
        cats[L] = round(sum(v) / (2 * len(v)) * 10 + 1e-9, 1) if v else None
    ok = [x for x in cats.values() if x is not None]
    return cats, (round(sum(ok) / len(ok) + 1e-9, 1) if ok else None)


def date_label(iso, lang):
    y, m, d = iso.split("-")
    return translator(lang)("date_label", day=int(d), month=UI[lang]["months"][int(m) - 1], year=y)


def asset_file(kind, name):
    """A font or a logo: the user's copy first, then the skill's."""
    mine = os.path.join(USER_DIR, kind, name)
    return mine if os.path.exists(mine) else os.path.join(ASSETS, kind, name)


def brand_logo(TH):
    """A theme's logo at the top of the report, kept inside the file. logos.report in the theme."""
    name = (TH.get("logos") or {}).get("report")
    if not name:
        return ""
    data = base64.b64encode(open(asset_file("logos", name), "rb").read()).decode()
    return f'<img class="brand-logo" src="data:image/{"svg+xml" if name.endswith(".svg") else "png"};base64,{data}" alt="">'


def fix_script():
    return "<script>" + open(os.path.join(ASSETS, "fix.js"), encoding="utf-8").read() + "</script>"


def fix_html(t, T, inline, esc):
    """What makes a task applicable: before and after, where, how, code to copy, a ready file. All optional."""
    def code(text):
        return f'<div class="fix-code"><button type="button" class="copy" data-done="{T("fix_copied")}">{T("fix_copy")}</button><pre>{esc(text)}</pre></div>'

    def side(v, cls, label):
        if isinstance(v, dict):
            body = f'<p class="serp-url">{esc(v.get("url", ""))}</p><p class="serp-title">{inline(v.get("title", ""))}</p>' + (f'<p class="serp-desc">{inline(v["desc"])}</p>' if v.get("desc") else "")
        else:
            body = f"<p>{inline(v)}</p>"
        return f'<div class="ba {cls}"><p class="lbl">{label}</p>{body}</div>'
    out = []
    if t.get("before") and t.get("after"):
        out.append(f'<div class="bas">{side(t["before"], "was", T("fix_before"))}{side(t["after"], "now", T("fix_after"))}</div>')
    if t.get("where"):
        out.append(f'<p class="fix-line"><span class="lbl">{T("fix_where")}</span> {inline(t["where"])}</p>')
    if t.get("how"):
        out.append(f'<p class="fix-line"><span class="lbl">{T("fix_how")}</span> {inline(t["how"])}</p>')
    if t.get("questions"):
        asks = "".join(f"<li>{inline(q)}</li>" for q in t["questions"])
        out.append(f'<div class="fix-line asks"><span class="lbl">{T("fix_asks")}</span><ul>{asks}</ul></div>')
    if t.get("snippet"):
        out.append(code(t["snippet"]))
    if t.get("file"):
        name = esc(t["file"])
        if t.get("file_content"):
            out.append(f'<details class="fix-file"><summary><span class="lbl">{T("fix_ready")}</span> <code>{name}</code></summary>{code(t["file_content"])}</details>')
        else:
            out.append(f'<p class="fix-line"><span class="lbl">{T("fix_ready")}</span> <code>{name}</code></p>')
    return f'<div class="fix">{"".join(out)}</div>' if out else ""


LOOKS = (("google", "A"), ("visitors", "BE"), ("server", "C"), ("copy", "D"), ("ai", "F"))


def looks_html(rows, score, T, lang, anchor):
    """The opening: the overall score and five looks at the site, each with one light. Thresholds as in the PowerPoint's bars."""
    cells = [f'<a class="look global" href="#{anchor}"><span class="v num">{score}</span><span class="n">{T("score_global")}</span></a>']
    for key, letters in LOOKS:
        vals = [int(r[2]) for r in rows if r[0][0] in letters and r[2] != "NV"]
        known = sum(1 for r in rows if r[0][0] in letters)
        count = f'<span class="cnt">{T("look_count", n=len(vals), total=known)}</span>' if vals and len(vals) < known else ""
        if vals:
            v = round(sum(vals) / (2 * len(vals)) * 10 + 1e-9, 1)
            cls = "r" if v < 4 else "o" if v < 7 else "v"
            mark = f'<span class="feu {cls}">{fmt_score(v, lang)}</span>'
        else:
            mark = f'<span class="feu nv">{T("look_nv")}</span>'
        cells.append(f'<a class="look" href="#{anchor}"><span class="n">{T("look_" + key)}</span><span class="q">{T("look_" + key + "_q")}</span>{mark}{count}</a>')
    return f'<div class="looks">{"".join(cells)}</div>'


def first_html(items, T, inline):
    """items = [(code, name, lane)]. Three numbered cards leading to the full task."""
    cards = "".join(f'<a class="first" href="#t-{code}"><span class="i num">{i}</span><b>{inline(name)}</b><span class="l">{inline(lane)}</span></a>' for i, (code, name, lane) in enumerate(items[:3], 1))
    return f'<section id="first"><div class="head"><h2>{T("first_title")}</h2></div><div class="firsts">{cards}</div></section>' if cards else ""


def view_html(view, T, inline, esc, lang, img=lambda p: p):
    """The site seen from outside: on Google, shared, read by a robot. img() turns a stored image into something a page can show."""
    if not view:
        return ""
    parts = []
    g, s = view.get("google"), view.get("share")
    if g:
        title, desc = g.get("title") or T("view_no_title"), g.get("desc") or T("view_no_desc")
        cut = lambda t, n: t if len(t) <= n else t[:n - 1].rstrip() + "…"
        parts.append(f'<div class="view-card"><p class="lbl">{T("view_google")}</p><p class="serp-url">{esc(g.get("url", ""))}</p><p class="serp-title">{esc(cut(title, 62))}</p><p class="serp-desc">{esc(cut(desc, 158))}</p><p class="legend">{T("view_google_note")}</p></div>')
    if s:
        pic = img(s.get("image")) if s.get("image") else None
        media = f'<img src="{esc(pic)}" alt="" loading="lazy">' if pic else f'<div class="share-none">{T("view_no_image")}</div>'
        small = f'<p class="legend warn-txt">{T("view_small_image", w=s["width"], h=s["height"])}</p>' if pic and s.get("width", 1200) < 1200 else ""
        parts.append(f'<div class="view-card"><p class="lbl">{T("view_share")}</p><div class="share">{media}<div class="share-txt"><p class="serp-url">{esc(s.get("domain", ""))}</p><p class="share-title">{esc(s.get("title") or T("view_no_title"))}</p><p class="serp-desc">{esc(s.get("desc") or T("view_no_desc"))}</p></div></div>{small}</div>')
    out = [f'<div class="grid2 view-top">{"".join(parts)}</div>'] if parts else []
    for p in view.get("pages", []):
        state = "empty" if p.get("words", 0) < 80 else "thin" if p.get("words", 0) < 300 else "ok"
        pill_cls = {"empty": "bad", "thin": "warn", "ok": "ok"}[state]
        shot = img(p.get("image")) if p.get("image") else None
        left = f'<figure class="seen"><p class="lbl">{T("view_visitor")}</p><img src="{esc(shot)}" alt="" loading="lazy"></figure>' if shot else ""
        out.append(f'<div class="robot-row{" solo" if not shot else ""}">{left}<div class="robot"><p class="lbl">{T("view_robot")}</p><p class="robot-url">{esc(p.get("url", ""))}</p>'
                   f'<p class="robot-n"><span class="num">{T("view_words", n=p.get("words", 0))}</span> <span class="pill {pill_cls}">{T("view_state_" + state)}</span></p><pre>{esc(p.get("excerpt") or T("view_nothing"))}</pre></div></div>')
    return f'<section id="view"><div class="head"><h2>{T("view_title")}</h2></div>{"".join(out)}</section>' if out else ""


def who_html(assistants, brand_q, T, esc):
    """Who the assistants cite instead, across the market answers."""
    from collections import Counter
    c = Counter()
    for a in assistants:
        if a.get("kind", "assistant") != "assistant":
            continue
        for x in a.get("answers", []):
            if str(x.get("q")) != str(brand_q):
                c.update(set(x.get("cited_instead") or []))
    if not c:
        return ""
    top = c.most_common()
    most = top[0][1]
    rows = "".join(f'<li><span class="who-n">{esc(n)}</span><span class="who-bar"><i style="width:{round(v / most * 100)}%"></i></span><span class="who-c num">{v}</span></li>' for n, v in top[:8])
    more = f'<p class="legend">{T("who_more", n=len(top) - 8)}</p>' if len(top) > 8 else ""
    return f'<div class="who"><h3>{T("who_title")}</h3><ul>{rows}</ul>{more}<p class="legend">{T("who_note")}</p></div>'


def grid_gain(rows, criterion, letters="ABCDEF"):
    """What the overall score would gain if this criterion were correct. On the audit's score, not on any ranking."""
    row = next((r for r in rows if r[0] == criterion), None)
    if not row or row[2] in ("2", "NV"):
        return 0
    _, now = grid_scores(rows, letters)
    _, then = grid_scores([[r[0], r[1], "2", *r[3:]] if r[0] == criterion else r for r in rows], letters)
    return round(then - now + 1e-9, 1)


def apply_recheck(rows, results):
    """The rows as they stand after a recheck: what got better replaces what the audit measured."""
    return [[r[0], r[1], results[r[0]]["new"], *r[3:]] if r[0] in results and results[r[0]]["status"] in ("fixed", "better") else r for r in rows]


def signed_gain(g, lang):
    return "+" + fmt_score(g, lang)


def task_marks(code, criterion, gain, result, T, lang, date_text="", repair=None, kind=None):
    """The tick box, the gain, what the last recheck found, and where the fix stands in the code."""
    verified = result and result["status"] == "fixed"
    box = f'<input class="done" type="checkbox" data-code="{code}" data-crit="{criterion or ""}" data-verified="{1 if verified else 0}" aria-label="{T("done_label", code=code)}">'
    chips = f' <span class="gain">{T("gain_chip", g=signed_gain(gain, lang))}</span>' if gain else ""
    if result:
        cls = {"fixed": "ok", "better": "warn", "same": "na", "worse": "bad"}[result["status"]]
        chips += f' <span class="pill {cls}">{T("rc_" + result["status"], date=date_text)}</span>'
    state = (repair or {}).get("status")
    if state == "applied" and not verified:
        chips += f' <span class="pill warn">{T("repair_applied")}</span>'
    elif state == "blocked":
        chips += f' <span class="pill na">{T("repair_blocked")}</span>'
    elif kind and not result and not state:
        chips += f' <span class="kind k-{kind}">{T("repair_kind_" + kind)}</span>'
    return box, chips


def repair_line(entry, branch, T, inline):
    """What was done in the code for this task. Not a proof that it is online: only a recheck says that."""
    if not entry:
        return ""
    line = T("repair_line", commit=entry["commits"][-1], branch=branch) if entry["status"] == "applied" else ""
    note = entry.get("note") or ""
    return f'<span class="rc-line">{inline((line + " " + note).strip())}</span>' if line or note else ""


def repair_block(kinds, repair, stack, T, esc, tasks=()):
    """Offers Claude's help where it can do something, says where things stand once it has, and asks for what only the person knows."""
    if (stack or {}).get("framework") in HOSTED:
        return ""
    copy = lambda text: f'<div class="fix-code"><button type="button" class="copy" data-done="{T("fix_copied")}">{T("fix_copy")}</button><pre>{esc(text)}</pre></div>'
    done = (repair or {}).get("tasks", {})
    waiting = waiting_tasks(tasks, done)
    form = ""
    if waiting:
        form = f'<details class="fix-file answers"><summary>{T("repair_answers_title", n=len(waiting))}</summary><p class="legend">{T("repair_answers_note")}</p>{copy(answers_form(waiting, T))}</details>'
    applied = sum(1 for e in done.values() if e["status"] == "applied")
    if applied:
        return f'<div class="repair"><p class="r-title">{T("repair_done", n=applied, branch=esc(repair["branch"]))}</p><p class="legend">{T("repair_done_note", file=T("repair_md_file"))}</p>{form}</div>'
    n = sum(1 for k in kinds if k in ("code", "file"))
    if not n and not form:
        return ""
    if not n:
        return f'<div class="repair">{form}</div>'
    return f'<div class="repair"><p class="r-title">{T("repair_offer", n=n, total=len(kinds))}</p><p class="legend">{T("repair_offer_note")}</p>{copy(T("repair_prompt"))}{form}</div>'


def progress_html(rows, tasks, site_id, start, T, lang, recheck_text=""):
    """tasks = [(code, criterion)]. Ticking only estimates: what confirms a fix is a recheck."""
    crit = [c for _, c in tasks if c]
    fixed = [[r[0], r[1], "2", *r[3:]] if r[0] in crit and r[2] != "NV" else r for r in rows]
    best = grid_scores(fixed, "ABCDEF")[1]
    data = {"id": site_id, "lang": lang, "rows": {r[0]: (None if r[2] == "NV" else int(r[2])) for r in rows}}
    up_to = f'<p class="p-best">{T("progress_best", start=start, best=fmt_score(best, lang))}</p>' if best is not None and fmt_score(best, lang) != start else ""
    return (f'<div class="progress" id="progress" data-count="{T("progress_count")}" data-est="{T("progress_est")}"><div class="p-top"><span class="p-count"></span><span class="p-est"></span></div>'
            f'<div class="p-bar"><i></i></div>{up_to}<p class="legend">{T("progress_note")}{" " + recheck_text if recheck_text else ""}</p></div>'
            f'<script type="application/json" id="audit-grid">{json.dumps(data, ensure_ascii=False)}</script>')


def md_details(t, T):
    """The same help in the Markdown to-do, to paste in a ticket."""
    out = []
    if t.get("where"):
        out.append(f"  - {T('fix_where')}{T('sep')}{t['where']}")
    if t.get("how"):
        out.append(f"  - {T('fix_how')}{T('sep')}{t['how']}")
    if t.get("questions"):
        out.append(f"  - {T('fix_asks')}{T('sep')}" + " ".join(t["questions"]))
    if t.get("file"):
        out.append(f"  - {T('fix_ready')}{T('sep')}`{t['file']}`")
    if t.get("snippet"):
        out += ["", "    ```"] + ["    " + l for l in t["snippet"].split("\n")] + ["    ```"]
    return out


def soft_domain(escaped):
    """A long domain in a big title breaks once, at the dot or hyphen nearest its middle: never just before the .app."""
    spots = [m.end() for m in re.finditer(r"[.-]", escaped)]
    if len(escaped) < 16 or not spots:
        return escaped
    at = min(spots, key=lambda i: abs(i - len(escaped) / 2))
    return escaped[:at] + "<wbr>" + escaped[at:]


def font_faces(TH, url_prefix=None):
    """@font-face rules of the theme's fonts: linked from url_prefix, or embedded so that the file needs no network."""
    out = []
    for w, fn, *family in TH["font"]["files"]:
        woff2 = fn.endswith(".woff2")
        if url_prefix is not None:
            src = url_prefix + fn
        else:
            src = f"data:font/{'woff2' if woff2 else 'ttf'};base64," + base64.b64encode(open(asset_file("fonts", fn), "rb").read()).decode()
        out.append(f"@font-face{{font-family:'{family[0] if family else TH['font']['family']}';font-weight:{w};font-style:normal;font-display:swap;src:url({src}) format('{'woff2' if woff2 else 'truetype'}')}}")
    return "".join(out)


def load_themes():
    themes = json.load(open(os.path.join(ASSETS, "themes.json"), encoding="utf-8"))
    mine = os.path.join(USER_DIR, "themes.json")
    if os.path.exists(mine):
        themes.update(json.load(open(mine, encoding="utf-8")))
    return themes


def theme_css(theme):
    """dossier.css with the colours and fonts a theme replaces; what it does not name keeps the film's look."""
    TH = load_themes()[theme]
    css = open(os.path.join(ASSETS, "dossier.css"), encoding="utf-8").read()
    if TH["font"].get("css"):
        css = re.sub(r"--font: [^;]+;", lambda m: f"--font: {TH['font']['css']};", css, count=1)
    head, rest = css.split(":root {", 1)
    block_, rest = rest.split("}", 1)
    for k, v in TH["css"].items():
        block_ = re.sub(rf"{re.escape(k)}:\s*[^;]+;", lambda m: f"{k}: {v};", block_)
    return TH, head + ":root {" + block_ + "}" + rest
