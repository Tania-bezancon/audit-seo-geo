---
name: audit-seo-geo
argument-hint: "[quick|full|compare|fix] <url or audit>"
description: SEO and GEO audit of any website, in two speeds. Quick (about 15 minutes, no browser or API key required): automatic crawl, public services, small AI panel, provisional score, the 10 most useful fixes. Full (a working day): 23 free external examiners with screenshots, a crawl of all pages, the AI panel (ChatGPT, Google AI Mode, Brave, Perplexity), a fixed grid of 30 criteria scored out of 10, three undated to-do lists (content, front-end, back-end) with P1 to P3 priorities, a report (HTML, PDF, single page) and a branded PowerPoint, plus a remeasure protocol. Reports in English or French. Use for any request for an audit, analysis, score or review of SEO, GEO, AEO, performance, Google visibility or AI visibility of a site, a list of front-end and back-end fixes, remeasuring progress, comparing two audits, or applying the fixes in the code of the site, on a branch, with nothing put online. Also in French: "audit SEO", "audit GEO", "référencement", "visibilité dans les IA", "refais l'audit".
---

# SEO and GEO audit

The same audit, always run the same way, so that scores compare from one site to another and from one month to the next. Call it with a URL: `/audit-seo-geo https://www.example.com`.

The audit takes five looks at the same site: **what Google can read** (crawling, indexing), **what visitors experience** (speed, accessibility, conversion), **what the server does** (codes, cache, security, privacy), **what the copy says** (content, facts, freshness) and **what AI assistants answer** (GEO, authority). Every problem found becomes a task, in one of three to-do lists: content, front-end, back-end.

## Where things are

The skill's folder is `${CLAUDE_SKILL_DIR}`. Every `scripts/`, `references/` and `assets/` path in this file and in the references is relative to it: run scripts with their full path, as in `python3 "${CLAUDE_SKILL_DIR}/scripts/quick.py"`.

**Never write in that folder**: a plugin update replaces it. Two places hold what you produce:
- **Your audits** go in the folder the requester names, otherwise in `audits/<domain>/YYYY-MM-DD/` under the current directory. Keep each `audit.json` or `quick.json` there: comparing two audits needs them.
- **Your settings** go in `~/.claude/audit-seo-geo/`: `sites.json`, `themes.json`, `fonts/`, `logos/`. The scripts read them before what the skill ships. `assets/sites.json` only shows the format.

The PowerPoint needs Node.js and one setup: `scripts/setup_pptx.sh`. Run it the first time a PowerPoint is asked for.

## Choose the speed and the language

**Speed.** The word `quick` in the request (or "fast", "first look", "aperçu", "rapide") means the quick audit: follow `references/quick-mode.md` and stop there. `full` (or "complet") means the rest of this file. If the request says neither, ask one question and recommend quick for a first look at a site: the full audit takes a working day. Without anyone to answer (a scheduled task), run quick.

**Comparing.** `compare`, "what changed", "did we progress" or "compare to the last audit" means comparing two audits of the same site: run `scripts/compare.py` (section 9). To measure progress, run a new audit first, of the same kind as the previous one.

**Rechecking.** `recheck`, "check my fixes", "revérifie", "c'est corrigé ?" or a task code means reading the site again for the fixes made: `python3 scripts/quick.py check <audit.json or quick.json> [B1,F3]` (task codes), then rebuild the report. It says, for each fix, what a machine can conclude, and leaves the audit's measures and score alone. For what it cannot check, use the task's "Verified when...". Never call a score progress from a recheck: progress is measured by a new audit and `compare.py`.

**Repairing.** `fix`, `repair`, "fix my site", "apply the fixes", "corrige le site", "corrige mon site", "applique les corrections" means changing the site's code from an audit: follow `references/repair-mode.md`. Only with a folder of code the requester names, on a branch of its own, one commit per task, tested on this machine. Never push, merge or deploy unless they ask for that step.

**Language.** Write the report in the language the requester writes in, unless they ask otherwise. It is set by `site.report_lang` (`en` or `fr`), which selects the fixed strings of `assets/ui.json` and the shared content of `assets/defaults.<lang>.json`. Everything you write in `audit.json` or `quick.json` goes in that language too. The questions asked to AI assistants stay in the language of the site's buyers, whatever the language of the report. Tell the requester if they want another language: adding one means translating those two files.

