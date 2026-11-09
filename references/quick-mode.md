# The quick audit: about 15 minutes

A first read of a site: automatic measures, what Claude can judge by reading the pages, a small AI panel if a browser is available, and the 10 most useful fixes. No browser and no API key are required. Announce the duration at the start.

The score uses the same fixed grid as the full audit, but it is **provisional**: unchecked criteria are NV (excluded, never guessed). Never compare it with a full audit's score, and never present it as one.

## 0. The questionnaire (about 1 minute)

Ask round 1 of `intake.md` (whose site, goal, who makes the changes, what to receive), unless the site is in `sites.json`. Round 2 comes in step 2, once you have read the pages: in quick mode, only questions 5 (the offer) and 9 (the AI questions), plus 7 if you find a fact in two versions. Do not hold the measure for the answers: start it, then ask while it runs.

## 1. Measure (about 1 to 2 minutes)

```bash
python3 scripts/quick.py measure <url> <folder> --brand "<brand>" --lang <en|fr>
```

Leave out `--brand` if the request does not give the name, and never guess it from the domain, which has no accents. Once the first page is read: `python3 scripts/quick.py brand <folder>/quick.json "The exact name"`.

It crawls at most 25 pages, one per second (`--max`, `--delay`), then measures speed and accessibility, and asks Mozilla Observatory and Wikidata. If Chrome and Pillow are there, it also takes what a visitor sees and the share image, for the report's "seen from outside" part; otherwise the report shows what a robot reads, alone. A service that does not answer is noted as unavailable, with its reason, and the audit goes on. It writes `<folder>/quick.json` and `<folder>/crawl/`.

- **Speed and accessibility.** PageSpeed usually answers 429 without a key. `measure` then runs Lighthouse on this machine, with the local Chrome and `npx`; its first run downloads it (`lighthouse` from npm) and adds about a minute. `measures.psi.source` says which one answered: only the PageSpeed API has visitors' real data (B1), and `PAGESPEED_API_KEY` is used if set. With neither, B1, B2 and E5 stay NV: say so, and do not wait for pagespeed.web.dev in a browser.
- **A site that blocks the crawl** stops the script with a message. Tell the user, and suggest the full audit with a browser.
- If the site has several languages, pass the URL of the main one.

## 2. Judge what a machine cannot (about 3 minutes)

Read the pages in `<folder>/crawl/crawl.jsonl` (titles, headings) and fetch the home page and one product page. Then add to `judged` in `quick.json` the criteria you can really conclude on, each with its score and a concrete piece of evidence taken from the site:

```json
"judged": {
  "E1": ["2", "The first lines say what it is and for whom: \"quotes and schedules for tradespeople\""],
  "E2": ["1", "A trial button on each key page, nothing for visitors who are not ready"],
  "D3": ["1", "Features are explained, but no page answers \"which software should I choose?\""],
  "E4": ["1", "Testimonials without surnames, two different customer figures"]
}
```

Usually D3, E1, E2 and E4. Also F4 if the pages make it clear. Score E1 and E2 against what the person said in the questionnaire (the offer, the goal), not against your own reading alone. Check the Wikidata candidate in `measures.wikidata.hits` against its description: if it is another entity, rescore F3 in `judged`. If the content is not readable (a page that needs JavaScript and no browser), leave the criterion out rather than guess. A `judged` entry replaces the automatic score of that criterion, so only override an automatic score with evidence that it missed something, such as a firewall blocking crawlers.

**A person's site.** The questions and tasks are written for a company. For a person, ask "Who is <name>?", read a case study as the product page, and rewrite in `task_overrides` what does not fit, such as a legal name or a Wikidata entry. Say that market questions asking for a company are a high bar for a personal site.

Do not judge what needs a real test: E3 (form), C5 (consent), B3 and B5 (a real phone). They stay NV in quick mode. D4 (facts) too, unless your reading finds a real contradiction between two pages or with what the AI assistants repeat: then score it, and quote both versions. You cannot confirm that facts are right, so never score it 2 in quick mode.

## 3. A small AI panel (about 5 to 8 minutes, only with a browser)

Write **3 questions** in the language buyers use: 2 market questions a buyer would ask without knowing the brand, then "What is <brand>?". Ask them to **2 assistants**, ChatGPT and Google AI Mode, at the addresses of `references/ai-panel.md`: new conversation for each question, no account, cookies refused.

**Look before you ask.** The addresses of `ai-panel.md` send the question as soon as they open, so first open each assistant's home page, with no question in the address, and look for an account. A signed-in assistant personalises its answers and keeps the question in the person's history, so the measure is worthless and the history is theirs. If a page shows a picture, a name or no "Sign in" button, close that tab without confirming anything, never sign out, and use another assistant of the panel instead (Brave needs no account). Say which one you replaced and why. If a question left while signed in, do not use its answer, and tell the requester which one, so that they can remove it from their history.

```json
"panel": {
  "questions": {"1": "...", "2": "...", "3": "What is Atelier Lumen?"},
  "brand_question": "3",
  "assistants": [
    {"name": "ChatGPT", "kind": "assistant", "answers": [
      {"q": 1, "cited": false, "note": "Recommends three products and a press comparison"}
    ]}
  ]
}
```

