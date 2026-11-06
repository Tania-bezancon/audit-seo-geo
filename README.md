<p align="center"><img src="docs/cover.png" alt="audit-seo-geo: audit your site, fix it, check it holds" width="100%"></p>

# audit-seo-geo

**A Claude skill that audits any website the same way every time: what Google can read, what visitors experience, what the server does, what the copy says, and what AI assistants really answer. Every finding has its evidence, and every problem becomes a task for the person who can fix it. Then, if you want, it applies the fixes in your code on a branch, and checks on your live site what holds.**

[Project page](https://tania-bezancon.github.io/audit-seo-geo/) · [Example: quick audit](https://tania-bezancon.github.io/audit-seo-geo/demo/quick/) · [Example: full audit](https://tania-bezancon.github.io/audit-seo-geo/demo/) · [Example: comparison](https://tania-bezancon.github.io/audit-seo-geo/demo/compare/) · [Version française](README.fr.md)

## Try it in 15 minutes

Type this in a Claude Code conversation, not in your shell:

```
/plugin marketplace add Tania-bezancon/audit-seo-geo
/plugin install audit-seo-geo@tania-bezancon
```

Then run an audit, or just ask for one in your own words ("run a quick SEO audit of my site"):

```
/audit-seo-geo:audit-seo-geo quick https://www.your-site.com
```

You need Claude Code and Python 3.9+. No browser and no API key are required: what cannot be measured is marked as not checked and excluded from the score, never guessed.

You get one HTML page with a provisional score and the fixes in order of usefulness, plus the to-do as Markdown and CSV. Then, if you have the site's code:

```
Fix my site with this audit.
```

Claude applies what it can on a branch of its own, asks you what it must not invent, and nothing goes online without you. Once you have published, ask it to recheck: it reads the live site and says which fixes hold.

 [See an example](https://tania-bezancon.github.io/audit-seo-geo/demo/quick/).

## Two speeds

| | Quick | Full |
|---|---|---|
| Ask for | `quick <url>` | `full <url>` |
| Time | about 15 minutes | a working day |
| Browser | optional | required |
| Pages | up to 25 | all, up to 400 |
| Criteria checked | about 15 to 22 of 30 | 30 |
| Evidence | measures and links | a dated screenshot for each finding |
| AI panel | 3 questions, 2 assistants, if a browser is available | 5 questions, 4 assistants |
| You get | one HTML page and the to-do | report, PDF, single page, PowerPoint, to-do, remeasure protocol |
| Score | provisional, for a first look | comparable from one audit to the next |
| Follow-up | `compare.py` between two quick audits | `compare.py` between two full audits, with the protocol |

Reports come in **English or French**, following the language you write in. To add a language, translate two files (`assets/ui.json`, `assets/defaults.<lang>.json`), plus `assets/quick.json` for quick mode.

## Why another audit

Most SEO audits look alike: a score from a single tool, fifty generic recommendations, and a schedule nobody keeps. Three months later you run another tool, the score has changed, and nobody knows whether the site improved or the measure did.

Two questions often stay unanswered:
- **who does what?** A list of 50 items mixes what marketing fixes in ten minutes in the CMS with what takes a developer a day;
- **do AI assistants cite us?** Buyers also ask ChatGPT or Perplexity now, and many modern sites are invisible to them because their text arrives through JavaScript.

This skill answers both.

## What makes it different

### Real AI answers, with no API key or paid service
The panel asks fixed questions to real assistants, in the same pages a buyer uses, without an account: market questions a buyer would ask without knowing the brand, and "What is <brand>?". It notes who gets cited instead of you and every wrong figure repeated about you. When remeasuring, each question is asked 3 times, and a citation only counts if it comes back at least 2 times out of 3.

### A score you can compare
The grid is **fixed**: 6 categories × 5 criteria, each scored 0, 1 or 2. Same tools, same settings, same questions at each audit. When the score moves, the site moved, not the method. A criterion that cannot be verified (without Search Console, for instance) is scored **NV** and excluded, rather than guessed.

| | Category | What it looks at |
|---|---|---|
| A | Crawling and indexing | robot access, one version of the site, HTTP codes, rendering without JavaScript, structure |
| B | Performance and front-end | real LCP, INP and CLS, mobile PageSpeed, images, JavaScript and CSS, mobile |
| C | Server, security and privacy | TLS and HSTS, security headers, compression and cache, response time, consent |
| D | Content and editorial SEO | titles, descriptions and sharing, structure, depth, accuracy of facts, freshness and languages |
| E | Experience, accessibility and conversion | the first 5 seconds, call to action, form, proof, WCAG |
| F | GEO and authority | structured data, AI crawlers and llms.txt, entity, citable content, presence in answers |

### It follows your fixes
Each fix shows what it can bring on the audit's score. Tick what you have done: the page remembers it in your browser and estimates the score, clearly as an estimate. Then ask Claude to recheck: `quick.py check` reads the site again and marks on each card what is confirmed fixed, better or not yet, without touching the audit's score.

### It says what really changed
`scripts/compare.py` compares two audits of a site and writes one page: the score on the criteria checked both times only, what improved, what got worse, the tools read with noise thresholds (under 5 PageSpeed points is noise), the AI answers, and the tasks still open. A tool that was down on the day does not look like progress, and a task that left the list is "no longer listed", not "done". `--fail-on-regression` makes it usable in CI. [See an example](https://tania-bezancon.github.io/audit-seo-geo/demo/compare/).

```bash
python3 scripts/compare.py audits/my-site/2026-11-05/audit.json audits/my-site/2027-02-01/audit.json
```

Or ask Claude: `compare` the last two audits of a site.

### It can apply the fixes in your code
Say "fix my site" and give it the folder of the code. Each task is sorted: Claude can do it, it needs your facts, or it is settled off the code. Tasks that need you come with their questions, and a form to fill in and paste. Claude works on a branch of its own, with one commit per task, and refuses to invent a legal name or a figure. It builds the site, reads it on your machine before and after, and stops if something that worked got worse. It cannot push or publish: you read the branch, you put it online, and `quick.py check` then confirms what holds on the live site.

### A report you understand at a glance
It opens on five looks with one light each, and the three tasks to start with. Then it shows the site from outside: its Google result, what people see when it is shared, and what a visitor sees next to what an AI crawler reads without JavaScript. The AI panel says who gets cited instead, by name and by how often.

### Fixes you can apply
A task says where to act and what to paste, for the platform of the site, which the crawl detects (Next.js, WordPress, Webflow, Shopify, Netlify, Vercel, Nginx...). The report shows the real page before and after, gives code to copy, and writes ready files in `fixes/`: the missing security headers in the host's format, an `llms.txt` from the site's own titles and descriptions, an Organization block, a table of the titles to fix. They are drafts to read, and nothing is ever applied to the site.

### Evidence for every finding
Each finding is filed as **verified**, **hypothesis** or **not verifiable**. In the full audit, a verified finding has its real screenshot, taken on the day of the measure, with a red box on the defect, or a link. No invented statistics, no assumed Google positions, no ranking promises.

### Three to-do lists, no calendar
Each problem becomes a precise task, with the fix and a "Verified when..." check that anyone can repeat. It goes in the list of the person who can do it:

- **Content** (`C1`, `C2`...): what is settled in the site's admin, with no developer;
- **Front-end** (`F1`...): what is settled in the page code;
- **Back-end and infra** (`B1`...): what is settled on the server.

Each task has a priority: **P1** blocking, **P2** important, **P3** polish. No dates, no deadlines, no effort in days. The to-do also comes as **Markdown** (to tick, to paste in a ticket) and **CSV** (to import in Notion, Jira, Linear, Trello or GitHub Projects).

The [360° checklist](references/checklist-360.md) gives, for more than 60 checks, the expected evidence, the standard fix, the default priority and the criterion affected.

### Five looks, 23 free examiners
No paid API, no opaque in-house score: anyone can repeat the measure at the same address.

| Look | What it checks | With what |
|---|---|---|
| **Google** | robots.txt, sitemap, redirects, fake 404s, canonicals, hreflang, rendering without JavaScript | automatic crawl, `site:` search, Bing, Rich Results Test, Schema Markup Validator |
| **Visitors** | Core Web Vitals, mobile, accessibility, call to action, form, proof | PageSpeed Insights (mobile and desktop), WAVE, W3C validator |
| **Server** | response time, compression, cache, TLS, security headers, trackers | automatic crawl, SSL Labs, Security Headers, Mozilla Observatory, Internet.nl, Webbkoll, Blacklight |
| **Copy** | titles, descriptions, share previews, typos, contradictory facts, freshness | automatic crawl, LanguageTool, OpenGraph.xyz |
| **AI** | who gets cited instead of you, which wrong facts circulate, AI crawlers, llms.txt, entity | ChatGPT, Google AI Mode, Brave, Perplexity (no account), Wikidata, Ahrefs, Similarweb |

The crawler (`crawl.py`) reads each page the way most AI crawlers do, without JavaScript, and flags pages that are nearly empty: often the most serious problem of a recent site.

### A report people want to read
Everything starts from one file, `audit.json`. The scripts turn it into:
- an **HTML report** in 5 parts (read in 5 minutes, understand the measure, 9 domains, act, follow up) and its appendices;
- its **A4 PDF** and a **single page** (one file, screenshots embedded, to send by email);
- the **to-do** as Markdown and CSV;
- a **16:9 PowerPoint** of about a hundred slides in the brand's colours.

![Three pages of the example report: the score, a domain, the to-do](docs/apercu-dossier.png)

### It checks itself
Before producing anything, the build stops if a task is cited but does not exist or exists but is never cited, if a task has no valid lane or priority, if a criterion is missing, or **if a score does not match the criteria**: it recalculates each category and the overall score. `scripts/selftest.sh` builds the example in both languages, runs the quick audit on a local test site, and checks each output, with no network.

### It respects the sites it audits
The full crawl leaves 3 seconds between two requests (1 second in quick mode) and resumes where it stopped. An audit never changes the site, never fills in a real form, never ticks an "I am human" box and never captures a logged-in area.

## Installing

**As a plugin** (recommended), in Claude Code:

```
/plugin marketplace add Tania-bezancon/audit-seo-geo
/plugin install audit-seo-geo@tania-bezancon
```

Or from your terminal:

```bash
claude plugin marketplace add Tania-bezancon/audit-seo-geo
claude plugin install audit-seo-geo@tania-bezancon
```

**As a plain skill folder**, if you prefer. The command is then the shorter `/audit-seo-geo quick <url>`:

```bash
git clone https://github.com/Tania-bezancon/audit-seo-geo.git ~/.claude/skills/audit-seo-geo
```

The skill costs about 240 tokens per session while idle, and about 5,700 when it loads. Your sites, themes, fonts and logos stay in `~/.claude/audit-seo-geo/`, and your audits go in `audits/<domain>/<date>/` under the current folder: updates touch neither. To remove the plugin: `/plugin uninstall audit-seo-geo@tania-bezancon`.

The PowerPoint needs one more step, which Claude runs the first time you ask for one: `scripts/setup_pptx.sh`.

| Tool | For what | Required |
|---|---|---|
| Python 3.9+ | crawl, report, to-do, quick audit | yes |
| Pillow (Python) | red boxes on screenshots | for the full audit |
| A browser driven by Claude | screenshots of the tools and the AIs | for the full audit; in quick mode, for the AI panel |
| Node.js 18+ | PowerPoint (pptxgenjs), speed measured with Lighthouse | for the PowerPoint; without a PageSpeed key, for speed and accessibility |
| Google Chrome or Chromium | PDF of the report (`CHROME=/path` otherwise) | for the PDF |
| Microsoft PowerPoint or LibreOffice, PyMuPDF | PDF and contact sheets of the PowerPoint | no |

PageSpeed's public API usually answers 429 without a key. The quick audit then runs Lighthouse on your machine, which needs Chrome and Node.js and downloads Lighthouse with `npx` the first time. Set `PAGESPEED_API_KEY` to use your own free key: only the API has visitors' real data.

The skill also triggers by itself when you ask for "an SEO audit", "our visibility in AI", "the list of front-end and back-end fixes", "redo the audit to see the progress"...

## Try it without auditing anything

The fictional example of Atelier Lumen (an `.example` site with placeholder screenshots) builds everything in a few seconds, from a clone of this repository:

```bash
scripts/selftest.sh /tmp/audit-example
open /tmp/audit-example/en/index.html
```

Or online: [quick audit](https://tania-bezancon.github.io/audit-seo-geo/demo/quick/), [full audit](https://tania-bezancon.github.io/audit-seo-geo/demo/), [full audit in French](https://tania-bezancon.github.io/audit-seo-geo/demo/fr/).

## How a full audit runs

A working day, announced at the start:

1. **Context**: activity, audience, goal, CMS or framework, available access. Nothing to ask again for a site already in `~/.claude/audit-seo-geo/sites.json`.
2. **Measures** (about 3 h): crawl in the background, rendering without JavaScript, the 19 tools with their numbered screenshot, the AI panel, site screenshots, the 360° checklist.
3. **Scoring** (about 2 h): the 30 criteria with their evidence, the 9 domains, the tasks of the three to-do lists.
4. **Building** (about 1 h): report, PDF, single page, to-do, PowerPoint, then checks at 1,280 and 375 px and contact sheets of the PowerPoint.
5. **Remeasure protocol**: the only dated document, to repeat exactly the same measure in 1, 3 or 6 months.

## What the repository contains

```
.claude-plugin/          the plugin's manifest and its marketplace
SKILL.md                 the method: speed and language, context, evidence, measures, grid, tasks, deliverables, checks
references/
  quick-mode.md          the quick audit, step by step
  checklist-360.md       more than 60 checks, lane by lane, with standard fix and priority
  tools.md               the 19 tools: address, setting, what to note, traffic light thresholds
  ai-panel.md            the 5 questions and the 4 AIs: writing, asking, scoring
  screenshots.md         storing, naming and boxing screenshots
  data-format.md         the format of audit.json
assets/
  ui.json                the fixed strings of the reports, by language
  defaults.<lang>.json   grid, lanes, priorities, tools, glossary, remeasure rules, domains
  quick.json             quick mode: criteria, evidence sentences, default tasks, by language
  recipes.json           how to apply a fix, by platform, by language
  themes.json            colours and font by brand (signature, neutral)
  sites.json             the format of your list of known sites
  example/               the fictional audit of Atelier Lumen, in English and French
scripts/
  quick.py               the quick audit: measure, then build
  compare.py             what changed between two audits
  fixes.py               the platform detected, and the files ready to adapt
  crawl.py               crawl of pages, server and AI crawlers, slow and resumable
  lt.py                  typos with LanguageTool, page by page
  annotate.py            red boxes on a screenshot
  build_dossier.py       audit.json → HTML, PDF, single page, to-do .md and .csv (after checks)
  build_pptx.js          audit.json → PowerPoint
  render_pptx_pdf.sh     PowerPoint → PDF and contact sheets
  setup_pptx.sh          installs the PowerPoint dependency, once
  selftest.sh            the example, the quick audit and the comparison from end to end, offline
docs/                    the project page and the online examples
```

## Adding your brand

Create `~/.claude/audit-seo-geo/themes.json`, copy into it the `signature` theme of `assets/themes.json` under a new name, change the colours, and put that name in `site.theme`. A font goes in `~/.claude/audit-seo-geo/fonts/` (listed in `font.files`) and will be embedded in the single page, so use an open-licence one or one you may distribute; a logo goes in `~/.claude/audit-seo-geo/logos/`.

## What it does not do

- It does not replace Search Console: without access, it says so in the limits and makes it a P1 task.
- It does not guarantee any ranking or any citation by an AI. It measures, sorts, and says what to fix.
- An audit never changes the site. Its code changes only if you ask, on a branch, and nothing goes online without you.

## Licence

MIT. See [LICENSE](LICENSE). The fonts in `assets/fonts/` (Archivo, Inter, JetBrains Mono) are under the SIL Open Font License, with their licences next to them. Created by [Tania Bezançon](https://taniabezancon.netlify.app/en) · Blue Hours Studio.
