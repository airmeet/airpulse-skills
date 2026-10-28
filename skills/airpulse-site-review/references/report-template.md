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
