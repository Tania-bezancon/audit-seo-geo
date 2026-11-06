# The 360° checklist

Every check of the audit, sorted by lane: **Content** (`C`), **Front-end** (`F`), **Back-end and infra** (`B`). Each row says how to verify it, the standard fix, the default priority and the grid criterion it affects. Start from the standard fix, then adapt it to the site: its CMS or framework, its pages, its figures.

Priorities: **P1** blocking (Google or the AIs cannot read the site, or trust is damaged), **P2** important (loses visitors, citations or enquiries), **P3** polish. A priority can go up or down depending on the site: a false 404 on a 10-page site is P2, on a 5,000-page site it is P1.

Sources of evidence: `summary.json` and `checks.json` from the crawl (key in square brackets), the tools by their number (`references/tools.md`), the AI panel (`ai-panel.md`), or a screenshot of the site.

## Content · what you fix without a developer

| Check | Evidence | Standard fix | Verified when | Prio | Criterion |
|---|---|---|---|---|---|
| The same facts everywhere (clients, year, team, certifications, prices) | site screenshots, tool 06, panel Q5 | One validated fact sheet, carried over to every page | the "site:" search shows only one version | P1 | D4 |
| Unique, descriptive titles (50 to 60 characters, topic first, brand last) | [titres_doublons], [titres_longs_65] | Rewrite each faulty title | the crawl finds no duplicate and no title over 65 characters | P2 | D1 |
| Descriptions present (140 to 160 characters, a promise and a call to action) | [sans_description] | Write one description per page | the crawl counts 0 pages without a description | P2 | D1 |
| Share preview (title, description, 1200 × 630 image) | [sans_open_graph], tool 40 | Fill in the CMS sharing fields | the preview in tool 40 is complete | P3 | D1 |
| One H1 per page, H2s that break the page up | [h1_different_de_1] | Fix the headings in the editor | the crawl counts 0 faulty pages | P2 | D2 |
| Glued words, typos | [mots_colles], `lt-<lang>.json` | Fix each reviewed alert | lt.py returns only false positives | P2 | D4 |
| Alt text on useful images (decorative: empty alt) | [images_sans_alt], tool 15 | Describe each useful image in the CMS | WAVE reports no image without a description | P2 | E5 |
| Pages that answer the audience's questions (not just slogans) | [pages_maigres_300_mots], reading | Add the questions, use cases and figures to each key page | every key page exceeds 300 useful words | P2 | D3 |
| Blog that is dated, recent, with no outdated article up front | [pages_datees], blog screenshots | Sort: keep, merge, remove (with a redirect, see B) | no outdated article left on the first page | P2 | D5 |
| Complete translations, with no leftovers from another language | [lang], screenshots | Translate the page or remove it from the language | each language has only pages in its own language | P2 | D5 |
| An "about" page that identifies the company (legal name, address, year, executives, sourced figures) | screenshot site-03 | Complete the page | all 4 items are online | P1 | F3 |
| Named authors and dates on articles | reading | Add a real author and a date to each article | every article has both | P3 | E4 |
| Proof: clients, testimonials, sourced figures, labels | screenshot site-02 | Add proof with its context | the home page shows at least 3 verifiable proofs | P2 | E4 |
| One main call to action on each key page | screenshots | Add the main button to pages that lack one | every key page has its call to action | P2 | E2 |
| An intermediate offer (guide, grid, trial, webinar) | reading | Create the offer and link it from the pages | the offer is online with its form | P3 | E2 |
| FAQ, buying guides, definitions | reading, AI panel | Write the pages the AIs cite in our place | the pages are online and linked to each other | P2 | F4 |
| Wikidata entry, consistent profiles (LinkedIn, directories) | tool 22 | Create or fix the entry, align the profiles | the entry exists with the official site | P3 | F3 |
| Google Business Profile (local business only) | brand search | Create or complete the profile (hours, category, photos, reviews) | the profile shows on the brand search | P2 | F3 |
| Links and mentions from reputable sites | tool 41 | Target the trade press, partners, sector directories | new domains link to the site | P3 | F4 |
| Facts repeated by the AIs are correct (Q5) | AI panel | Fix the source they cite (page, profile, Wikidata) | Q5 contains no wrong figure at the remeasure | P2 | F5 |

