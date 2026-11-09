// PowerPoint of the full audit report, from an audit.json
//   node build_pptx.js AUDIT.json CAPTURES_DIR OUT.pptx [--lang en|fr]
// pptxgenjs must be loadable: run scripts/setup_pptx.sh once. Theme: assets/themes.json. Strings and shared content: assets/ui.json, assets/defaults.<lang>.json.
const fs = require("fs");
const os = require("os");
const path = require("path");
// what belongs to the user lives outside the skill's folder, which is replaced at each plugin update (same rule as common.py)
const USER_DIR = process.env.AUDIT_SEO_GEO_HOME || path.join(os.homedir(), ".claude", "audit-seo-geo");
module.paths.push(path.join(USER_DIR, "node_modules"));
let pptxgen;
try { pptxgen = require("pptxgenjs"); } catch (e) { console.error("pptxgenjs not found: run scripts/setup_pptx.sh once."); process.exit(1); }

const argv = process.argv.slice(2);
const langAt = argv.indexOf("--lang");
const LANG_ARG = langAt >= 0 ? argv.splice(langAt, 2)[1] : null;
const [AUDIT, CAPDIR, OUT] = argv;
if (!AUDIT || !CAPDIR || !OUT) { console.error("usage: node build_pptx.js AUDIT.json CAPTURES_DIR OUT.pptx [--lang en|fr]"); process.exit(1); }
const ASSETS = path.join(__dirname, "..", "assets");
const A = JSON.parse(fs.readFileSync(AUDIT, "utf8"));
// report language: --lang, then site.report_lang, then site.lang when supported, then English (same rule as common.py)
const LANGS = ["en", "fr"];
const LANG = [LANG_ARG, A.site.report_lang, A.site.lang].map((c) => (c || "").slice(0, 2).toLowerCase()).find((c) => LANGS.includes(c)) || "en";
const UI = JSON.parse(fs.readFileSync(path.join(ASSETS, "ui.json"), "utf8"))[LANG];
const T = (key, vars = {}) => Object.entries(vars).reduce((t, [k, v]) => t.split("{" + k + "}").join(String(v)), UI[key]);
const NW = (n, key) => UI[key + ((LANG === "fr" ? n <= 1 : n === 1) ? "_one" : "_other")];
const SCORE = (x) => { const v = parseFloat(String(x).replace(",", ".")); if (Number.isNaN(v)) return x; const t = v.toFixed(1); return LANG === "fr" ? t.replace(".", ",") : t; };
A.note.global = SCORE(A.note.global);
A.note.categories = Object.fromEntries(Object.entries(A.note.categories).map(([L, v]) => [L, SCORE(v)]));
const DEF = JSON.parse(fs.readFileSync(path.join(ASSETS, `defaults.${LANG}.json`), "utf8"));
const userThemes = path.join(USER_DIR, "themes.json");
const THEMES = Object.assign(JSON.parse(fs.readFileSync(path.join(ASSETS, "themes.json"), "utf8")), fs.existsSync(userThemes) ? JSON.parse(fs.readFileSync(userThemes, "utf8")) : {});
const TH = THEMES[A.site.theme || "signature"];
const assetFile = (kind, name) => (fs.existsSync(path.join(USER_DIR, kind, name)) ? path.join(USER_DIR, kind, name) : path.join(ASSETS, kind, name));
const S = A.site, P = TH.pptx;
const VOIES = DEF.voies.map(([k, n, court, detail]) => ({ k, n, court, detail }));
const WHO = Object.assign(Object.fromEntries(VOIES.map((v) => [v.k, v.n])), S.who || {});
const PRIO = Object.fromEntries(DEF.priorites.map(([n, code, label]) => [n, [code, label]]));
const N_CRIT = 5 * DEF.categories.length;
if (!A.todo || !Object.keys(A.todo).length) {
  A.todo = Object.fromEntries(VOIES.map((v) => [v.k, Object.keys(PRIO).map(Number).sort().map((n) => [`${PRIO[n][0]} · ${PRIO[n][1]}`,
    Object.keys(A.tasks).filter((c) => c[0] === v.k && (A.tasks[c].prio || 2) === n)]).filter((g) => g[1].length)]));
}
const CAPS = fs.readdirSync(CAPDIR).filter((f) => /\.(jpe?g|png)$/i.test(f)).sort();
const OUTIL = Object.fromEntries(DEF.outils.map((o) => [o.key, o]));
const ASSIST = Object.fromEntries(DEF.assistants.map((a) => [a.key, a]));
const ROLE = (k) => (OUTIL[k] || ASSIST[k]).role;
const DOMLAB = Object.fromEntries(DEF.domaines.map(([k, n, l, c]) => [k, [n, l, c]]));
const DOMS = A.domain_order || DEF.domaines.map((d) => d[0]);
const plain = (t) => String(t).replace(/\*\*/g, "").replace(/`/g, "").replace(/\[\[|\]\]/g, "");
const dateShort = S.date_label.replace(/ \d{4}$/, "");

const NAVY = P.dark, TURQ = P.bright, TURQ_F = P.accentText, TURQ_S = P.soft, INK2 = P.ink2, MUTED = P.muted,
  LINE = P.line, BG2 = P.bg2, WHITE = "FFFFFF", NAVY_MUTED = P.darkMuted;
// a dark theme (the default) separates what a light one can share: the page, the filled panels, the strong text, the cards
const PAGE = P.page || WHITE, PANEL = P.panel || NAVY, PANEL2 = P.panel2 || INK2, TXT = P.text || NAVY, CARD = P.card || WHITE, GLYPH = P.glyph || WHITE;
const BACKDROP = P.backdrop ? { path: path.join(ASSETS, P.backdrop) } : { color: NAVY };
const FEUC = P.feu || { v: ["1A7F4E", "E3F4EA"], o: ["B56A00", "FDF1DC"], r: ["C62B1F", "FBE7E5"] };
const FEU = { v: [...FEUC.v, T("feu_v")], o: [...FEUC.o, T("feu_o")], r: [...FEUC.r, T("feu_r")] };
const TINT = (f) => (P.feu ? P.bg2 : FEU[f][1]); // large surfaces stay in the theme's palette when it says so
const PILL = { ok: FEU.v, warn: FEU.o, bad: FEU.r, na: [MUTED, BG2] };
const MONO = "Courier New";
const FONT = TH.font.family;
const LOGO_D = TH.logos.onDark && assetFile("logos", TH.logos.onDark);

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
pres.theme = { headFontFace: FONT, bodyFontFace: FONT };
pres.title = T("pptx_title", { domain: S.domain });
pres.subject = T("pptx_subject", { date: S.date_label });
pres.author = S.prepared_by || "";
const W = 13.333, X0 = 0.6, XW = W - 1.2, Y0 = 1.62, YMAX = 6.78;

// Text measure: 0.47 em per character, with a margin for a substitute font
function lines(text, w, pt) {
  const cpl = Math.max(6, Math.floor((w * 72) / (pt * 0.47)));
  let n = 0;
  for (const para of String(text).split("\n")) {
    let cur = 0, l = 1;
    for (const word of para.split(" ")) {
      const len = word.length + (cur ? 1 : 0);
      if (cur + len > cpl && cur) { l++; cur = word.length; } else cur += len;
    }
    n += l;
  }
  return n;
}
const th = (text, w, pt, lh = 1.22) => (lines(plain(text), w, pt) * pt * lh) / 72 + 0.04;
function logoSize(file, h) { const b = fs.readFileSync(file); return [(b.readUInt32BE(16) / b.readUInt32BE(20)) * h, h]; }

// ---------- Layouts ----------
const FOOT = T("footer", { brand: S.brand, domain: S.domain, date: S.date_label }) + (S.usage ? " · " + S.usage : "");
const logoObj = (x, y, h) => (LOGO_D ? [{ image: { x, y, w: logoSize(LOGO_D, h)[0], h, path: LOGO_D } }] : []);
pres.defineSlideMaster({
  title: "MASTER_COVER", background: BACKDROP,
  objects: [...logoObj(X0, 0.55, 0.95),
    { placeholder: { options: { name: "eyebrow", type: "body", x: X0, y: 2.05, w: 11, h: 0.4, fontSize: 14, bold: true, color: TURQ, margin: 0, charSpacing: 1.5, align: "left" }, text: "" } },
    { placeholder: { options: { name: "title", type: "title", x: X0, y: 2.5, w: 11.5, h: 1.9, fontSize: 44, bold: true, color: WHITE, margin: 0, valign: "top", align: "left" }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: X0, y: 4.45, w: 10.5, h: 1.1, fontSize: 17, color: NAVY_MUTED, margin: 0, valign: "top", align: "left" }, text: "" } }],
});
pres.defineSlideMaster({
  title: "MASTER_DIVIDER", background: BACKDROP,
  objects: [...logoObj(X0, 6.55, 0.58),
    { placeholder: { options: { name: "eyebrow", type: "body", x: X0, y: 2.2, w: 11, h: 0.45, fontSize: 16, bold: true, color: TURQ, margin: 0, charSpacing: 2, align: "left" }, text: "" } },
    { placeholder: { options: { name: "title", type: "title", x: X0, y: 2.7, w: 11.5, h: 1.3, fontSize: 44, bold: true, color: WHITE, margin: 0, valign: "top", align: "left" }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: X0, y: 4.1, w: 10, h: 1.4, fontSize: 18, color: NAVY_MUTED, margin: 0, valign: "top", align: "left" }, text: "" } }],
  slideNumber: { x: 12.1, y: 6.85, w: 0.65, h: 0.3, fontSize: 10, color: NAVY_MUTED, align: "right" },
});
pres.defineSlideMaster({
  title: "MASTER_CONTENT", background: { color: PAGE },
  objects: [
    { text: { text: FOOT, options: { x: X0, y: 7.0, w: 9.5, h: 0.28, fontSize: 9, color: MUTED, margin: 0 } } },
    { placeholder: { options: { name: "eyebrow", type: "body", x: X0, y: 0.38, w: XW, h: 0.3, fontSize: 11, bold: true, color: TURQ_F, margin: 0, charSpacing: 1.5, align: "left" }, text: "" } },
    { placeholder: { options: { name: "title", type: "title", x: X0, y: 0.7, w: XW, h: 0.82, fontSize: 26, bold: true, color: TXT, margin: 0, valign: "top", align: "left" }, text: "" } }],
  slideNumber: { x: 12.08, y: 6.98, w: 0.65, h: 0.3, fontSize: 9, color: MUTED, align: "right" },
});

let section = "";
function content(eyebrow, title) {
  const s = pres.addSlide({ masterName: "MASTER_CONTENT", sectionTitle: section });
  s.addText(eyebrow.toUpperCase(), { placeholder: "eyebrow" });
  s.addText(title.length > 72 ? [{ text: title, options: { fontSize: 22 } }] : title, { placeholder: "title" });
  return s;
}
function divider(eyebrow, title, body) {
  const s = pres.addSlide({ masterName: "MASTER_DIVIDER", sectionTitle: section });
  s.addText(eyebrow.toUpperCase(), { placeholder: "eyebrow" });
  s.addText(title, { placeholder: "title" });
  if (body) s.addText(body, { placeholder: "body" });
  return s;
}
function newSection(t) { section = t; pres.addSection({ title: t }); }

// ---------- Components ----------
function text(s, t, o) { s.addText(typeof t === "string" ? plain(t) : t, Object.assign({ margin: 0, isTextBox: true, valign: "top", color: INK2, fontSize: 13 }, o)); }
function box(s, x, y, w, h, fill, line) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: fill }, line: line ? { color: line, width: 0.75 } : { type: "none" } });
}
function pillW(t, pt = 11) { return (t.length * pt * 0.55) / 72 + 0.42; }
function pill(s, x, y, kind, t, pt = 11, dot = true) {
  const [c, bg] = PILL[kind] || FEU[kind];
  const w = pillW(t, pt) + (dot ? 0.16 : 0), h = (pt * 1.9) / 72;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: h / 2, fill: { color: bg }, line: { type: "none" } });
  if (dot) s.addShape(pres.shapes.OVAL, { x: x + 0.13, y: y + h / 2 - 0.05, w: 0.1, h: 0.1, fill: { color: c }, line: { type: "none" } });
  text(s, t, { x: x + (dot ? 0.3 : 0.16), y, w: w - (dot ? 0.36 : 0.28), h, fontSize: pt, bold: true, color: c, valign: "middle" });
  return w;
}
const feu = (s, x, y, f, label, pt = 11) => pill(s, x, y, f, label || FEU[f][2], pt);
function roleBox(s, x, y, w, t, pt = 12) {
  const h = 0.22 + 0.28 + th(t, w - 0.36, pt);
  box(s, x, y, w, h, TURQ_S, TURQ);
  text(s, T("role_title").toUpperCase(), { x: x + 0.18, y: y + 0.14, w: w - 0.36, h: 0.22, fontSize: 9.5, bold: true, color: TURQ_F, charSpacing: 1 });
  text(s, t, { x: x + 0.18, y: y + 0.4, w: w - 0.36, h: h - 0.45, fontSize: pt, color: TXT });
  return h;
}
function capFile(prefix) { const f = CAPS.find((c) => c.startsWith(prefix)); if (!f) throw new Error("screenshot not found: " + prefix); return f; }
const SIZES = {};
function imgSize(file) {
  if (SIZES[file]) return SIZES[file];
  const b = fs.readFileSync(path.join(CAPDIR, file));
  if (b.readUInt32BE(0) === 0x89504e47) return (SIZES[file] = [b.readUInt32BE(16), b.readUInt32BE(20)]);
  let i = 2;
  while (i < b.length) {
    const m = b[i + 1], len = b.readUInt16BE(i + 2);
    if (m >= 0xc0 && m <= 0xc3) return (SIZES[file] = [b.readUInt16BE(i + 7), b.readUInt16BE(i + 5)]);
    i += 2 + len;
  }
  throw new Error("cannot read the size of " + file);
}
function capture(s, file, x, y, maxW, maxH, caption) {
  const [iw, ih] = imgSize(file);
  let w = maxW, h = (w * ih) / iw;
  if (h > maxH) { h = maxH; w = (h * iw) / ih; }
  const cx = x + (maxW - w) / 2;
  s.addImage({ path: path.join(CAPDIR, file), x: cx, y, w, h, altText: caption || file });
  s.addShape(pres.shapes.RECTANGLE, { x: cx, y, w, h, fill: { type: "none" }, line: { color: LINE, width: 0.75 } });
  if (caption) text(s, caption, { x: cx, y: y + h + 0.08, w: Math.min(Math.max(w, 3), x + maxW - cx), h: 0.25, fontSize: 10, color: MUTED });
  return h;
}
function codeBlock(s, x, y, w, t, pt = 11) {
  t = plain(t);
  const h = th(t, w - 0.3, pt * 1.12, 1.25) + 0.24;
  box(s, x, y, w, h, BG2);
  text(s, t, { x: x + 0.15, y: y + 0.12, w: w - 0.3, h: h - 0.2, fontSize: pt, fontFace: MONO, color: TXT });
  return h;
}
function noteBox(s, x, y, w, t, pt = 12, fill = BG2, label) {
  const h = th(t, w - 0.36, pt) + 0.3 + (label ? 0.26 : 0);
  box(s, x, y, w, h, fill);
  if (label) text(s, label.toUpperCase(), { x: x + 0.18, y: y + 0.14, w: w - 0.36, h: 0.22, fontSize: 9.5, bold: true, color: MUTED, charSpacing: 1 });
  text(s, t, { x: x + 0.18, y: y + 0.15 + (label ? 0.26 : 0), w: w - 0.36, h: h - 0.25 - (label ? 0.26 : 0), fontSize: pt, color: INK2 });
  return h;
}
function bullets(s, items, x, y, w, pt = 13, color = INK2, gap = 5) {
  const runs = items.map((t, i) => ({ text: plain(t), options: { bullet: { indent: 14 }, breakLine: i < items.length - 1, paraSpaceAfter: gap } }));
  const h = items.reduce((a, t) => a + th(t, w - 0.22, pt) + gap / 72, 0);
  text(s, runs, { x, y, w, h, fontSize: pt, color });
  return h;
}
function rich(p) { // **bold**
  return String(p).replace(/`/g, "").split(/(\*\*[^*]+\*\*)/).filter(Boolean).map((t) => (t.startsWith("**") ? { text: t.slice(2, -2), options: { bold: true, color: TXT } } : { text: t }));
}
const cell = (t, o) => ({ text: plain(t), options: o });