The rest of this file is the **full audit**.

The complete example is the fictional audit of Atelier Lumen: `assets/example/audit.en.json` (French: `audit.fr.json`) with its placeholder screenshots in `assets/example/captures/` (French: `captures-fr/`). When in doubt about the level of detail expected, refer to it. `scripts/selftest.sh` builds the whole example and checks that nothing is broken.

A working day in all: about 3 h of measures, 2 h of scoring and writing, 1 h of building and checking. Announce the duration to the requester at the start and keep them posted at each step.

## What the skill contains

| File | Role |
|---|---|
| `references/quick-mode.md` | The quick audit, step by step |
| `references/repair-mode.md` | Applying the fixes in the site's code: the rules, the steps, who does what |
| `references/checklist-360.md` | All the checks, lane by lane (content, front-end, back-end), with the expected evidence, the standard fix, the priority and the criterion affected |
| `references/tools.md` | The 19 tools (the 4 AI assistants are in `ai-panel.md`): exact address, setting, what to note, screenshot number, traffic light thresholds |
| `references/ai-panel.md` | The 5 questions and the 4 AI assistants: writing, asking, scoring |
| `references/screenshots.md` | Where to store screenshots, which to take, the traps |
| `references/data-format.md` | The format of `audit.json`, the only file to write |
| `assets/sites.json` | The format of `~/.claude/audit-seo-geo/sites.json`, the known sites: activity, audience, area, goal, theme, approver, folder |
| `assets/defaults.<lang>.json` | Shared content: grid, lanes, priorities, tools and their role, assistants, glossary, remeasure rules, domains |
| `assets/ui.json` | The fixed strings of the reports, by language |
| `assets/quick.json` | Quick mode: criteria labels, evidence sentences and default tasks, by language |
| `assets/themes.json`, `logos/`, `fonts/` | Colours, font and logo by brand: `signature` (the default, the look of the Blue Hours Studio film: petrol black, petrol and glacier), `neutre` (light), and those you add |
| `assets/example/` | The complete fictional audit, to copy for a new audit |
| `scripts/crawl.py` | Careful automatic crawl of all pages, the server and the AI crawlers |
| `scripts/quick.py` | The quick audit: `measure`, then `build`; `check` reads the live site again after fixes |
| `scripts/repair.py` | The fixes in the site's code: `plan`, `start`, `place`, `commit`, `skip`, `verify`, `finish`. It has no way of pushing or publishing |
| `scripts/compare.py` | What changed between two audits: score like for like, noise rules, AI panel, tasks |
| `scripts/fixes.py` | The platform detected, and the files ready to adapt: security headers for the host, llms.txt, Organization block, titles to fix |
| `assets/recipes.json` | How to apply a fix, by criterion and by platform, by language |
| `scripts/lt.py` | Spelling and grammar with LanguageTool on titles, descriptions, H1 and H2, page by page |
| `scripts/annotate.py` | Red boxes on a screenshot |
| `scripts/build_dossier.py` | `audit.json` → HTML report, PDF (`--pdf`), single page (`--single`), to-do as Markdown and CSV, after checking consistency and scores |
| `scripts/build_pptx.js` | `audit.json` → PowerPoint (`scripts/setup_pptx.sh` once) |
| `scripts/render_pptx_pdf.sh` | PowerPoint → PDF and contact sheets (Microsoft PowerPoint on Mac, otherwise LibreOffice) |
| `scripts/selftest.sh` | Builds the example in both languages, runs the quick audit on a local test site, and checks each output |

The keys of `audit.json` and of the crawl's output are in French for historical reasons. Keep them as they are (`references/data-format.md` has a glossary).

## 1. The site's context

If the site is in `~/.claude/audit-seo-geo/sites.json`, ask nothing. Otherwise, ask only what is missing among: the activity, the target audience, the area and languages, the goal (contact requests, sales, sign-ups, awareness), the brand (for the theme), the fact approver and the folder for the audit, then add the site to that file for next time, creating it if needed.