## Front-end · what you fix in the page code

| Check | Evidence | Standard fix | Verified when | Prio | Criterion |
|---|---|---|---|---|---|
| Content readable without JavaScript | [rendu_js_probable], page without JS | Server-side rendering or static generation (SSR, SSG) for public pages | the received HTML contains the main text and the links | P1 | A4 |
| Links as real `<a href>` tags | reading the HTML | Replace JavaScript links (`onclick`) with real links | every menu link has its `href` | P1 | A4 |
| Head tags in the received HTML (title, description, canonical, hreflang, robots) | crawl | Generate them server-side, once per page | the crawl finds them on every page | P1 | A2 |
| Structured data by page type | tools 07 and 16, [jsonld_types] | Organization (with `sameAs`) across the whole site; Product, SoftwareApplication, Service, LocalBusiness, Article, FAQPage, BreadcrumbList depending on the pages | the rich results test detects them with no error | P2 | F1 |
| LCP under 2.5 s | tools 01 and 09 | Main image first (`fetchpriority="high"`, no lazy loading), preloaded, in the right format | PageSpeed mobile ≥ 75 over 3 runs | P2 | B1, B2 |
| INP under 200 ms | tool 09 (field data) | Break up long JavaScript tasks, defer third-party scripts | the real INP turns green | P2 | B1 |
| CLS under 0.1 | tools 01 and 09 | Dimensions on images and videos, reserved space for banners, `font-display: swap` with adjusted fonts | the CLS turns green | P2 | B1 |
| Images in the right format and size | tool 01, [html_lourd_100ko] | WebP or AVIF, `srcset` and `sizes`, `loading="lazy"` below the fold | PageSpeed no longer flags any image to optimise | P2 | B3 |
| Blocking or unused JavaScript and CSS | tool 01 | Defer (`defer`), split, remove dead code, inline critical CSS | PageSpeed no longer flags any blocking resource | P2 | B4 |
| Fonts | tool 01 | Self-host, preload, limit the weights, subsets | no text jump while loading | P3 | B4 |
| Mixed http content | [contenu_mixte_http] | Switch every resource to https | the crawl counts 0 faulty pages | P1 | B4 |
| Viewport and display at 375 px | [sans_viewport], screenshots site-08 and 09 | `<meta name="viewport" content="width=device-width, initial-scale=1">`, grids that collapse | no horizontal scrolling at 375 px | P1 | B5 |
| Tap targets of at least 24 × 24 px | tool 01 (accessibility) | Enlarge buttons and mobile menu links | Lighthouse no longer flags a target that is too small | P3 | B5 |
| Contrast | tool 15 | Darken light text (4.5:1 for body text) | WAVE no longer flags any contrast | P2 | E5 |
| Keyboard navigation and visible focus | manual test (Tab) | `:focus-visible` style, logical order, "skip to content" link | you can go through the page by keyboard without getting lost | P2 | E5 |
| Accessible form that confirms | screenshot site-05 | `<label>` tags, clear error messages, confirmation | WAVE flags nothing on the form | P2 | E3 |
| Valid, semantic HTML (`header`, `nav`, `main`, `footer`) | tool 10 | Fix the template errors | the W3C validator counts fewer than 5 errors | P3 | D2 |
| Breadcrumb and links between related pages | reading | Breadcrumb, "read also" blocks | each useful page receives at least 3 internal links | P3 | A5 |
| Pagination and filters | crawl | Indexable list pages, filters set to `noindex` or canonical to the list | no thousands of filter URLs in the crawl | P2 | A5 |

## Back-end and infra · what you fix on the server

