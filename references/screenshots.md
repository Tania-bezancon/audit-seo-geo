# Proof screenshots

Every "verified" finding has its screenshot or its link. Screenshots are real, taken on the day of the measurement, never retouched: only red frames point out the defect.

## Where and how to store them

- Folder: `<site folder>/screenshots/YYYY-MM-DD/`, with a `site/` subfolder for the screenshots of the site's pages.
- Names: `NN-subject.jpg` for tools and AIs (fixed numbers, see `tools.md` and `ai-panel.md`), `site-NN-subject.jpg` for the site's pages. The number stays the same from one audit to the next.
- The HTML report and the PowerPoint find a screenshot by the start of its name (`"06"`, `"site-03"`): two files must not start the same way.

## Site screenshots to take at every audit

| No. | Page | What to show |
|---|---|---|
| site-01 | Home page, on first display | The cookie banner. Record the network requests at the same time (`read_network_requests`): if Google Analytics, LinkedIn or others fire before the click, that is a finding |
| site-02 | Home page, proof block | Logos, figures, testimonials: with or without context |
| site-03 | About | The facts (year, publisher, address) to compare with the title, the sharing tags and the reference sheet |
| site-04 | A product or use-case page | Typos or glued words, framed |
| site-05 | Contact or demo request | Required fields, captcha, promised response time |
| site-06 | A page in another language | Missing translation, title in another language |
| site-07 | The blog, the oldest page | Dates, generic images |
| site-08, 09 | Home page at 375 px | Empty screen, then displayed content (`mobile` preset of `resize_window`, then back to `desktop`) |

Add as many as needed (site-10…), always one screenshot per finding.

## Known pitfalls

- The first screenshot of the built-in browser often comes out blank or faded: take one at `scale: 0.1`, then the real one.
- Desktop preset: 1024 px window, 800 px image. Multiply the page coordinates by 0.78125 to place a frame.
- Check every red frame on a contact sheet: a misplaced frame undermines the finding.
- A refused cookie banner stays refused in the built-in browser's profile: for site-01, open the home page in a new tab in a private window if the banner no longer shows, or note it.
- Never capture a logged-in production area (the customers' application, an intranet): colleagues' names and internal files.
- AI screenshots show competitors' names: the full report stays for internal use. The deck for management anonymises them (A, B, C…).
