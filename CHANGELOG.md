# Changelog

## 1.1.0

- Made for people who are not developers: freelancers, marketing teams, business owners.
- A short questionnaire first (`references/intake.md`): whose site, its goal, who makes the changes, what to receive. After the first measures, only what the site cannot tell: the offer and what makes it better, the competitors, a fact found in two versions, the access to statistics, the questions for the AIs. "I don't know" leaves a criterion unchecked, never guessed.
- The report is delivered first as one web page, published as a private Claude artifact when the tool allows it. The PDF and the PowerPoint are made only when asked for, and Claude installs nothing unasked.
- Fixed: the home page was read twice when the address had no final slash, which doubled it in `llms.txt` and flagged its title as a duplicate.
- Fixed: the draft security policy (`_headers` and the others) blocked the fonts, scripts and frames a site loads from other hosts; it now lets them through.
- Fixed: the full report stopped when the share image of `view.json` was an address, or when a tool without a screenshot, such as LanguageTool, was cited in a domain.
- Fixed: a site that describes itself as a kind of organisation (a travel agency, a shop, a law firm…) no longer gets an Organization block to add, nor a lower score for it.
- The full report names the tasks that fall back on general questions, so that each one asks what this audit found.

## 1.0.0

- Available as a Claude Code plugin, and still as a skill folder.
- It follows your fixes: the gain of each one, ticks and progress remembered in the browser, and `quick.py check` to reread the site and confirm them.
- Fixes applied in the code on request (`scripts/repair.py`, `references/repair-mode.md`): on a branch, one commit per task, secrets and invented facts refused, the local site read before and after. Nothing is pushed or published.
- The install command of the README is fixed, tests run on GitHub, and the exact brand is set after reading the site (`quick.py brand`).
- A report can take the look of the audited site: titles' weight, logo, and any open-licence font.
- An empty page built by a few scripts now counts as empty, and a new measure really reads the site again.
- Speed and accessibility measured without a key: Lighthouse on your machine when PageSpeed refuses.
- The address of the site itself is checked: a redirect that says nowhere to go no longer scores as healthy.
- The AI panel looks for an account before sending any question.
- Tasks that need you come with their questions and a form to paste, and a question left unanswered stays in it. No task disappears after the first 10, and the Markdown and CSV to-do follow the fixes.
- A clearer report: five looks and three tasks to start with, the site seen on Google, shared and by an AI crawler, and who gets cited instead.
- Fixes you can apply: the platform of the site is detected, tasks say where to act and what to paste, the report shows before and after, and ready files are written to `fixes/`.
- The look of the Blue Hours Studio film across reports, PowerPoint and project page, with its fonts embedded (SIL OFL).
- Quick audit: about 15 minutes, no browser or API key required, a provisional score and the 10 most useful fixes.
- Comparison of two audits: score like for like, noise thresholds, AI answers and tasks.
- English first: skill, references, reports and example. Reports in English or French.
- Your sites, themes, fonts, logos and the PowerPoint dependency now live in `~/.claude/audit-seo-geo/`, so updates keep them.