// ---------- Templates ----------
function toolSlide(key, eyebrow) {
  const o = OUTIL[key], res = (A.resultats[key] || [""])[0];
  // a tool with no screenshot (LanguageTool) can have no card: its result is enough
  const t = A.fiches[key] || { who: [o.name, o.editor].filter(Boolean).join(" · "), bullets: res ? [res] : [] };
  const s = content(eyebrow, `${o.name} : ${plain(res)}`);
  const xl = X0, wl = 5.75;
  let y = Y0 + 0.05;
  for (const pt of [14, 13.5, 13, 12.5, 12, 11.5, 11]) {
    const need = 0.5 + th(o.role, wl - 0.36, pt - 0.5) + 0.25 + 0.36 + 0.72 + ((t.bullets || []).length ? t.bullets.reduce((a, b) => a + th(b, wl - 0.22, pt) + 5 / 72, 0) + 0.12 : 0) + (t.says ? th(t.says, wl - 0.36, pt - 0.5) + 0.56 : 0);
    if (need <= YMAX - Y0 - 0.05 || pt === 11) { draw(pt); break; }
  }
  function draw(pt) {
    y += roleBox(s, xl, y, wl, o.role, pt - 0.5) + 0.25;
    text(s, t.who, { x: xl, y, w: wl, h: 0.3, fontSize: 13, bold: true, color: INK2 });
    y += 0.36;
    let x = xl;
    if (t.big) { const bw = (t.big.length * 38 * 0.56) / 72 + 0.1; text(s, t.big, { x, y: y - 0.06, w: bw, h: 0.66, fontSize: 38, bold: true, color: TXT, valign: "middle" }); x += bw + 0.12; }
    for (const [k, p] of t.pills || []) x += pill(s, x, y + 0.12, k, p, 12) + 0.1;
    y += 0.72;
    if ((t.bullets || []).length) y += bullets(s, t.bullets, xl, y, wl, pt) + 0.12;
    if (t.says) noteBox(s, xl, y, wl, t.says, pt - 0.5, BG2, T("says"));
  }
  if (t.capture) capture(s, t.capture, 6.75, Y0 + 0.05, 5.98, 4.7, t.caption);
}

