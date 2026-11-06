# audit.json: the only file you write for an audit

The HTML report, the PDF, the single page and the PowerPoint are all built from `audit.json`. Never touch the generated files: fix `audit.json` and rerun the scripts.

**Keys are in French, on purpose.** The keys of `audit.json` are French for historical reasons. Keep them exactly as they are, whatever the language of the report: the scripts read them by name. Only the values are written in the report language. The less obvious ones:

| Key | Meaning |
|---|---|
| `fiches` | tool cards (one per captured tool) |
| `domaines` | domains (the report sections) |
| `criteres` | criteria (the 30 rows of the grid) |
| `resultats` | results (one line per tool) |
| `une` | one-sentence summary of a domain |
| `pourquoi` | why it matters |
| `feu` | traffic light (`v` green, `o` orange, `r` red) |
| `limites` | limits of the measure |
| `fautes` | typos |
| `remesure` | remeasure |
| `concurrents` | competitors |
| `lexique` | glossary |
| `outils`, `assistants` | tools, assistants |

Starting point: copy `assets/example/audit.en.json` (the full audit of the fictional Atelier Lumen; French version: `audit.fr.json`) and replace every value. The content shared by all sites (tools, roles, glossary, remeasure rules, categories, domains) is in `assets/defaults.<lang>.json`, where `<lang>` is the report language; a key of the same name in `audit.json` replaces it (`lexique`, `remesure`).

## Text formatting

In all strings: `**bold**`, `` `code` `` and, in code extracts (`code`), `[[highlighted in red]]` to show the defect. No full stop at the end of titles (`title`, `headline`, `stat_label`, block titles).

## The keys

