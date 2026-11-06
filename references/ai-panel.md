# The AI panel: what the AIs answer

Ask **5 fixed questions** to **4 assistants**, without an account, and note whether the brand is cited. The panel is fixed at the first audit of a site, written into `audit.json` (`ia.questions`) and into the remeasure protocol, then never changes: otherwise two measurements cannot be compared.

## Writing the 5 questions

- **Q1 to Q4, market questions**: the ones a buyer asks without knowing the brand. Write them in the language(s) buyers of the audited site use, whatever the language of the report. Include at least one question in English if the site targets international buyers. Vary the angles: the category ("which solutions for…"), the comparison with the leader ("what alternative to…"), a precise use case ("for a crisis unit"), the audience ("for a public body").
- **Q5, the brand question**: "What is <brand>?". It checks that the facts the AIs repeat are correct.
- The questions are validated with the client before the measurement.

Example (Atelier Lumen, a fictional site selling quoting and scheduling software to UK tradespeople):
1. Which quoting and scheduling software should a UK electrician choose?
2. What is a simple alternative to job management software for a small plumbing business?
3. How can a tradesperson write quotes on their phone?
4. Which quoting software do UK builders use?
5. What is Atelier Lumen?

## The 4 assistants

**Look before you ask.** The addresses below send the question as soon as they open, so never open one first. Open each assistant's home page, with no question in the address (`https://chatgpt.com/`, `https://www.google.com/`, `https://search.brave.com/`, `https://www.perplexity.ai/`), and look for an account: a picture, a name, or no "Sign in" button. If there is one, answers would be personalised and the questions would land in the person's history: close the tab, never sign out, tell the requester, and use a private profile or mark that assistant as not asked. If a question ever left while signed in, do not use its answer, and tell the requester which assistant and which question, so that they can remove it from their history.

**Wait for the end of the answer.** An assistant can take a minute. An answer that stops mid-sentence, or a page still saying it is answering, is not an answer: read it again before noting anything. An anonymous conversation usually cannot be reopened, so note it when you read it.

| Assistant | Address (`{q}` = encoded question) | Condition |
|---|---|---|
| ChatGPT | `https://chatgpt.com/?hints=search&q={q}` | no account, web search on |
| Google AI Mode | `https://www.google.com/search?hl={lang}&gl={country}&udm=50&q={q}` | no account, cookies refused |
| Brave | `https://search.brave.com/ask?q={q}` | no account |
| Perplexity | `https://www.perplexity.ai/search?q={q}` | no account: only one question accepted. After that it asks for a sign-up, but the answer is often already in the page: extract it with `get_page_text` and say so in the note |

## Asking and scoring

- A new conversation for each question. Wait for the answer to finish before the screenshot (scroll if the list is long).
- Screenshot numbers: Q1 of the morning at 03 (Perplexity), 04 (ChatGPT), 05 (Google), 17 (Brave); the following questions from 23 onward, assistant by assistant.
- For each answer, in `ia.assistants[].answers[]`: `q`, `cited` (true if the brand is named), `capture`, `note` (one sentence: what the AI recommends instead, anonymising competitors as "competitor A, B…" in anything that leaves the team), `hour`.
- On the brand question, record every figure it repeats (file sizes, encryption, year, publisher's name, number of participants) and compare it with the reference sheet: a wrong figure is a finding in the "Facts" domain. Frame these figures in red on the screenshot (`scripts/annotate.py`).
- Category score = answers that cite the brand ÷ answers obtained on Q1 to Q4. Brand score = Q5 described correctly or not.
- At the remeasure: each question 3 times; a citation counts if it comes back in 2 runs out of 3. Note the 3 results in the answer as `"runs": [true, true, false]`: `scripts/compare.py` uses them, and marks a change seen in fewer than 3 runs as "to confirm".

## What to write

- The `d-ia` domain of the report (block `{"type": "ia"}`): the table of answers, a "Key takeaway" sentence (`ia.note`) on what the AIs cite in our place (buying guides, comparisons, press, public tools), then each AI question by question.
- Criterion F5 of the grid.
- A line in the reference table: "Citations across N market answers".
- The Wikidata search (tool 22): without an entry, the AIs misidentify the publisher.