function findingSlide(eyebrow, b) {
  const s = content(eyebrow, b.title || plain(b.where || ""));
  const caps = b.captures || [];
  const wl = caps.length ? 5.75 : XW;
  let y = Y0 + 0.05;
  if (b.where) { text(s, b.where.toUpperCase(), { x: X0, y, w: wl, h: 0.3, fontSize: 12, bold: true, color: MUTED }); y += 0.48; }
  for (const p of b.paras || []) {
    const h = th(p, wl, 16, 1.25);
    text(s, rich(p), { x: X0, y, w: wl, h, fontSize: 16, color: INK2, lineSpacingMultiple: 1.05 });
    y += h + 0.18;
  }
  if (b.list) y += bullets(s, b.list, X0, y, wl, caps.length ? 14 : 17, INK2, 12) + 0.1;
  if (b.code) y += codeBlock(s, X0, y + 0.05, wl, b.code, 12.5) + 0.2;
  if (b.note) noteBox(s, X0, y + 0.05, wl, b.note, 14, BG2);
  if (caps.length === 1) capture(s, capFile(caps[0][0]), 6.75, Y0 + 0.05, 5.98, 4.7, caps[0][1]);
  if (caps.length === 2) { capture(s, capFile(caps[0][0]), 6.75, Y0 + 0.05, 2.85, 4.75, caps[0][1]); capture(s, capFile(caps[1][0]), 9.88, Y0 + 0.05, 2.85, 4.75, caps[1][1]); }
}

function domainIntro(key) {
  const D = A.domaines[key], [num, label] = DOMLAB[key], f = D.feu;
  const s = content(`${num} · ${label}`, D.title);
  const cw = (XW - 0.5) / 3, y = Y0 + 0.08, h = 2.75;
  [[T("one_sentence"), D.une], [T("why"), D.pourquoi], [T("verdict"), D.verdict]].forEach(([l, t], i) => {
    const x = X0 + i * (cw + 0.25);
    box(s, x, y, cw, h, i === 2 ? (P.feu ? PANEL : FEU[f][1]) : BG2);
    text(s, l.toUpperCase(), { x: x + 0.25, y: y + 0.22, w: cw - 0.5, h: 0.25, fontSize: 11, bold: true, color: i === 2 ? FEU[f][0] : MUTED, charSpacing: 1 });
    let ty = y + 0.6;
    if (i === 2) { feu(s, x + 0.25, ty, f, null, 12); ty += 0.5; }
    text(s, t, { x: x + 0.25, y: ty, w: cw - 0.5, h: y + h - ty - 0.15, fontSize: 16.5, color: TXT });
  });
  const by = y + h + 0.3, bh = YMAX - by;
  box(s, X0, by, XW, bh, CARD, LINE);
  text(s, D.stat || "", { x: X0 + 0.35, y: by + 0.2, w: 3.3, h: bh - 0.4, fontSize: 50, bold: true, color: FEU[f][0], valign: "middle" });
  text(s, D.stat_label || "", { x: X0 + 3.75, y: by + 0.2, w: 3.7, h: bh - 0.4, fontSize: 17, color: TXT, valign: "middle" });
  const inside = [];
  const nf = (D.blocks || []).filter((b) => b.type !== "ia").length;
  if (nf) inside.push(T("pptx_inside_seen", { n: nf, word: NW(nf, "finding") }));
  if ((D.blocks || []).some((b) => b.type === "ia")) inside.push(T("pptx_inside_ia"));
  if ((D.tools || []).length) inside.push(T("pptx_inside_tools", { names: D.tools.map((k) => OUTIL[k].name).join(", ") }));
  if ((D.tasks || []).length) inside.push(T("pptx_inside_tasks", { n: D.tasks.length, word: NW(D.tasks.length, "task") }));
  text(s, T("pptx_in_chapter"), { x: X0 + 7.75, y: by + 0.28, w: 4.2, h: 0.25, fontSize: 10, bold: true, color: MUTED, charSpacing: 1 });
  text(s, inside.map((t, i) => ({ text: t, options: { bullet: { indent: 14 }, breakLine: i < inside.length - 1, paraSpaceAfter: 3 } })), { x: X0 + 7.75, y: by + 0.58, w: 4.3, h: bh - 0.7, fontSize: 14, color: INK2 });
}