Also ask, once, what would change the measure: access to Search Console, Bing Webmaster Tools or the analytics (otherwise these criteria are NV), the site's CMS or framework (WordPress, Webflow, Next.js..., to write fixes the team can apply), and whether the business is local (then also look at the Google Business Profile).

Before starting, read what the site's folder already contains (a CLAUDE.md, a reference of facts, claims and competitors) and the site's latest audit, to measure the gap. A site without a theme takes `signature`; for a new brand, add a theme in `~/.claude/audit-seo-geo/themes.json` (colours, open-licence font in `fonts/`, logo in `logos/`, next to that file).

## 2. The rules of evidence

- Examine at least: the home page, each product or offer page, the contact page, the "about" page, the blog and 3 articles, and all the sitemap addresses for the automatic checks. Note the pages studied, the date and the limits.
- Each finding is filed in one of three categories: **verified** (with evidence), **hypothesis** or **not verifiable** (no Search Console, analytics, etc.).
- Invent no statistic, no Google position, no test result. A good GEO structure does not guarantee being cited by an AI.
- Screenshots are real, taken in the browser, with the URL visible or noted (`references/screenshots.md`). For a text or code problem, give a before and after. A style preference is not a mistake.
- Recheck live any surprising finding before writing it (an empty page, a wrong date, a contradictory figure, a blocked crawler).
- Do not name competitors in anything that may leave the team: A, B, C... Names stay in internal documents.
- An audit never changes the site: its code changes only on request, in repair mode. Never fill in a real form, never tick an "I am human" box.

## 3. The measures, in this order

1. **Automatic crawl**, in the background from the start: `python3 scripts/crawl.py <url> <folder>/crawl --delay 3`. It reads each page (codes, response time, cache, title, description, headings, alt, JSON-LD, Open Graph, viewport, scripts, JavaScript rendering hint) and the whole site (`checks.json`: AI crawlers, llms.txt, compression, security headers, fake 404, www, http). A server can block an address after about a hundred fast requests: keep 3 s between two pages, and rerun with `--jina` if blocked. Then `python3 scripts/lt.py <folder>/crawl --lang <en-GB|fr|...> --prefix <url>` (one language at a time), and read each alert by hand.
2. **Rendering without JavaScript**: if `summary.json` reports `rendu_js_probable`, open the page with JavaScript disabled (or read `crawl.jsonl`) and confirm with a screenshot. A page that is empty without JavaScript is invisible to most AI crawlers: this is a P1 finding.
3. **The 19 tools** of `references/tools.md`, each with its numbered screenshot.
4. **The AI panel**: 5 questions × 4 assistants (`references/ai-panel.md`), then the Wikidata search and, if wanted, the backlinks.
5. **The site screenshots** (`site-01` and following, `references/screenshots.md`), boxed in red with `scripts/annotate.py`. Check the boxes on a contact sheet.
6. **The walkthrough**: the checklist of `references/checklist-360.md`, lane by lane. Whatever a tool did not cover is looked at there (form, keyboard navigation, share preview, legal pages, structured data by page type).
7. **Competitors** (optional, internal): PageSpeed mobile, Security Headers, Mozilla Observatory and agent readability on their home page, the same day, and the number of times the AIs cite them on Q1 to Q4.
8. Note each result in `audit.json` right away (`resultats`, `fiches`, `ia`, `captures`).

## 4. The fixed grid (do not change it from one audit to another)

There are 6 categories of 5 criteria. Each criterion scores **0** (missing or wrong), **1** (partial) or **2** (correct). Each category is therefore scored out of 10.
A criterion that cannot be verified or does not apply is scored **NV** and excluded from the calculation: category score = points ÷ (2 × verified criteria) × 10. Point this out next to the score.
**Overall score = mean of the 6 category scores (each rounded to one decimal), rounded to one decimal.** `build_dossier.py` redoes the calculation from `criteres` and stops if `note` does not match. Always write "x.x / 10" (a comma in French), never out of 100.