`cited` is true only if the answer names the brand. Add to each market answer `"cited_instead": ["Name", "Name"]`, the sites or brands it names instead: the report counts them. By default the report stays with the requester, so use real names and say so; if they say it will be shared, write A, B, C.

 Only market questions asked to `"kind": "assistant"` count for F5. This is a snapshot, from one run: the full audit and the remeasure ask each question 3 times.

**Without a browser**: if a web search tool is available, run the 2 market questions through it and note whether the site comes up, as an assistant with `"kind": "search"` and the name of the tool. The report labels it "search results only" and it does not count in the score, because a list of search results is not an AI answer. Never present it as what ChatGPT or another AI answers. With no search tool either, leave `panel` empty: F5 stays NV and the report says so.

Never tick an "I am human" box, never sign in, and stop at a CAPTCHA: the panel is then what could be asked.

## 4. Adapt the tasks and the summary (about 2 minutes)

`quick.py` suggests a task for each criterion scored 0 or 1. The 10 most urgent come first in the report, and the others stay below them. Make them specific to the site when you know how, in `task_overrides`, keyed by **criterion** (`A3`, `F3`): the codes shown on the cards (`C1`, `B1`) are given at build, and mean something else. `drop_tasks` and `first` use criteria too:

```json
"task_overrides": {
  "A4": {"what": "The product pages are rendered in the browser: pre-render them with the framework's static export"},
  "X1": {"lane": "C", "prio": 1, "name": "Pick one customer figure", "what": "...", "check": "Verified when ..."}
},
"drop_tasks": ["C3"]
```

The report already gives, for what it can: the platform detected (correct it with `site.stack`, for example `{"framework": "wordpress", "host": null}`, if it is wrong), the instructions for it from `assets/recipes.json`, and the ready files of `<folder>/fixes/`. An override can also set `before` and `after` (text, or `{"url": "...", "title": "..."}` to show a search result), `where`, `how`, `snippet` and `file`. Take `before` from the site itself, and only write an `after` you could really publish.

A key outside the grid (`X1`) adds a task, and it needs `lane` (C, F or B), `name`, `what`, `check` and `prio`. A task that only the person can complete takes `"repair": "facts"` and `"questions": ["..."]`, the questions shown on its card: make them precise, with what this audit found ("Did the Northwind project end in May 2026?"). The grid's own tasks have general ones, which you can replace the same way. `drop_tasks` removes a suggestion that does not apply. No dates, no durations.

Choose the three tasks the report opens with in `first`, by key (`["X1", "D4", "C2"]`), when the most urgent are not the most useful to start with.

In French, the report says "vous": write "vous" too in everything you add, even for a personal site.

Write the summary in the report's language: `headline` (the message, no final period), `good` and `bad` (up to 4 short sentences each). Without them, the report falls back on the criteria names.

## 5. Build and check

```bash
python3 scripts/quick.py build <folder>/quick.json
```

It recomputes the score and refuses unknown criteria, empty evidence and incomplete tasks. It writes `YYYY-MM-DD Quick audit - <domain>.html` (`Audit rapide` in French) (one file, ready to send, with the ready files inside), the to-do as `.md` and `.csv`, and `fixes/`: the missing security headers in the host's format, an `llms.txt` drafted from the site's own titles and descriptions, an Organization block, a table of the titles to fix. Only what the measures show is missing. Nothing is applied to the site: say so, and say they are drafts to read. `--lang fr` or `en` rebuilds in the other language; the text you wrote stays in the language you wrote it in.

Deliver the report as asked in round 1: by default, publish the HTML page as a private web page when the tool allows it (a Claude artifact; it is one file with everything inside), otherwise give the file. Then tell the user, in a few lines: the provisional score and how many criteria were checked, what was unavailable and why, the 3 fixes that matter most, and that the full audit is what gives screenshots as evidence and a comparable score. If the site's code may be on this machine, offer to apply the fixes (`repair-mode.md`), and tell them how many Claude can do alone.

To follow progress, keep `quick.json` and run a new quick audit later, then `python3 scripts/compare.py <old quick.json> <new quick.json>` (`SKILL.md`, section 9). Two quick audits compare with each other; a quick audit and a full one only as an indication.

After fixes, `python3 scripts/quick.py check <folder>/quick.json` reads the site again (add task codes such as `B1,F3` for some tasks only; encryption, security headers and AI access then need one page), and `build` shows the result on the cards. Tell the requester what is confirmed, and that the score of the audit has not changed: the report's ticks and estimate are theirs, in their browser.

To have Claude apply the fixes in the site's code, on a branch and with nothing put online, see `repair-mode.md`.

## What changes compared with the full audit

| | Quick | Full |
|---|---|---|
| Time | about 15 minutes | a working day |
| Browser | optional | required |
| Pages | at most 25 | all (up to 400) |
| Criteria | about 15 to 22 of 30 | 30 |
| Evidence | measures and links | a dated screenshot for each finding |
| AI panel | 3 questions, 2 assistants | 5 questions, 4 assistants |
| Output | one web page, to-do | web page and report, to-do, remeasure protocol; PDF and PowerPoint on request |
| Score | provisional, not comparable | comparable from one audit to the next |
