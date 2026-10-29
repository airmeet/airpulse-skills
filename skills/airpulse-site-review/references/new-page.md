# New page check: is this page ready for AI search?

Use this flow when the user is building or changing a page that is not live yet ("I am creating this new page, is it ready for GEO / SEO?", "check this page before I publish", "review my draft landing page"). There is no audit finding for an unpublished page, so the review is: the page's own checks, how it plugs into the site, and how well it answers the buyer questions AirPulse tracks for the brand.

Step 0 of SKILL.md (the AirPulse connection) still comes first.

**Required for a verdict.** Do all of N1 to N5. In particular, pull the engines' answers for the target prompts (N2) and render the page (N3); these are what make this more than a generic checklist. If one of them is impossible (no tracked prompt matches, the build needs secrets you do not have), say exactly why in the report and do not give the verdict **Ready**.

## N1. Find the page and its target questions

1. Identify the page from the user's message, the current branch diff (`git diff --name-only main...HEAD`, `git status`) or the file they have open. Note the route it will have in production (for example `/compare/acme-vs-us`).
2. Give it a page type (the table in SKILL.md step 3).
3. Find what the page should be cited for:
   - Ask the user for the 1 to 3 questions a buyer would ask an AI assistant that this page should answer, unless the page makes them obvious (H1, title, question headings).
   - `list_brand_prompts(brand_id)` (page through with `offset` while `pagination.has_more`) and `get_brand_topics(brand_id)`. Pick the tracked prompts that match the page's subject. These are the target prompts. If none match, say so: the page targets questions AirPulse does not track yet, and suggest adding them as tracked prompts in AirPulse.
   - `get_brand_profile(brand_id)` for the category, audience, value proposition and competitors the page should be consistent with.

## N2. See what the engines answer today (required)

For each target prompt (up to 3):

1. `list_prompt_responses(brand_id, prompt_id, date_range="30d", limit=10)`, then `get_prompt_response(brand_id, execution_id)` for the latest succeeded answer on each engine.
2. Record: is the brand named, in what position, which competitors are named, and which URLs are cited.
3. `list_citation_pages(brand_id, prompt_ids=[...], date_range="30d", sort="citations")` for the pages cited most for these prompts, with ownership (owned, competitor, third party).

This is the bar the new page has to clear: the answer engines already have sources for these questions, and the page has to be a better one.

## N3. Render the page as a crawler sees it (required)

Use the current branch, not production. Building and running the site locally is not editing it, so do it even when the user says not to change files. Stop any server you start when you are done.

- Static or built output: build (`npm run build`, `hugo`, `astro build`) and run `page_facts.py` on the output folder or file with `--base https://<production domain>`.
- Server-rendered: build and start the production server locally on a free port (for Next.js: `npm run build && npx next start -p 3456`), then `page_facts.py --rendered --text --base https://<production domain> http://localhost:3456/<route>`.
- Preview deployment: use its URL (ask for a bypass link if it is protected).
- Cannot build: read the route's source and template and run the checks by reading the code; mark checks that need rendered HTML as `could_not_check`.

On localhost or preview hosts the canonical, og:url and sitemap URLs point at that host. Check them against the production domain and the route from N1.

Also run `page_facts.py --text` on the top 3 pages from N2 that are not the brand's own (the competitor and third-party pages engines cite). These are the comparison set for N5.

## N4. Run the checks

1. Run every check in `references/checks.md` that applies to the page type, plus the `all` checks. Record `pass`, `fail`, `warn`, `not_applicable`, `could_not_check`.
2. Run these launch checks for a new page:

| ID | Check | How |
|---|---|---|
| NEW-01 | The production canonical is the page's own final URL (absolute, https, no query string, no trailing-slash mismatch with the site's convention) | `canonical` from page_facts compared with the route. If the page sets no canonical, find what it inherits from parent layouts and site defaults (for example a root layout with `alternates: { canonical: "/" }`, a `<link rel=canonical>` in a shared head, an SEO plugin default). A page that inherits the homepage canonical tells engines it is a copy of the homepage: that is a blocker |
| NEW-02 | The page is indexable: no noindex in meta robots, X-Robots-Tag or a staging-only environment switch that reaches production | `robots_meta`, `x_robots_tag`; search the repo for the environment flag that sets noindex |
| NEW-03 | The route is not disallowed in robots.txt for search or AI answer crawlers | `page_facts.py --site https://<production domain> --check-path /<route>`: `crawlers[].paths` per bot; also read the robots source on the branch in case it changes |
| NEW-04 | The page will be in the sitemap (static entry or generated from the collection it belongs to) | sitemap source (`app/sitemap.ts`, `next-sitemap.config.js`, `@astrojs/sitemap`, CMS) |
| NEW-05 | At least 2 existing pages link to it with descriptive anchor text (navigation, a hub or index page, related articles), so crawlers find it without the sitemap | search the repo for the route in links; propose where to add links |
| NEW-06 | It is listed in llms.txt if the site keeps one and lists pages of this kind | `public/llms.txt` or its generator |
| NEW-07 | It has a share image (og:image) that resolves, and a title and description written for this page, not inherited from the layout | `og`, `title`, `meta_description` compared with the layout defaults |
| NEW-08 | It does not repeat another page: no existing page targets the same questions with the same content | `kb_search(brand_id, query=<H1 or target question>)`; compare with the top hits. If one exists, recommend merging, differentiating or a canonical, and let the owner decide |
| NEW-09 | Facts on the page match the brand's other pages (prices, plan names, numbers, founding year, locations, claims) | `kb_search` for each hard fact; flag every mismatch with both sources |

## N5. Compare with what engines cite today

Using the target prompts (N2) and the comparison set (N3):

- **Engines today:** for each target prompt, say which engines name the brand and in what position, which competitors they name, and what the answer says. Quote at most one sentence per engine.
- **Answer:** does the page answer each target question directly in its first 60 words after the H1, or under a question heading (CITE-001, CITE-002)?
- **Coverage:** list the sub-topics, comparison rows, specs, prices, steps and FAQs that appear in the cited pages or in the engines' answers but not on the new page. Report what is missing; do not copy competitor text.
- **Specifics:** count the concrete facts (numbers, named entities, dates, sources) on the new page against the cited pages. Fewer specifics is a gap.
- **Brand clarity:** is the brand named with what it is in the opening (CONTENT-001)? If engines named competitors and not the brand for these prompts, the page has to state plainly how the brand fits the question.
- **Format:** if the cited pages use a table, a numbered list or an FAQ for this question and the new page does not, recommend the format.

## N6. Verdict and fixes

Give one verdict:

| Verdict | When |
|---|---|
| **Ready** | No `fail` on a critical or high check, all launch checks pass, and the page answers each target question |
| **Ready after fixes** | Only medium or low fails, or launch checks with a clear code fix (for example a missing sitemap entry or internal link) |
| **Not ready** | Any critical or high fail (not indexable, blocked, content only after JavaScript, no answer to the target question, broken or missing schema for the page type, a fact that contradicts another page) |

Then:

1. List the fixes in order: blockers first, then the launch checks, then content gaps.
2. Show each code fix as a diff in the file that owns it (page, layout, sitemap, robots, a hub page that should link to it, llms.txt). Ask before editing.
3. For content gaps, give the exact change: which heading to add, the question it answers, the facts it needs and where they come from (the brand's own pages via `kb_search`, or a question for the owner). Never invent facts.
4. After the user applies fixes, re-run N3 and N4 on the changed page and show before and after.
5. Write `airpulse-site-review/page-<slug>.md` using the "New page report" section of `references/report-template.md`.

After the page goes live, suggest adding its target questions as tracked prompts in AirPulse (if they are not tracked yet) and running a GEO audit in a few weeks, so the page is measured.