**A. Crawling and indexing**
1. Robot access: robots.txt blocks nothing useful (CSS, JS and images included), the sitemap is complete, up to date and declared, no noindex by mistake.
2. One version of the site: http to https, www or no www, consistent canonicals, reciprocal hreflang if the site has several languages.
3. HTTP codes: no broken links, no fake 404s, no redirect chains, no 5xx errors.
4. Rendering: the main content, links and tags are in the HTML received, without waiting for JavaScript.
5. Structure: each useful page is at most 3 clicks from the home page and receives internal links; no orphan pages.

**B. Performance and front-end**
1. Core Web Vitals of real visitors (LCP < 2.5 s, INP < 200 ms, CLS < 0.1). Without real data, NV.
2. Performance measured on mobile (PageSpeed mobile, median of 3 runs).
3. Images: modern formats (WebP, AVIF), declared dimensions, sizes adapted to the screen, lazy loading below the fold.
4. Code: no needless blocking JavaScript or CSS, fonts loaded without text jumps, no mixed http content.
5. Mobile: displays at 375 px without horizontal scrolling, viewport declared, tap targets large enough.

**C. Server, security and privacy**
1. Encryption: valid certificate, TLS 1.2 or higher, HSTS.
2. Security headers: CSP, X-Content-Type-Options, X-Frame-Options or frame-ancestors, Referrer-Policy, Permissions-Policy; server version not shown.
3. Transport: compression (Brotli or gzip), caching of static files, HTTP/2 or higher, CDN if the audience is far from the server.
4. Response time: median TTFB under 800 ms, no slowness on dynamic pages.
5. Privacy: no tracker or third-party cookie before consent, refusing as easy as accepting, an up-to-date privacy policy.

**D. Content and editorial SEO**
1. Unique, descriptive titles and descriptions of the right length, counting the pages at fault; complete share preview (Open Graph).
2. Structure: one H1 per page, logical headings, semantic HTML, no glued words.
3. Depth: pages that answer the audience's questions and search intents, not just slogans.
4. Accuracy: spelling, grammar, and the same facts everywhere (figures, dates, certifications). Each contradiction is listed for approval by the site's approver (`site.validateur`).
5. Freshness and languages: dated and recent blog and news, complete and faithful translations, nothing outdated up front.