const LANE_COLOR = (L) => (P.lanes || { C: TURQ_F, F: NAVY, B: INK2 })[L] || MUTED;
const PRIO_COLOR = { P1: FEU.r[0], P2: FEU.o[0], P3: MUTED };
function taskRowH(code, w) { const t = A.tasks[code]; return 0.38 + th(t.what, w - 0.85, 13) + (t.check ? th(t.check, w - 0.85, 12) : 0) + 0.12; }
function drawTask(s, code, x, y, w, withWho = true) {
  const t = A.tasks[code];
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: y + 0.02, w: 0.62, h: 0.3, rectRadius: 0.06, fill: { color: LANE_COLOR(code[0]) }, line: { type: "none" } });
  text(s, code, { x, y: y + 0.02, w: 0.62, h: 0.3, fontSize: 12, bold: true, color: WHITE, align: "center", valign: "middle" });
  const xt = x + 0.8, wt = w - 0.85;
  const pr = PRIO[t.prio || 2][0];
  const head = [{ text: pr + "  ", options: { bold: true, color: PRIO_COLOR[pr], fontSize: 11.5 } }, { text: plain(t.name), options: { bold: true, color: TXT } }];
  if (withWho) head.push({ text: "  ·  " + WHO[code[0]], options: { color: MUTED, fontSize: 11.5 } });
  text(s, head, { x: xt, y, w: wt, h: 0.34, fontSize: 14.5, valign: "middle" });
  const runs = [{ text: plain(t.what), options: { breakLine: !!t.check, paraSpaceAfter: 2 } }];
  if (t.check) runs.push({ text: plain(t.check), options: { fontSize: 12, italic: true, color: MUTED } });
  text(s, runs, { x: xt, y: y + 0.38, w: wt, h: th(t.what, wt, 13) + (t.check ? th(t.check, wt, 12) : 0), fontSize: 13, color: INK2 });
}
function tasksSlides(eyebrow, codes) {
  const cw = (XW - 0.4) / 2, avail = YMAX - Y0 - 0.05, pages = [];
  let page = [[], []], col = 0, used = 0;
  for (const c of codes) {
    const h = taskRowH(c, cw);
    if (used + h > avail && page[col].length) { if (col === 0) { col = 1; used = 0; } else { pages.push(page); page = [[], []]; col = 0; used = 0; } }
    page[col].push([c, used]); used += h + 0.22;
  }
  pages.push(page);
  const n = codes.length;
  pages.forEach((p, i) => {
    const s = content(eyebrow, T("pptx_tasks_title", { n, word: NW(n, "task") }) + (i ? T("pptx_continued") : ""));
    p.forEach((colItems, ci) => colItems.forEach(([c, yy]) => drawTask(s, c, X0 + ci * (cw + 0.4), Y0 + 0.08 + yy, cw)));
  });
}

function tableSlides(eyebrow, title, head, rows, colW, opts = {}) {
  const pt = opts.pt || 11, avail = YMAX - Y0 - 0.1;
  const rowH = (r) => Math.max(...r.map((c, i) => th(typeof c === "string" ? c : c.text, colW[i] - 0.16, pt * 0.93, 1.15))) + 0.08;
  const headH = rowH(head), pages = [];
  let cur = [], used = headH;
  for (const r of rows) { const h = rowH(r); if (used + h > avail && cur.length) { pages.push(cur); cur = []; used = headH; } cur.push(r); used += h; }
  pages.push(cur);
  pages.forEach((p, i) => {
    const s = content(eyebrow, title + (i ? T("pptx_continued") : ""));
    s.addTable([head.map((h) => cell(h, { bold: true, color: WHITE, fill: { color: PANEL } })), ...p.map((r) => r.map((c) => (typeof c === "string" ? cell(c, {}) : c)))], {
      x: X0, y: Y0 + 0.05, w: colW.reduce((a, b) => a + b, 0), colW, fontSize: pt, color: INK2, valign: "top",
      margin: [0.05, 0.08, 0.05, 0.08], border: { type: "solid", pt: 0.5, color: LINE }, autoPage: false,
    });
    if (opts.after && i === pages.length - 1) opts.after(s, Y0 + 0.05 + headH + p.reduce((a, r) => a + rowH(r), 0) + 0.2);
  });
}
function twoColTable(s, head, rows, x, y, w, c1) {
  s.addTable([head.map((h) => cell(h, { bold: true, color: WHITE, fill: { color: PANEL } })), ...rows.map(([a, b]) => [cell(a, {}), cell(b, { bold: true, color: TXT })])],
    { x, y, w, colW: [c1, w - c1], fontSize: 11.5, color: INK2, valign: "middle", margin: [0.07, 0.1, 0.07, 0.1], border: { type: "solid", pt: 0.5, color: LINE } });
}

function block(key, b) {
  const [num, label] = DOMLAB[key], eb = `${num} · ${label} · ${T("seen")}`;
  if (b.type === "finding") return findingSlide(eb, b);
  if (b.type === "table") {
    const tot = XW, cw = b.colw || b.head.map(() => tot / b.head.length);
    return tableSlides(eb, b.title, b.head, b.rows, cw, { pt: 12 });
  }
  if (b.type === "stats") {
    const s = content(eb, b.title);
    let x = X0, w = XW;
    if (b.role) {
      const h = roleBox(s, X0, Y0 + 0.05, 4.3, ROLE(b.role), 12);
      text(s, b.role_title || "", { x: X0, y: Y0 + h + 0.25, w: 4.3, h: 0.5, fontSize: 14, bold: true, color: TXT });
      x = X0 + 4.6; w = XW - 4.6;
    }
    return twoColTable(s, b.head, b.rows, x, Y0 + 0.05, w, w * 0.55);
  }
  if (b.type === "tri") {
    const s = content(eb, b.title);
    twoColTable(s, b.head, b.rows, X0, Y0 + 0.05, 6.6, 3.6);
    const x = X0 + 6.95, w = XW - 6.95;
    text(s, (b.tri_title || "").toUpperCase(), { x, y: Y0 + 0.05, w, h: 0.25, fontSize: 10, bold: true, color: MUTED, charSpacing: 1 });
    b.tri.forEach(([n, a, c, f], i) => {
      const y = Y0 + 0.4 + i * 0.95;
      box(s, x, y, w, 0.82, TINT(f));
      text(s, n, { x: x + 0.2, y, w: 0.95, h: 0.82, fontSize: 30, bold: true, color: FEU[f][0], valign: "middle" });
      text(s, [{ text: a, options: { bold: true, color: TXT, breakLine: true } }, { text: c, options: { color: INK2, fontSize: 11.5 } }], { x: x + 1.2, y, w: w - 1.35, h: 0.82, fontSize: 14, valign: "middle" });
    });
    if (b.tri_note) text(s, b.tri_note, { x, y: Y0 + 0.4 + b.tri.length * 0.95 + 0.1, w, h: 0.8, fontSize: 11.5, color: MUTED });
    return;
  }
  if (b.type === "note") { const s = content(eb, b.title || label); noteBox(s, X0, Y0 + 0.1, XW, b.text, 15, BG2, b.label); return; }
  if (b.type === "ia") return iaSlides(key);
  throw new Error("unknown block type: " + b.type);
}