| Check | Evidence | Standard fix | Verified when | Prio | Criterion |
|---|---|---|---|---|---|
| Access to Search Console and Bing Webmaster Tools | — | Verify the domain (DNS record), submit the sitemap there | clicks and positions are readable | P1 | (limits) |
| robots.txt blocks nothing useful | `robots.txt` from the crawl, [robots_bloque] | Remove the blocks on CSS, JS, images, useful pages | the crawl no longer finds a useful block | P1 | A1 |
| AI robots | [robots_ia] in `checks.json` | Allow at least the search robots (OAI-SearchBot, ChatGPT-User, PerplexityBot, Claude-SearchBot, Bingbot); decide deliberately for the training ones (GPTBot, Google-Extended, CCBot); also check the firewall | the wanted robots are "allowed" and the firewall does not block them | P1 | F2 |
| llms.txt | [llms_txt] | Publish `/llms.txt`: one sentence about the company and links to the reference pages | `/llms.txt` returns 200 | P3 | F2 |
| Complete, up-to-date sitemap | [plan_du_site], [pages_hors_plan] | Generate the sitemap automatically, with `lastmod`, and declare it in robots.txt | all useful pages are in it, and nothing else | P2 | A1 |
| One address per page | [checks.autre_hote], [checks.http], [sans_canonical] | 301 redirects to the chosen https version (with or without www), canonical on every page | the other versions redirect in a single step | P1 | A2 |
| hreflang (multilingual sites) | crawl | Reciprocal tags, `x-default` | each language links to the others | P2 | A2 |
| A real 404 | [checks.fausse_404] | Return the 404 code on an unknown address, with a useful page | `checks.json` says "vraie 404" | P2 | A3 |
| No broken links or redirect chains | [codes] | Fix the links, redirect in one step | the crawl no longer counts any 404 or chain | P2 | A3 |
| Redirects for removed pages | blog triage | A 301 to the closest page, never to the home page by default | every old address redirects to a related page | P2 | A3 |
| No 5xx errors | [codes] | Fix the cause on the server, monitor | the crawl no longer counts any 5xx | P1 | A3 |
| Certificate, TLS, HSTS | tools 13 and 14 | TLS 1.2 and 1.3 only, HSTS with a `max-age` of at least 6 months | SSL Labs gives A or A+ | P1 | C1 |
| Security headers | tools 02 and 08, [checks.accueil.securite] | Content-Security-Policy, X-Content-Type-Options, frame-ancestors or X-Frame-Options, Referrer-Policy, Permissions-Policy | Security Headers gives B or better | P2 | C2 |
| Server version hidden | [version_serveur_affichee] | Remove the version from the `Server` and `X-Powered-By` headers | no version appears | P3 | C2 |
| Compression | [checks.accueil.compression] | Brotli (or gzip) on HTML, CSS, JS, SVG | compression is no longer "aucune" | P2 | C3 |
| Cache for static files | [sans_cache], tool 01 | `Cache-Control: public, max-age=31536000, immutable` on versioned files | PageSpeed no longer flags a cache that is too short | P2 | C3 |
| HTTP/2 or HTTP/3, CDN | tool 14, headers | Enable at the host or the CDN | the test confirms it | P3 | C3 |
| Server response time | [ttfb_median_ms], tool 01 | Page cache, CDN, lighter database queries | median TTFB under 800 ms | P2 | C4 |
| No tracker before consent | tools 11 and 12, screenshot site-01 | Block third-party scripts until the click, consent mode | Webbkoll sees no third-party request before consent | P1 | C5 |
| Refusing as easy as accepting | screenshot site-01 | A "Refuse" button at the same level as "Accept" | the banner has both buttons | P2 | C5 |
| Audience measurement in place and compliant | reading, tool 12 | A privacy-friendly measurement tool, or one subject to consent, with conversion goals declared | enquiries are counted | P2 | (limits) |
| Backups and uptime monitoring | — | Monitor the home page and the form, alert on failure | a test alert arrives | P3 | C4 |

## What you do not tick off

- **A position in Google** or **a citation by an AI**: these are results, not tasks. They are tracked in the reference table and at the remeasure.
- **Traffic volume** (Similarweb): a trend, never a goal.