**E. Experience, accessibility and conversion**
1. In 5 seconds on the home page, you understand what it is, for whom, and why it is better.
2. One clear main call to action, visible on each key page, and an intermediate offer for visitors who are not ready (guide, trial, webinar).
3. A short form that works, with a confirmation, and labels a screen reader can read.
4. Proof and trust: customers, sourced figures, testimonials, named authors, legal information, a real contact (E-E-A-T).
5. Accessibility: contrast, alternative text, keyboard navigation, visible focus (WCAG 2.2 AA, WAVE's AIM score).

**F. GEO and authority**
1. Structured data: Organization (with `sameAs`), plus Product, SoftwareApplication, Service, LocalBusiness, Article or FAQPage according to the pages.
2. AI access: AI crawlers are not blocked without a reason, an llms.txt is present or planned.
3. Entity: an "about" page with identity, address, year, leaders; a Wikidata entry or consistent profiles (LinkedIn, directories, Google Business Profile if the business is local).
4. Citable content and authority: FAQ, buying guides, definitions, sourced figures; links and mentions from serious sites.
5. Presence in answers: the fixed panel of 5 questions (`references/ai-panel.md`). If nothing could be tested, the criterion is NV.

If the previous audit used another grid, the first audit with this one serves as a new starting point: say so, without comparing the scores directly. The findings can still be compared (`evolution`).

## 5. The 9 domains and the tasks

The report files findings in 9 domains, always the same: facts and consistency, clean pages, blog, speed and front-end, server and rendering, security and privacy, what Google understands, experience and conversion, presence in AI. A site without a blog removes that domain with `domain_order`. Each domain has: a sentence saying what it is, why it matters, a verdict with a traffic light, a key figure, its findings with screenshots, its tools, its tasks.

The tasks:
- **Three to-do lists**, one per lane, and the first letter of the code gives the lane:
  - **Content** (`C1`, `C2`...): everything settled in the site's admin or off the site, with no developer (copy, figures, typos, titles, descriptions, images and their alt text, articles, pages, FAQ, Wikidata, profiles, directories);
  - **Front-end** (`F1`...): what is settled in the page code (templates, semantic HTML, tags, structured data, responsive images, JavaScript and CSS, fonts, accessibility, forms, server rendering);
  - **Back-end and infra** (`B1`...): what is settled on the server (redirects, HTTP codes, robots.txt, sitemap, headers, cache, compression, CDN, certificate, response time, cookies and consent, access to Search Console and analytics).
  A task belongs to one lane only. If it needs two trades, split it in two linked tasks ("after F4").
- **A priority, never a date**: `prio` is 1 (P1, blocking: stops Google or AI from reading the site, or damages trust), 2 (P2, important: loses visitors, citations or requests) or 3 (P3, polish). No deadline, no effort in days: a to-do list, not a calendar.
- Each task gives the precise fix, adapted to the site's CMS or framework when known, and "Verified when...": a check anyone can repeat (a tool, a command, a page).
- `references/checklist-360.md` gives the standard fix and the default priority of each check: start there, then adapt to the site.
- **Open on what matters.** The report opens on the five looks and three tasks to start with: put the most useful ones in `first` (`["F1", "C1", "B3"]`), otherwise the most urgent come first. `view` in `audit.json` shows the site from outside: on Google, shared, and read by a robot next to what a visitor sees (`view.json` from `fixes.py` below; `image` is the prefix of a screenshot of the audit, `"site-01"`). In the panel, list in `cited_instead` the names each market answer gives instead of the site: use real names only in a report that stays internal, otherwise A, B, C.
- **Say which criterion each task answers**, with `criterion` (`"C2"`). The report then shows what it can bring on the score, and the recheck can follow it. Several tasks on one criterion share it: the label says "up to".
- **Make each task applicable by the person who reads it.** Set `site.stack` (`{"framework": "next", "host": "netlify"}`; the crawl detects it in `checks.json`, and the requester can correct it) and, in a task, as far as you can: `before` and `after` taken from the site, `where`, `how`, `snippet`, and `file` for a ready file. `assets/recipes.json` has the instructions by platform: start there. `python3 scripts/fixes.py <folder>/crawl <folder> --url <url> --brand "<brand>" --lang <en|fr>` writes the ready files to `<folder>/fixes/`. Everything in them is a draft to read: never present it as tested on the site, and leave a TODO for what the crawl cannot know.
- Approvals: the site's approver approves facts and claims, the person in charge of communication approves new pages and content before publication.
- Separate what the team controls (the fixes) from what remains uncertain (visibility). No ranking promise.

## 6. The deliverables

Everything starts from `audit.json` (`references/data-format.md`), stored with the audit's sources. In the site's folder:

1. **The report** `YYYY-MM-DD SEO GEO Audit - <domain>.md`: scores, the 30 criteria with their evidence, findings, AI panel, appendices.
2. **The remeasure protocol** `YYYY-MM-DD SEO GEO Remeasure Protocol.md`: exact addresses, settings, questions, searches tracked, noise thresholds (`remesure` in the defaults file), remeasure dates (the only place with dates).
3. **The complete report**, frozen in `YYYY-MM-DD Full audit/`:
   ```bash
   python3 scripts/build_dossier.py audit.json "<folder>/YYYY-MM-DD Full audit" --captures "<screenshots>" --pdf --single
   node scripts/build_pptx.js audit.json "<folder>/YYYY-MM-DD Full audit/captures" "<folder>/YYYY-MM-DD Full audit/YYYY-MM-DD Full audit - <domain>.pptx"
   scripts/render_pptx_pdf.sh "<...>.pptx" "<...> - slides.pdf" "<temporary folder>/sheets"
   ```
   This gives `index.html` with `captures/`, the A4 PDF, the single page (one file, screenshots and font embedded, ready to send), **the to-do as Markdown** (to tick, to paste in a ticket or a wiki) **and CSV** (to import in Notion, Jira, Linear, Trello or GitHub Projects), the PowerPoint (90 to 110 16:9 slides) and its PDF. Copy `audit.json` to `source/`, with a README. File names follow the report language (`Audit complet` in French).
4. **A web page** of the report if the tool allows it (a Claude artifact, for example), private until the requester shares it. It stays internal if competitors appear in the screenshots.
5. **The summary for management** if asked: a short deck (12 to 15 slides), competitors anonymised, one message per slide, goals as badges with no dates.
6. **The trace**: if the folder is tracked by git, a commit describing the work; never a push without agreement.

## 7. Before delivering

- `build_dossier.py` stops if `audit.json` is inconsistent (task cited but missing, task never cited, task in an unknown lane, unknown priority, tool without a card, missing criterion) or if a score does not match the 30 criteria, and flags competitor names left in the text (`competitors_regex`).
- The scores of the report and the PowerPoint are exactly those of the Markdown report (same rounding, same scale).
- Each "verified" finding has its screenshot or link; each red box is in the right place.
- Each P1 is really blocking; if there are more than 8 P1, reread them: a to-do where everything is urgent says nothing.
- Render the report in Chrome at 1280 px and 375 px (in headless mode, Chrome does not go below 500 px: measure `scrollWidth` rather than trust the screenshot).
- The PowerPoint: look at the sheets from `render_pptx_pdf.sh` one by one (cut text, overflow, overlap). A `.pptx` cannot carry its fonts, and a missing one can fall back on a serif: `signature` uses Arial there for that reason. With another font, tell the requester that the look depends on the computer that opens the file.
- No final period in titles, no field left empty, no date in the to-do.

## 8. Known traps

- Headless Chrome produces nothing without `--user-data-dir=<folder>`; the script adds it. `build_dossier.py --pdf` looks for Chrome in its usual place; otherwise, give its path in the `CHROME` variable.
- Without PowerPoint, `render_pptx_pdf.sh` goes through LibreOffice (less faithful, enough to spot an overflow).
- PowerPoint on Mac: it must open a copy with a unique, non-hidden name (otherwise it re-exports the old version or returns error -9074). Exporting 100 slides exceeds the default AppleScript timeout (the script raises it to 15 min). If PowerPoint returns -9074 on every file, a dialog is waiting: ask the user to close it. Never close their open presentations.
- pptxgenjs writes the file uncompressed: the script recompresses it.
- The built-in browser of the Claude app cannot read `file://` or `localhost`: check the pages with headless Chrome, or publish them as an artifact.
- `crawl.py` does not run JavaScript, on purpose: it sees the site as most AI crawlers do. For the speed people experience, trust PageSpeed, not the crawl.
- A host can answer "allowed" in robots.txt and still block AI crawlers at the firewall (Cloudflare, for example): if the site is absent from AI answers despite an open robots.txt, note it as a hypothesis and ask the developer to check the firewall rules.
- To check that no shape leaves a slide, `python-pptx` is enough if the pptx skill's `validate.py` does not run.

## 9. Comparing two audits

```bash
python3 scripts/compare.py <old audit.json or quick.json> <new one> [<folder>] [--lang en|fr]
```

It writes `YYYY-MM-DD Comparison - <domain>` as HTML (one file), Markdown and JSON. Keep each audit's `audit.json` or `quick.json`: the comparison needs nothing else. Read the result, then tell the requester in a few lines what really moved, what got worse, and what is still to confirm.

What the script does, so you can explain it:
- **The score is like for like**: only the criteria checked both times count. A criterion that became NV, or stopped being NV, is listed apart and moves nothing, so a tool that was down on the day does not look like progress.
- **Noise**: under 5 PageSpeed points is noise, 5 to 9 is to confirm, 10 or more counts. Any change of a security grade counts. Similarweb is always to confirm.
- **AI answers**: fill `runs` in the answers of the new audit (`references/ai-panel.md`). A citation counts if it comes back at least 2 times out of 3, and a change seen in fewer than 3 runs is marked "to confirm".
- **Tasks**: a task that left the list is "no longer listed", not "done". Before calling it done, apply its "Verified when...". In a full audit, tasks are matched by name: keep the name of a task that stays open.
- **It refuses** two different domains (`--force` after a move) and a file that does not use the 30-criteria grid: then compare the findings by hand, as in section 4.
- **A full audit against a quick one** is compared with a warning, without the published scores or the tasks. Do not present it as progress: say the evidence differs.

Never attribute a move to a fix without evidence: the comparison says what changed, not why. `--fail-on-regression` exits with code 3 if a criterion got worse or a tool clearly dropped, for use in a CI job.