function iaSlides(key) {
  const I = A.ia, [num, label] = DOMLAB[key], E = `${num} · ${label}`;
  const names = I.assistants.map((a) => a.name), qs = Object.keys(I.questions).sort((a, b) => a - b), bq = String(I.brand_question || qs[qs.length - 1]);
  const res = Object.fromEntries(I.assistants.map((a) => [a.name, Object.fromEntries(a.answers.map((x) => [String(x.q), x]))]));
  { // the answers table
    const s = content(E, T("pptx_answers_title", { q: qs.length, a: names.length }));
    const qw = 6.3, cw = (XW - qw) / names.length, rh = Math.min(0.66, 3.3 / qs.length);
    names.forEach((c, i) => text(s, c, { x: X0 + qw + i * cw, y: Y0, w: cw, h: 0.35, fontSize: 12.5, bold: true, color: TXT, align: "center", valign: "middle" }));
    qs.forEach((q, r) => {
      const y = Y0 + 0.42 + r * rh;
      if (r % 2 === 0) box(s, X0, y, XW, rh - 0.06, BG2);
      text(s, [{ text: `Q${q}  `, options: { bold: true, color: TURQ_F } }, { text: I.questions[q] }], { x: X0 + 0.15, y, w: qw - 0.3, h: rh - 0.06, fontSize: 11, color: TXT, valign: "middle" });
      names.forEach((n, i) => {
        const x = res[n][q], k = !x ? "na" : x.cited ? "ok" : "bad", t = !x ? T("not_asked") : x.cited ? T("cited") : T("not_cited"), w = pillW(t, 10.5) + 0.16;
        pill(s, X0 + qw + i * cw + (cw - w) / 2, y + (rh - 0.06) / 2 - 0.14, k, t, 10.5);
      });
    });
    if (I.note) noteBox(s, X0, Y0 + 0.62 + qs.length * rh, XW, I.note, 12.5, TINT("r"), T("says"));
  }
  for (const a of I.assistants) {
    const cat = a.answers.filter((x) => String(x.q) !== bq), cited = cat.filter((x) => x.cited).length;
    const s = content(`${E} · ${a.name}`, cited ? T("pptx_cited_title", { name: a.name, n: cited, total: cat.length }) : T(cat.length > 1 ? "pptx_absent_many" : "pptx_absent_one", { name: a.name, total: cat.length }));
    const h = roleBox(s, X0, Y0 + 0.05, 4.2, ROLE(a.name), 14);
    text(s, [{ text: T("pptx_how"), options: { bold: true, color: TXT } }, { text: a.how }], { x: X0, y: Y0 + h + 0.25, w: 4.2, h: 0.9, fontSize: 13, color: INK2 });
    const x = X0 + 4.55, w = XW - 4.55;
    let y = Y0 + 0.05;
    const rhs = a.answers.map((x2) => Math.max(0.5, th(x2.note, w - 2.2, 13)) + 0.26);
    const scale = Math.min(1, (YMAX - Y0) / rhs.reduce((p, q) => p + q, 0));
    a.answers.forEach((x2, i) => {
      const hh = rhs[i] * scale;
      box(s, x, y, w, hh - 0.08, i % 2 ? CARD : BG2);
      text(s, `Q${x2.q}`, { x: x + 0.15, y: y + 0.1, w: 0.5, h: 0.3, fontSize: 13, bold: true, color: TURQ_F });
      pill(s, x + 0.65, y + 0.1, x2.cited ? "ok" : "bad", x2.cited ? T("cited") : T("not_cited"), 10.5);
      text(s, x2.note, { x: x + 2.05, y: y + 0.1, w: w - 2.2, h: hh - 0.2, fontSize: 13, color: INK2 });
      y += hh;
    });
    for (let i = 0; i < a.answers.length; i += 2) {
      const pair = a.answers.slice(i, i + 2);
      const sc = content(`${E} · ${a.name}`, T("pptx_shots_title", { name: a.name, qs: pair.map((r) => "Q" + r.q).join(T("pptx_q_and")) }));
      const cw2 = (XW - 0.35) / 2;
      pair.forEach((x2, j) => {
        const cx = X0 + j * (cw2 + 0.35);
        pill(sc, cx, Y0 + 0.02, x2.cited ? "ok" : "bad", x2.cited ? T("cited") : T("not_cited"), 10.5);
        text(sc, `Q${x2.q} · ${I.questions[String(x2.q)]}`, { x: cx + 1.35, y: Y0, w: cw2 - 1.35, h: 0.6, fontSize: 12.5, color: TXT });
        capture(sc, capFile(x2.capture + "-"), cx, Y0 + 0.7, cw2, 4.15, `${T("screenshot")} ${x2.capture} · ${a.name}, Q${x2.q}, ${dateShort}${x2.hour ? ", " + x2.hour : ""}`);
      });
      if (pair.length === 1) noteBox(sc, X0 + cw2 + 0.35, Y0 + 0.7, cw2, pair[0].note, 15, pair[0].cited ? TINT("o") : BG2, T("pptx_answer_says"));
    }
  }
}

// =====================================================================
const nTasks = Object.keys(A.tasks).length, nP1 = Object.values(A.tasks).filter((t) => (t.prio || 2) === 1).length;
const nEx = Object.keys(A.resultats).length;
const cats = Object.fromEntries(DEF.categories.map(([L, n, short]) => [L, short]));

newSection(T("pptx_section_cover"));
{
  const s = pres.addSlide({ masterName: "MASTER_COVER", sectionTitle: section });
  s.addText(T("pptx_cover_eyebrow", { date: S.date_label.toUpperCase() }), { placeholder: "eyebrow" });
  s.addText(T("pptx_cover_title", { domain: S.domain }), { placeholder: "title" });
  s.addText(T("pptx_cover_body", { n: nEx }), { placeholder: "body" });
  [[`${A.note.global} / 10`, T("pptx_score")], [String(S.pages || ""), T("pptx_pages")], [String(Object.keys(A.captures).length), T("pptx_shots")], [String(nTasks), T("pptx_tasks")]]
    .forEach(([v, l], i) => { const x = X0 + i * 3.0; text(s, v, { x, y: 5.75, w: 2.8, h: 0.6, fontSize: 30, bold: true, color: WHITE }); text(s, l, { x, y: 6.35, w: 2.8, h: 0.3, fontSize: 12, color: NAVY_MUTED }); });
}
{
  const s = content(T("toc"), T("pptx_toc_title"));
  [["1", T("p1_title"), T("pptx_toc_1")], ["2", T("p2_title"), T("pptx_toc_2", { n: nEx })],
   ["3", T("p3_title"), DOMS.filter((k) => A.domaines[k]).map((k) => DOMLAB[k][1]).join(", ")], ["4", T("p4_title"), T("pptx_toc_4") + (A.concurrents ? T("pptx_toc_4c") : "")],
   ["5", T("p5_title"), T("pptx_toc_5")], ["A", T("pptx_annex"), T("pptx_toc_a", { n: N_CRIT })]].forEach(([n, t, d], i) => {
    const col = i % 2, row = Math.floor(i / 2), cw = (XW - 0.3) / 2, x = X0 + col * (cw + 0.3), y = Y0 + 0.1 + row * 1.7;
    box(s, x, y, cw, 1.45, BG2);
    s.addShape(pres.shapes.OVAL, { x: x + 0.25, y: y + 0.3, w: 0.62, h: 0.62, fill: { color: n === "A" ? PANEL2 : PANEL }, line: { type: "none" } });
    text(s, n, { x: x + 0.25, y: y + 0.3, w: 0.62, h: 0.62, fontSize: 20, bold: true, color: n === "A" ? WHITE : TURQ, align: "center", valign: "middle" });
    text(s, t, { x: x + 1.1, y: y + 0.25, w: cw - 1.3, h: 0.38, fontSize: 18, bold: true, color: TXT });
    text(s, d, { x: x + 1.1, y: y + 0.66, w: cw - 1.3, h: 0.65, fontSize: 12.5, color: INK2 });
  });
}