| Key | Content |
|---|---|
| `site` | `domain`, `url` (tested page), `brand`, `brand_q` (brand search), `theme` (`signature` by default, `neutre` or an added theme; see `assets/themes.json`), `lang` (language of the site), `report_lang` (optional: language of the report, see below), `country`, `date` (YYYY-MM-DD), `date_label` ("2 November 2026"), `date_long` ("Monday 2 November 2026"), `perimetre` (one line), `pages` (number), `prepared_by`, `usage` ("internal use" if competitors are named), `validateur` ("the CTO"), `who` (optional, renames the lanes: `{"C": "Communication", "F": "Web agency"}`), `stack` (optional: `{"framework": "next", "host": "netlify"}`, shown above the to-do) |
| `lead`, `headline` | The report's introductory sentence, and the headline of the score ("A well-built site, badly tuned…") |
| `note` | `global` ("5.1") and `categories` (`{"A": "7.0", … "F": "2.0"}`), computed with the grid in SKILL.md; `build_dossier.py` recomputes them and stops if they differ |
| `bulletin` | Per domain (`d-faits`, `d-pages`, `d-blog`, `d-vitesse`, `d-infra`, `d-securite`, `d-google`, `d-conversion`, `d-ia`): `[feu, sentence]`, feu = `v`, `o` or `r` |
| `good`, `bad`, `decisions` | 3 to 5 sentences each: what works, what blocks, the decisions asked of management |
| `conditions`, `limites` | The conditions of the measurement (`[label, text]`) and what the measurement does not tell |
| `resultats` | Per tool (key of `defaults.outils`, or the assistant's name): `[one-line result, feu]`. A tool missing from `resultats` does not appear |
| `fiches` | Per captured tool: `who`, `big` (the big grade), `pills` (`[[ok|warn|bad, text]]`), `bullets` (2 to 4 findings), `says` ("Key takeaway"), `capture` (file name), `caption` (caption with date and time) |
| `domaines` | See below |
| `ia` | `questions` (`{"1": "…"}`), `brand_question` (5), `intro`, `note`, `assistants`: `[{name, how, answers: [{q, cited, capture, note, hour}]}]` (see `ai-panel.md`). `name` must match a key of the assistants in the defaults file of the report language: "Google AI Mode" for an English report, "Google Mode IA" for a French one. Optional in an answer: `runs`, the results of each run, as `[true, true, false]`, and `cited_instead`, the names a market answer gives instead of the site |
| `tasks` | Per code (`C1`… content, `F1`… front-end, `B1`… back-end and infra; see `voies` in `defaults.<lang>.json`): `name`, `what` (the precise fix), `check` ("Verified when…"), `prio` (1, 2 or 3; 2 by default). No date, no deadline. Optional, to make it applicable: `before` and `after` (text, or `{"url", "title"}` to show a search result), `where`, `how`, `snippet`, `file`, `criterion` (the code of the criterion it answers: shows the gain and allows the recheck) |
| `todo` | Optional: `{"C": [[group, [codes]]], "F": [...], "B": [...]}` to group by theme. Without this key, each to-do is sorted by priority (P1, P2, P3) |
| `first` | Optional: the three task codes the report opens with (`["F1", "C1", "B3"]`). Without it, the most urgent |
| `repair` | Written by `repair.py`: `branch`, `base`, `tasks` by code (`status` applied or blocked, `commits`, `files`, `note`), `local_before`, `local`. Do not write it by hand. On a task, `"repair": "code"`, `"file"`, `"facts"` or `"outside"` overrides who can do it, and `"questions": ["..."]` says what only the person can answer (`repair-mode.md`) |
| `recheck` | Written by `quick.py check`: `date`, and `results` by criterion (`status` fixed, better, same or worse, `old`, `new`, `evidence`, `code`). Do not write it by hand |
| `view` | Optional: the site seen from outside. `google` (`url`, `title`, `desc`), `share` (`domain`, `title`, `desc`, `image`), `pages` (`url`, `words`, `excerpt`, `image`: the prefix of a screenshot, `"site-01"`). `fixes.py` writes it to `view.json` |
| `todo_intro`, `validations` | The split of roles in one sentence, and who validates what ("The CTO validates…", "The communications director validates…") |
| `concurrents` | Optional, internal: `title`, `head` (`["Measure", "Us", "A", …]`), `rows`, `note`. Competitors anonymised as A, B, C… |
| `reference` | `rows`: `[domain, measure, today's value, target]` for each tracked figure; `missing` (what is missing for a complete baseline); `tasks` (the tasks that supply what is missing) |
| `criteres` | The 30 rows of the grid: `[code, criterion, score "0"/"1"/"2"/"NV", evidence]` |
| `evolution` | Optional: `title`, `intro`, `head`, `rows` (findings of the previous audit → state today) |
| `fautes` | `[["p", "Glued words (…):"], ["li", "EN: …"], ["note", "…"]]` |
| `captures` | Index: by number (`"01"`, `"site-03"`): `[tool or page, what it shows, time, domain]` |
| `documents` | `[label, path or URL]`: report, to-do, protocol, screenshots, artifacts |
| `footer_note`, `competitors_regex` | The footer note (claims to validate), and an expression ("A|B|C"): the script flags any competitor name left in the text |
| `domain_order` | Optional: order or subset of the domains |

### Report language and number format

- `site.report_lang` (optional, `"en"` or `"fr"`): the language of the report. If absent, it falls back to `site.lang` when that is `en` or `fr`, otherwise to `"en"`. It decides which defaults file is read (`assets/defaults.<lang>.json`), the labels, the date format and the output file names.
- Scores may be written `"5.1"` or `"5,1"` in `audit.json`: the build reformats them for the report language (a point in English, a comma in French).
- Dates: `date_label` is a short form ("2 November 2026"), `date_long` the long form with the weekday ("Monday 2 November 2026"). Write both in the report language.
- Output names in English reports: `YYYY-MM-DD To-do SEO GEO - <domain>.md` and `.csv`.

## A domain

```json
"d-faits": {
  "title": "The same facts say different things from one page to the next",
  "feu": "r",
  "une": "What it is, in one sentence",
  "pourquoi": "Why it matters for a buyer, for Google or for the AIs",
  "verdict": "The finding in one sentence",
  "stat": "6", "stat_label": "contradictions found, 3 of them already displayed by Google",
  "blocks": [ … ],
  "tools": ["06", "21"],
  "tools_label": "optional, replaces \"What the tools say\"",
  "tasks": ["C1", "C2", "B4"]
}
```

The blocks, in reading order:

| `type` | Fields | Rendering |
|---|---|---|
| `finding` | `title`, `where` (page and address), `paras`, `list`, `code`, `captures` (`[[prefix, caption]]`, one or two), `note` | A finding: text on the left, screenshot on the right (two screenshots side by side for the phone) |
| `table` | `title`, `head`, `rows`, `colw` (widths in inches in the PowerPoint, total 12.13) | A wide table (contradictions…) |
| `stats` | `title`, `head`, `rows` (2 columns), `role` (tool key whose role is shown), `role_title` | A table of figures, with the "What this tool is for" box |
| `tri` | `title`, `head`, `rows`, `tri_title`, `tri` (`[[number, action, detail, feu]]`), `tri_note` | Figures + triage plan (the blog) |
| `note` | `text`, `label`, `title` | A box on its own |
| `ia` | (nothing) | The table of the AIs' answers and each AI question by question, from the `ia` key |

The report also writes the to-do separately, in Markdown and CSV (`YYYY-MM-DD To-do SEO GEO - <domain>.md` and `.csv`).

Every task cited in a domain must exist in `tasks`, and every task in `tasks` must appear in a domain or in `reference.tasks`.
