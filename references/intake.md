# The questionnaire: what only the person knows

The skill is built for people who are not developers: a freelancer auditing a client, a marketing team, a business owner. A crawl tells what the site says. It cannot tell what the site is for, what makes the offer better, or which facts are true. So the audit starts with a short questionnaire, and asks a second time only about what the measures could not settle.

Three rules:

- **Never ask what the site already says clearly.** Read it first (the crawl, or the home page), then ask to confirm in one sentence rather than to describe.
- **Every question has a default.** "I don't know" is a fine answer: the criterion becomes not verifiable (NV) or the finding a hypothesis. Never invent an answer.
- **Two rounds at most**, of four questions each. If the person has an answer ready ("the goal is bookings"), do not ask it again.

With the `AskUserQuestion` tool, ask each round in one call, with the options below; the person can always type their own answer. Without it (on claude.ai, for example), ask the round as a short numbered list in one message, with the default in brackets, and wait for the answer.

If the site is already in `~/.claude/audit-seo-geo/sites.json`, skip round 1 and say what you are reusing in one line.

## Round 1: before measuring

Ask these right after the speed (quick or full), in the person's language.

| # | Question | Options | What it changes |
|---|---|---|---|
| 1 | Whose site is it, for you? | My own site · A client's site (I am a freelancer or an agency) · My company's site (I work in the marketing team) · A prospect's site (to show what I can do) | Who reads the report. For a client or a prospect, competitors are anonymised (A, B, C) and the report is written to be handed over; for your own site it says "you" and can name them. Recorded in `site.usage` and `site.prepared_by` |
| 2 | What should the site bring in? (several answers) | Contact or quote requests · Bookings or calls · Online sales · Sign-ups or trials · Visibility and trust | Which pages count as key pages, criterion E2, and the tasks that come first. `sites.json` → `objectif` |
| 3 | Who will make the changes? | Me, in the site's admin (WordPress, Webflow, Wix, Shopify…) · A developer or an agency · Claude, in the site's code on this computer · Not decided yet | How the tasks are written: in plain words with where to click, or with code. The names of the three to-do lists (`site.who`). Claude in the code means the repair mode (`repair-mode.md`) is offered at the end |
| 4 | What do you want to receive? (several answers) | A web page to read and share (recommended: nothing to install) · A PDF · A PowerPoint · The to-do for Notion, Trello or Jira (CSV) | The deliverables of section 6 of `SKILL.md`. The web page is always made; the PDF needs Google Chrome, the PowerPoint needs Node.js: install nothing unless they are asked for |

For the full audit, also ask in this round, only if the answer is not known: the brand's exact name (accents included) and whether the business is local (then its Google Business Profile is looked at).

## Round 2: after the first measures

Once the crawl has run and you have read the home page, the offer pages and the "about" page, ask only what is still uncertain. Pick the four most useful among these, in this order:

| # | Question | How to ask it | What it changes |
|---|---|---|---|
| 5 | Is this the offer? | "I read that **<brand>** offers **<what>** to **<whom>**, and that what makes it better is **<why>**. Is that right?" · Yes · Partly (correct it) · No (say what it is) | Criterion E1 (is it understood in 5 seconds?), the market questions of the AI panel, and every sentence of the report that describes the business. `sites.json` → `activite`, `public`, `valeur` |
| 6 | Who do buyers compare you with? | "Name two or three competitors a buyer would compare you with." · I don't know, find them in the AI answers | The competitors measured in section 3.7, and the reading of the AI panel. Their names stay internal (`sites.json` → `concurrents`) |
| 7 | Which of these facts is right? | Only if the crawl or the AI answers show two versions of one fact (a figure, a price, a date, who does what): quote both, with the page of each | Criterion D4 and the "facts" tasks. The answer is what the fix says; without one, the task asks the person to decide |
| 8 | Do you have access to Search Console, or to the site's statistics? | No · Yes, I can open them or send screenshots · I can ask for it | Criteria B1 and A1, and the task that asks for the access. Without access these are NV, never guessed |
| 9 | Are these the right questions to ask the AIs? | Show the five questions of the panel (`ai-panel.md`) · Use them · Change them | The panel is fixed at the first audit, so it must be the questions real buyers ask |

For a client's site (answer "A client's site" to question 1), the freelancer may not know the answers to 5 to 7. Then write the best reading of the site, mark it "to confirm with the client", and turn it into questions on the tasks concerned (`questions`): the report carries them to the client.

## Where the answers go

- `~/.claude/audit-seo-geo/sites.json`, keyed by the domain: `activite`, `public`, `zone`, `objectif`, `valeur`, `concurrents`, `qui_corrige`, `livrables`, `theme`, `validateur`, `dossier`. The next audit of that site asks nothing in round 1.
- In `audit.json` (full) or `quick.json` (quick): `site.usage`, `site.prepared_by`, `site.who`, and a line in `conditions` that says what the person confirmed and what stays to confirm.
- In the tasks: what the person could not answer becomes `questions` on the task that needs it, never a guess in the report.