newSection("1 · " + T("p1_title"));
divider(T("p1_eyebrow"), T("p1_title"), T("p1_sub").replace(/\.$/, ""));
{
  const s = content(T("pptx_score_eyebrow"), A.headline);
  box(s, X0, Y0 + 0.08, 3.6, 4.45, PANEL);
  text(s, A.note.global, { x: X0 + 0.35, y: Y0 + 0.8, w: 3, h: 1.6, fontSize: 96, bold: true, color: WHITE });
  text(s, T("score_global"), { x: X0 + 0.4, y: Y0 + 2.5, w: 3, h: 0.4, fontSize: 16, color: TURQ });
  text(s, T("pptx_score_avg", { n: DEF.categories.length }), { x: X0 + 0.4, y: Y0 + 3.05, w: 2.9, h: 0.9, fontSize: 12, color: NAVY_MUTED });
  const x0 = X0 + 4.0, w = XW - 4.0;
  Object.entries(A.note.categories).forEach(([L, sv], i) => {
    const v = parseFloat(sv.replace(",", ".")), y = Y0 + 0.12 + i * (4.6 / DEF.categories.length), f = v < 3 ? "r" : v < 6 ? "o" : "v";
    text(s, cats[L], { x: x0, y, w: 3.2, h: 0.4, fontSize: 16, bold: true, color: TXT, valign: "middle" });
    text(s, sv, { x: x0 + w - 1.1, y, w: 1.1, h: 0.4, fontSize: 22, bold: true, color: FEU[f][0], align: "right", valign: "middle" });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x0, y: y + 0.5, w, h: 0.16, rectRadius: 0.08, fill: { color: LINE }, line: { type: "none" } });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x0, y: y + 0.5, w: Math.max(0.16, (w * v) / 10), h: 0.16, rectRadius: 0.08, fill: { color: FEU[f][0] }, line: { type: "none" } });
  });
  text(s, T("pptx_score_intro", { crit: N_CRIT, ex: nEx }), { x: X0, y: 6.4, w: XW, h: 0.35, fontSize: 12.5, color: MUTED });
}
{
  const s = content(T("pptx_bulletin_eyebrow"), T("bulletin_title"));
  DOMS.filter((k) => A.bulletin[k]).forEach((k, i) => {
    const [f, l] = A.bulletin[k], y = Y0 + 0.05 + i * 0.63;
    if (i % 2 === 0) box(s, X0, y, XW, 0.58, BG2);
    text(s, `${DOMLAB[k][0]}  ${DOMLAB[k][1]}`, { x: X0 + 0.2, y, w: 3.4, h: 0.58, fontSize: 14, bold: true, color: TXT, valign: "middle" });
    feu(s, X0 + 3.7, y + 0.14, f, null, 11);
    text(s, l, { x: X0 + 5.4, y, w: XW - 5.6, h: 0.58, fontSize: 12.5, color: INK2, valign: "middle" });
  });
}
{
  const s = content(T("pptx_brief_eyebrow"), T("pptx_brief_title", { n: A.decisions.length }));
  const cw = (XW - 0.5) / 3;
  [[T("good"), "v", A.good], [T("bad"), "r", A.bad], [T("decisions", { n: A.decisions.length }), "n", A.decisions]].forEach(([t, f, items], i) => {
    const x = X0 + i * (cw + 0.25), y = Y0 + 0.08, h = YMAX - y;
    box(s, x, y, cw, h, f === "n" ? PANEL : TINT(f));
    s.addShape(pres.shapes.OVAL, { x: x + 0.3, y: y + 0.3, w: 0.5, h: 0.5, fill: { color: f === "n" ? TURQ : FEU[f][0] }, line: { type: "none" } });
    text(s, f === "v" ? "✓" : f === "r" ? "!" : "→", { x: x + 0.3, y: y + 0.3, w: 0.5, h: 0.5, fontSize: 18, bold: true, color: f === "n" ? NAVY : GLYPH, align: "center", valign: "middle" });
    text(s, t, { x: x + 0.3, y: y + 0.95, w: cw - 0.6, h: 0.45, fontSize: 18, bold: true, color: f === "n" ? WHITE : TXT });
    bullets(s, items, x + 0.3, y + 1.55, cw - 0.6, 14, f === "n" ? WHITE : TXT, 8);
  });
}

newSection("2 · " + T("p2_title"));
divider(T("p2_eyebrow"), T("p2_title"), T("p2_sub").replace(/\.$/, ""));
{
  const s = content(T("seo_geo_title"), T("pptx_seo_title"));
  const cw = (XW - 0.3) / 2;
  DEF.seo_geo.forEach(([big, t, d], i) => {
    const x = X0 + i * (cw + 0.3), y = Y0 + 0.1;
    box(s, x, y, cw, 4.9, i ? PANEL : BG2);
    text(s, big, { x: x + 0.4, y: y + 0.35, w: cw - 0.8, h: 1.1, fontSize: 64, bold: true, color: i ? TURQ : TURQ_F });
    text(s, t, { x: x + 0.4, y: y + 1.6, w: cw - 0.8, h: 0.5, fontSize: 22, bold: true, color: i ? WHITE : TXT });
    text(s, d, { x: x + 0.4, y: y + 2.25, w: cw - 0.8, h: 2.4, fontSize: 15, color: i ? "DDE2EA" : INK2, lineSpacingMultiple: 1.1 });
  });
}
{ // one card per examiner, at most 6 per slide
  const all = [];
  for (const o of DEF.outils) if (A.resultats[o.key]) all.push([o.group, o.key, o.name, o.editor]);
  for (const a of A.ia.assistants) all.push([T("group_ai"), a.name, a.name, ASSIST[a.name].editor]);
  const groups = [];
  for (const it of all) { const g = groups.find((x) => x[0] === it[0]); if (g) g[1].push(it); else groups.push([it[0], [it]]); }
  const slides = []; // pairs up the small groups (3 or fewer)
  const used = new Set();
  groups.forEach(([g, items], i) => {
    if (used.has(i)) return;
    const j = items.length <= 3 ? groups.findIndex(([, it], jj) => jj > i && !used.has(jj) && it.length <= 3) : -1;
    if (j > 0) { used.add(j); slides.push([T("pptx_and", { a: g, b: groups[j][0].toLowerCase() }), [...items, ...groups[j][1]]]); }
    else for (let k = 0; k < items.length; k += 6) slides.push([g, items.slice(k, k + 6)]);
  });
  const cw = (XW - 0.5) / 3;
  for (const [title, items] of slides) {
    const s = content(T("examiners_title", { n: nEx }), T("pptx_examiners_title", { title, n: items.length, word: NW(items.length, "examiner") }));
    let y = Y0 + 0.02;
    for (let r = 0; r < items.length; r += 3) {
      const row = items.slice(r, r + 3);
      const ch = Math.max(...row.map(([, k]) => { const [res, f] = A.resultats[k]; return 0.46 + th(ROLE(k), cw - 0.4, 11) + 0.14 + th(T("on_date", { date: dateShort }) + " " + res, cw - 0.55 - pillW(FEU[f][2], 11) - 0.28, 12) + 0.22; }));
      row.forEach(([, k, n, e], i) => {
        const [res, f] = A.resultats[k], x = X0 + i * (cw + 0.25);
        box(s, x, y, cw, ch, CARD, LINE);
        text(s, [{ text: n, options: { bold: true, color: TXT, fontSize: 14.5 } }, { text: "  " + e, options: { color: MUTED, fontSize: 11 } }], { x: x + 0.2, y: y + 0.14, w: cw - 0.4, h: 0.3 });
        const hr = th(ROLE(k), cw - 0.4, 11);
        text(s, ROLE(k), { x: x + 0.2, y: y + 0.5, w: cw - 0.4, h: hr, fontSize: 11, color: INK2 });
        const yr = y + 0.5 + hr + 0.08, pw = pillW(FEU[f][2], 11);
        feu(s, x + 0.2, yr, f, null, 11);
        text(s, [{ text: T("on_date", { date: dateShort }) + " ", options: { bold: true, color: TXT } }, { text: plain(res) }], { x: x + 0.2 + pw + 0.28, y: yr + 0.02, w: cw - 0.55 - pw - 0.28, h: ch - (yr - y) - 0.1, fontSize: 12, color: INK2 });
      });
      y += ch + 0.14;
    }
  }
}
{
  const s = content(T("conditions_title"), T("pptx_conditions_title"));
  let y = Y0 + 0.05;
  A.conditions.forEach(([k, v]) => {
    const h = Math.max(0.36, th(v, XW - 2.6, 14.5));
    text(s, k, { x: X0, y, w: 2.3, h, fontSize: 14.5, bold: true, color: TXT });
    text(s, v, { x: X0 + 2.5, y, w: XW - 2.5, h, fontSize: 14.5, color: INK2 });
    y += h + 0.1;
  });
  noteBox(s, X0, y + 0.1, XW, A.limites, 13.5, TINT("o"), T("pptx_limits"));
}

