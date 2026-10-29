# Report template

Write `airpulse-site-review/REPORT.md` in this shape. Plain sentences, tables over prose, the most important fix first.

```markdown
# AI search review: <site>

Brand: <brand name> (AirPulse brand id <id>). Audit: <audit_id>, completed <date> (<n> days old<, stale>).
Reviewed: <n> pages on branch <branch> at <commit>, built HTML from <folder> and live URLs.

## Fix first

| # | Fix | Pages | File | Why it matters | Effort |
|---|---|---|---|---|---|
| 1 | ... | 14 (blog template) | `app/blog/[slug]/page.tsx` | ... | 1 h |

## AirPulse findings

| Finding | Page | Verdict | Evidence | Action |
|---|---|---|---|---|
| <title> (<severity>) | /pricing | confirmed | `meta_description_length` = 0 | Diff 1 |
| ... | ... | already_fixed | canonical present at `app/layout.tsx:12` | Mark task done |

Task status vs verification conflicts: <list or "none">.

## Code checks

| Check | Result | Pages failing | Evidence |
|---|---|---|---|
| CITE-001 Answer in the first 60 words | fail | 6 of 12 | ... |

## Questions for the owner

- <exact question, and which fix waits on it>

## Not checked

- <check id>: <why it could not be checked>

## Changes made

<branch name, files changed, before/after values from page_facts.py> or "No files changed yet."
```

`results.json` holds one object per check and per finding: `{ "id", "page", "result" or "verdict", "evidence", "file", "line" }`. Results are `pass`, `fail`, `warn`, `not_applicable` or `could_not_check`.

## New page report

For the new page check, write `airpulse-site-review/page-<slug>.md`:

```markdown
# Is <route> ready for AI search?

Verdict: **Ready | Ready after fixes | Not ready**. <one sentence on why>
Brand: <brand>. Page type: <type>. Checked: <branch> at <commit>, rendered from <local build | preview URL | source only>.

## Target questions

| Question (tracked prompt) | Engines that name the brand today | Pages cited most | Does the page answer it? |
|---|---|---|---|
| <prompt> | ChatGPT 3rd, Perplexity no | competitor.com/x, g2.com/y | yes, first paragraph / no |

## Fix before publishing

| # | Fix | File | Check |
|---|---|---|---|
| 1 | Remove the noindex set by the preview flag | `app/layout.tsx:14` | NEW-02 |

## Launch checks

| Check | Result | Evidence |
|---|---|---|
| NEW-04 In the sitemap | fail | `/compare/x` not in `app/sitemap.ts` |

## Content gaps against cited pages

- <sub-topic or fact the cited pages cover and this page does not>, needed for <question>. Source for the fact: <brand page via kb_search | question for the owner>.

## Page checks

| Check | Result | Evidence |
|---|---|---|

## After launch

- Track these questions in AirPulse: <list, if not tracked>.
- Run a GEO audit after the page has been crawled.
```

