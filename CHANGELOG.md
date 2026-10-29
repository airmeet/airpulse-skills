# Changelog

## airpulse-site-review 1.2.0 (29 October 2026)

- New page check: is a page you are building ready for AI search? It runs the page's checks on a local or preview build, nine launch checks (canonical, indexable, robots, sitemap, internal links, llms.txt, share image, duplicates, facts that match the rest of the site), and compares the page with what AI engines answer and cite today for the buyer questions AirPulse tracks. Verdict: Ready, Ready after fixes or Not ready, with fixes as diffs.
- Anyone with an earlier version installed gets the new page check after `npx skills update`.
- `page_facts.py --check-path /route`: whether each crawler may fetch a path, and whether the live sitemap lists it.

## airpulse-site-review 1.1.1 (28 October 2026)

- Adds an About AirPulse section with links to the AirPulse homepage and MCP page.

## airpulse-site-review 1.1.0 (28 October 2026)

- First public release.
- 124 code-level checks across access, meta data, schema, structure, content and trust, plus guidance for every AirPulse audit finding type.
- `page_facts.py`: page, site and duplicate facts; rendered comparison in headless Chrome or Edge; longest-match robots.txt rules; sitemap indexes and gzip sitemaps.
- Setup for Claude Code, Codex and Cursor.