newSection(T("pptx_section_state"));
divider(T("p3_eyebrow"), T("p3_title"), T("p3_sub").replace(/\.$/, ""));
for (const k of DOMS.filter((d) => A.domaines[d])) {
  const D = A.domaines[k], [num, label] = DOMLAB[k];
  domainIntro(k);
  for (const b of D.blocks || []) block(k, b);
  for (const t of D.tools || []) toolSlide(t, `${num} · ${label} · ${D.tools_label || T("tools_say")}`);
  if ((D.tasks || []).length) tasksSlides(`${num} · ${label}`, D.tasks);
}

newSection("4 · " + T("p4_title"));
divider(T("p4_eyebrow"), T("p4_title"), T("p4_sub", { lanes: VOIES.map((v) => WHO[v.k]).join(", ") }).replace(/\.$/, ""));
{
  const s = content(T("todo_title"), T("pptx_todo_title", { n: nTasks, p1: nP1, l: VOIES.length }));
  const n = VOIES.length, cw = (XW - 0.3 * (n - 1)) / n;
  VOIES.forEach((v, i) => {
    const x = X0 + i * (cw + 0.3), y = Y0 + 0.1, cnt = Object.keys(A.tasks).filter((c) => c[0] === v.k).length;
    const p1 = Object.keys(A.tasks).filter((c) => c[0] === v.k && (A.tasks[c].prio || 2) === 1).length;
    box(s, x, y, cw, 4.0, i === 1 ? PANEL : BG2);
    text(s, String(cnt), { x: x + 0.35, y: y + 0.3, w: 2.5, h: 1.2, fontSize: 66, bold: true, color: i === 1 ? TURQ : TURQ_F });
    text(s, WHO[v.k], { x: x + 0.35, y: y + 1.5, w: cw - 0.7, h: 0.45, fontSize: 19, bold: true, color: i === 1 ? WHITE : TXT });
    text(s, T("pptx_todo_of_which", { court: v.court, p1 }), { x: x + 0.35, y: y + 1.95, w: cw - 0.7, h: 0.45, fontSize: 12, color: i === 1 ? NAVY_MUTED : MUTED });
    text(s, v.detail, { x: x + 0.35, y: y + 2.45, w: cw - 0.7, h: 1.45, fontSize: 12, color: i === 1 ? "DDE2EA" : INK2 });
  });
  text(s, T("pptx_todo_note"), { x: X0, y: Y0 + 4.35, w: XW, h: 0.7, fontSize: 12.5, color: MUTED });
}
for (const v of VOIES) {
  const L = v.k, groups = A.todo[L] || [], n = groups.reduce((a, g) => a + g[1].length, 0);
  if (!n) continue;
  const s = content(T("todo_title") + " · " + WHO[L], T("pptx_lane_title", { who: WHO[L], n, court: v.court }));
  const ncol = 3, cw = (XW - 0.5) / ncol, avail = YMAX - Y0 - 0.05, hOf = (g) => 0.42 + g[1].length * 0.33 + 0.1;
  let col = 0, y = Y0 + 0.05;
  for (const g of groups) {
    if (y - Y0 + hOf(g) > avail && y > Y0 + 0.1 && col < ncol - 1) { col++; y = Y0 + 0.05; }
    const x = X0 + col * (cw + 0.25);
    text(s, g[0].toUpperCase(), { x, y, w: cw, h: 0.3, fontSize: 10, bold: true, color: MUTED, charSpacing: 1 });
    y += 0.38;
    for (const c of g[1]) {
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: 0.55, h: 0.27, rectRadius: 0.05, fill: { color: LANE_COLOR(L) }, line: { type: "none" } });
      text(s, c, { x, y, w: 0.55, h: 0.27, fontSize: 11, bold: true, color: WHITE, align: "center", valign: "middle" });
      text(s, [{ text: PRIO[A.tasks[c].prio || 2][0] + "  ", options: { bold: true, color: PRIO_COLOR[PRIO[A.tasks[c].prio || 2][0]], fontSize: 10 } }, { text: A.tasks[c].name }], { x: x + 0.68, y, w: cw - 0.7, h: 0.27, fontSize: 13, color: TXT, valign: "middle" });
      y += 0.33;
    }
    y += 0.12;
  }
}
if ((A.validations || []).length) {
  const s = content(T("pptx_validations_eyebrow"), T("pptx_validations_title"));
  let y = Y0 + 0.1;
  A.validations.forEach((v, i) => {
    const m = plain(v).match(new RegExp(T("pptx_validation_re"))), who = m ? m[1] : "";
    const h = Math.max(0.9, th(v, XW - 2.2, 15) + 0.4);
    box(s, X0, y, XW, h, i ? BG2 : TURQ_S);
    text(s, who, { x: X0 + 0.3, y, w: 1.5, h, fontSize: 20, bold: true, color: TURQ_F, valign: "middle" });
    text(s, v, { x: X0 + 1.9, y, w: XW - 2.2, h, fontSize: 15, color: TXT, valign: "middle" });
    y += h + 0.2;
  });
}
if (A.concurrents) {
  const C = A.concurrents, s = content(T("versus_title"), C.title);
  const c0 = 4.6, cw = (XW - c0) / (C.head.length - 1);
  s.addTable([C.head.map((h, i) => cell(h, { bold: true, color: WHITE, fill: { color: PANEL }, align: i ? "center" : "left" })),
    ...C.rows.map((r) => r.map((c, i) => cell(c, i === 0 ? {} : i === 1 ? { bold: true, color: TXT, fill: { color: TURQ_S }, align: "center" } : { align: "center" })))],
  { x: X0, y: Y0 + 0.1, w: XW, colW: [c0, ...Array(C.head.length - 1).fill(cw)], fontSize: 13, color: INK2, valign: "middle", rowH: 0.52, margin: [0.06, 0.12, 0.06, 0.12], border: { type: "solid", pt: 0.5, color: LINE } });
  if (C.note) noteBox(s, X0, Y0 + 0.75 + C.rows.length * 0.53, XW, C.note, 14, BG2, T("says"));
}

