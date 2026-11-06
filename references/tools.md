# The 19 tools: addresses, settings, what to record

Together with the 4 AI assistants of `ai-panel.md`, they make up the 23 external examiners of the audit. The automatic survey (`crawl.py`) also covers what no public tool measures page by page: status codes, response time, cache, compression, AI robots, llms.txt, rendering without JavaScript.

Always the same tools, at the same addresses, in the same order, so that two audits can be compared. The addresses come from `assets/defaults.<lang>.json` (key `outils`), which also holds the "What this tool is for" text shown in the report: do not rewrite it from one audit to the next.

Address variables: `{url}` the tested page (often the home page in the main language), `{url_enc}` the same, encoded, `{url_noproto_enc}` without `https://`, encoded, `{host}` the domain (including `www.` if there is one), `{host_nowww}` without `www.`, `{brand_q}` the brand, encoded for a search, `{lang}` and `{country}` (fr, fr).

| Capture no. | Tool | Publisher | Address | Setting | What to record | Report domain |
|---|---|---|---|---|---|---|
| 01 | PageSpeed Insights, mobile | Google | `https://pagespeed.web.dev/analysis?url={url_enc}&form_factor=mobile` | 3 runs, keep the middle value | Performance, LCP, accessibility, best practices, SEO, agentic browsing | d-vitesse |
| 09 | PageSpeed Insights, desktop | Google | `https://pagespeed.web.dev/analysis?url={url_enc}&form_factor=desktop` | 3 runs, middle value | Performance and real visitor data (Core Web Vitals over 28 days) | d-vitesse |
| 02 | Security Headers | Snyk | `https://securityheaders.com/?q={url_enc}&followRedirects=on&hide=on` |  | Grade, missing and present headers, server version displayed | d-securite |
| 08 | HTTP Observatory | Mozilla | `https://developer.mozilla.org/en-US/observatory/analyze?host={host}` |  | Grade, score out of 100, tests passed | d-securite |
| 13 | SSL Server Test | Qualys SSL Labs | `https://www.ssllabs.com/ssltest/analyze.html?d={host}&hideResults=on` | wait for the test to finish (2 to 3 min) | Grade, TLS version, certificate expiry date | d-securite |
| 14 | Internet.nl | Internet Standards Platform | `https://internet.nl/site/{host}/` | start the website test | Score, IPv6, DNSSEC, HTTPS, HSTS | d-securite |
| 12 | Webbkoll | 5th of July Foundation | `https://webbkoll.5july.net/en/check?url={url_enc}` |  | Third-party cookies, requests to other companies, CSP | d-securite |
| 11 | Blacklight | The Markup | `https://themarkup.org/blacklight?url={url_noproto_enc}&device=desktop&location=eu` |  | Ad trackers, third-party cookies, session recording, fingerprinting | d-securite |
| 15 | WAVE | WebAIM | `https://wave.webaim.org/report#/{url}` |  | AIM score, errors, contrast, images without a description | d-pages |
| 10 | Nu HTML Checker | W3C | `https://validator.w3.org/nu/?doc={url_enc}` |  | Errors and warnings | d-pages |
| — | LanguageTool | LanguageTooler | `https://api.languagetool.org/v2/check` | lt.py script on the crawl's titles, descriptions, H1s and H2s | Typos and glued words | d-pages |
| 06 | "site:" search | Google | `https://www.google.com/search?hl={lang}&gl={country}&q=site%3A{host}&num=100` | private browsing, cookies refused | Number of results, facts shown by Google (titles, descriptions) | d-faits |
| 21 | Brand search | Bing | `https://www.bing.com/search?q={brand_q}` |  | Position of the site, description shown, language | d-faits |
| 40 | Share preview | OpenGraph.xyz | `https://www.opengraph.xyz/url/{url_enc}` |  | Title, description and image shown when sharing (LinkedIn, messaging apps) | d-pages |
| 07 | Rich results test | Google | `https://search.google.com/test/rich-results?url={url_enc}` |  | Structured data types detected | d-google |
| 16 | Schema Markup Validator | Schema.org | `https://validator.schema.org/#url={url_enc}` |  | Items and errors | d-google |
| 18 | Similarweb | Similarweb | `https://www.similarweb.com/website/{host_nowww}/` | estimate: read it as a trend | Visits over 3 months, trend, countries, bounce | d-google |
| 22 | Wikidata | Wikimedia | `https://www.wikidata.org/w/index.php?search={brand_q}` | also search for the publisher's name | Entry present or not | d-ia |
| 41 | Backlink checker | Ahrefs | `https://ahrefs.com/backlink-checker` | optional; it asks for an "I am human" box: the user must tick it, never Claude | Domains that link to the site, estimated authority | d-ia |

The 4 AI assistants (captures 03, 04, 05, 17 for Q1, then 23 onward) are in `ai-panel.md`.

## How to record a tool

1. Open the address in the built-in browser (`preview_start` with `url`), without an account, non-essential cookies refused.
2. Wait for the test to finish (SSL Labs: 2 to 3 min; PageSpeed: 3 runs, keep the middle value).
3. Screenshot: the first screenshot of the pane often comes out blank or faded. Take one at `scale: 0.1`, then the real one. The desktop preset gives a 1024 px window and an 800 px image.
4. Copy the image (file `mcp-Claude_Browser-blob-*.jpg` in `~/.claude/projects/<project>/tool-results/`) to `screenshots/YYYY-MM-DD/NN-subject.jpg`, with the number from the left column.
5. Record in `audit.json`: `resultats.NN` (the one-line result and a v/o/r light) and `fiches.NN` (who, the big grade, one or two pills, 2 to 4 findings, a "Key takeaway" sentence, the screenshot and its caption with the date and time).

## Light thresholds

| Tool | Green | Orange | Red |
|---|---|---|---|
| PageSpeed | ≥ 90 | 50 to 89 | < 50 |
| Security Headers, Mozilla Observatory | A or B | C | D, E or F |
| SSL Labs | A or A+ | B | C or lower |
| Internet.nl | ≥ 90% | 60 to 89% | < 60% |
| Webbkoll, Blacklight | no tracker before consent | known trackers (analytics, LinkedIn) | intrusive ad trackers, session recording |
| WAVE (AIM score) | ≥ 8 | 5 to 7.9 | < 5 |
| W3C | 0 to 5 errors | 6 to 50 | > 50 |
| Structured data | Organization + business type | partial | nothing |
| Wikidata | accurate entry | incomplete entry | no entry |
| Share preview | title, description and image | one of the three is missing | nothing |
| Median TTFB (crawl) | < 800 ms | 800 to 1,800 ms | > 1,800 ms |
| AI robots (crawl) | search robots allowed | one search robot blocked | all blocked |

## Outside the list

- **check-host.net** (`check-host.net/check-http?host={url}`): does the site respond from abroad? Useful when the server blocks the office.
- **Search Console** and **Bing Webmaster Tools**: the only real figures for clicks and positions. Without access, write it in the limits and make it a P1 back-end task.
- **Google Business Profile**: for a local business, the listing on the brand search (hours, reviews, category).