newSection("5 · " + T("p5_title"));
divider(T("p5_eyebrow"), T("p5_title"), T("p5_sub", { date: dateShort }).replace(/\.$/, ""));
{
  const rows = A.reference.rows, per = 14;
  for (let i = 0; i < rows.length; i += per) {
    const s = content(T("reference_title"), T("reference_heading", { date: S.date_label }) + (i ? T("pptx_continued") : ""));
    s.addTable([[T("ref_domain"), T("ref_measure"), dateShort, T("ref_target"), T("ref_next")].map((h) => cell(h, { bold: true, color: WHITE, fill: { color: PANEL } })),
      ...rows.slice(i, i + per).map(([a, b, c, d]) => [cell(a, { color: MUTED }), cell(b, {}), cell(c, { bold: true, color: TXT }), cell(d, {}), cell("", { fill: { color: TURQ_S } })])],
    { x: X0, y: Y0 + 0.05, w: XW, colW: [1.5, 4.5, 1.7, 2.75, 1.68], fontSize: 12.5, color: INK2, valign: "middle", rowH: 0.33, margin: [0.04, 0.1, 0.04, 0.1], border: { type: "solid", pt: 0.5, color: LINE } });
  }
  if (A.reference.missing || (A.reference.tasks || []).length) {
    const s = content(T("reference_title"), T("pptx_ref_more"));
    text(s, A.reference.missing || "", { x: X0, y: Y0 + 0.1, w: XW, h: 1.0, fontSize: 15, color: INK2 });
    (A.reference.tasks || []).forEach((c, i) => drawTask(s, c, X0, Y0 + 1.45 + i * 1.2, XW));
  }
}
{
  const R = A.remesure || DEF.remesure, s = content(T("remeasure_title"), T("pptx_remeasure_title"));
  const cw = (XW - 0.3) / 2;
  [[T("rules"), R.regles], [T("noise"), R.bruit]].forEach(([t, items], i) => {
    const x = X0 + i * (cw + 0.3), y = Y0 + 0.1;
    box(s, x, y, cw, 3.45, BG2);
    text(s, t, { x: x + 0.3, y: y + 0.25, w: cw - 0.6, h: 0.45, fontSize: 18, bold: true, color: TXT });
    bullets(s, items, x + 0.3, y + 0.85, cw - 0.6, 13.5, INK2, 6);
  });
  noteBox(s, X0, Y0 + 3.8, XW, R.promesse, 13.5, TINT("o"), T("pptx_promise"));
}

newSection(T("pptx_annex"));
divider(T("annex_eyebrow"), T("annex_title"), T("annex_sub").replace(/\.$/, ""));
{
  const rows = [];
  for (const [L, name] of DEF.categories) {
    rows.push([cell(`${L}. ${name} · ${A.note.categories[L]} / 10`, { bold: true, color: TXT, fill: { color: TURQ_S }, colspan: 4 })]);
    for (const [c, k, n, p] of A.criteres.filter((r) => r[0][0] === L)) {
      const kind = { 0: "bad", 1: "warn", 2: "ok" }[n] || "na";
      rows.push([c, k, cell(n, { bold: true, color: PILL[kind][0], fill: { color: PILL[kind][1] }, align: "center" }), p]);
    }
  }
  const colW = [0.55, 3.9, 0.7, 6.98], pt = 11.5, avail = YMAX - Y0 - 0.1;
  const rowH = (r) => (r.length === 1 ? 0.28 : Math.max(th(r[1], colW[1] - 0.16, pt * 0.93, 1.15), th(r[3], colW[3] - 0.16, pt * 0.93, 1.15)) + 0.08);
  const pages = []; let cur = [], used = 0.3;
  for (const r of rows) { const h = rowH(r); if (used + h > avail && cur.length) { pages.push(cur); cur = []; used = 0.3; } cur.push(r); used += h; }
  pages.push(cur);
  pages.forEach((p, i) => {
    const s = content(T("annex_a"), T("pptx_annex_a_title", { n: N_CRIT }) + (i ? T("pptx_continued") : ""));
    s.addTable([["#", T("crit_col"), T("crit_score"), T("crit_proof")].map((h) => cell(h, { bold: true, color: WHITE, fill: { color: PANEL } })), ...p.map((r) => r.map((c) => (typeof c === "string" ? cell(c, {}) : c)))],
      { x: X0, y: Y0 + 0.05, w: XW, colW, fontSize: pt, color: INK2, valign: "top", margin: [0.04, 0.08, 0.04, 0.08], border: { type: "solid", pt: 0.5, color: LINE } });
  });
}
if (A.evolution) {
  const E = A.evolution;
  tableSlides(T("annex_b"), E.title, E.head, E.rows, [6.5, 5.63], { pt: 14, after: (s, y) => text(s, E.intro || "", { x: X0, y, w: XW, h: 0.5, fontSize: 12, color: MUTED }) });
}
if ((A.fautes || []).length) {
  const s = content(T("annex_c"), T("typos_heading"));
  const runs = [];
  A.fautes.forEach(([k, t], i) => {
    t = plain(t);
    if (k === "li") return runs.push({ text: t, options: { bullet: { indent: 14 }, paraSpaceAfter: 5, breakLine: true } });
    if (k === "note") return runs.push({ text: t, options: { italic: true, color: MUTED, breakLine: true } });
    const j = t.indexOf(":") + 1;
    runs.push({ text: t.slice(0, j), options: { bold: true, color: TXT, paraSpaceBefore: i ? 8 : 0 } });
    runs.push({ text: t.slice(j), options: { paraSpaceAfter: 5, breakLine: true } });
  });
  text(s, runs, { x: X0, y: Y0 + 0.05, w: XW, h: YMAX - Y0, fontSize: 13, color: INK2 });
}
{
  const ord = (k) => (/^\d+$/.test(k) ? +k : 1000 + (+(k.match(/\d+/) || [0])[0]));
  const rows = Object.entries(A.captures).sort((a, b) => ord(a[0]) - ord(b[0])).map(([k, [a, b, h, d]]) => [cell(k, { bold: true, color: TXT }), a, b, h, DOMLAB[d][2]]);
  tableSlides(T("annex_d"), T("pptx_index_title", { n: rows.length, date: S.date_label }), [T("idx_no"), T("idx_tool"), T("idx_what"), T("idx_hour"), T("idx_domain")], rows, [1.0, 3.0, 5.53, 1.1, 1.5], { pt: 13 });
}
{
  const LEX = A.lexique || DEF.lexique, per = 12;
  for (let p = 0; p < LEX.length; p += per) {
    const s = content(T("annex_e"), T("pptx_lexicon_title", { n: LEX.length }) + (p ? T("pptx_continued") : ""));
    const items = LEX.slice(p, p + per), cw = (XW - 0.4) / 2, half = Math.ceil(items.length / 2);
    items.forEach(([t, d], i) => {
      const col = i < half ? 0 : 1, row = col ? i - half : i, x = X0 + col * (cw + 0.4), y = Y0 + 0.05 + row * 0.86;
      text(s, t, { x, y, w: cw, h: 0.28, fontSize: 14, bold: true, color: TXT });
      text(s, d, { x, y: y + 0.3, w: cw, h: 0.52, fontSize: 12.5, color: INK2 });
    });
  }
}
if ((A.documents || []).length) {
  const s = content(T("annex_f"), T("docs_heading"));
  A.documents.forEach(([a, b], i) => {
    const y = Y0 + 0.05 + i * 0.5;
    if (i % 2 === 0) box(s, X0, y, XW, 0.46, BG2);
    text(s, a, { x: X0 + 0.2, y, w: 5.2, h: 0.46, fontSize: 14, bold: true, color: TXT, valign: "middle" });
    const isUrl = /^https?:/.test(b);
    text(s, isUrl ? [{ text: b.replace(/^https?:\/\//, ""), options: { hyperlink: { url: b } } }] : b, { x: X0 + 5.5, y, w: XW - 5.7, h: 0.46, fontSize: 12.5, fontFace: MONO, color: isUrl ? TURQ_F : INK2, valign: "middle" });
  });
  if (A.footer_note) text(s, A.footer_note, { x: X0, y: 6.4, w: XW, h: 0.3, fontSize: 11.5, italic: true, color: MUTED });
}

(async () => {
  await pres.writeFile({ fileName: OUT });
  // pptxgenjs saves without compression: recompress (slide XML / 10)
  const JSZip = require("jszip");
  const zip = await JSZip.loadAsync(fs.readFileSync(OUT));
  fs.writeFileSync(OUT, await zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE", compressionOptions: { level: 6 } }));
  console.log("ok", OUT, pres.slides.length, "slides");
})();
