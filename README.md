# AirPulse agent skills

Agent skills from [AirPulse](https://airpulse.ai/?utm_source=github&utm_medium=referral&utm_campaign=airpulse-site-review&utm_content=home) for Claude Code, Codex, Cursor and the other agents that the [skills](https://skills.sh) installer supports.

```bash
npx skills add airmeet/airpulse-skills
```

## airpulse-site-review

Your coding agent reviews your website's code, page by page, for what AI search engines need: pages they can fetch, understand, trust and quote. It reads your AirPulse GEO audit through the AirPulse MCP, confirms each finding in your source code, runs 124 code-level checks, and proposes fixes as diffs in the right files.

Then ask your agent either of these:

- *"I am creating this new page. Is it ready for GEO and SEO? If not, what should I change?"* The agent builds the page locally, runs the checks for its page type and the launch checks (canonical, sitemap, internal links, robots, llms.txt, share image, duplicates, facts that match the rest of your site), compares it with what ChatGPT, Perplexity and Gemini answer and cite today for the buyer questions you track in AirPulse, and gives a verdict (Ready, Ready after fixes, Not ready) with the fixes as diffs.
- *"Review this site for AI search with AirPulse."* The agent confirms every finding in your AirPulse GEO audit against your code and proposes fixes.

| Area | What it checks |
|---|---|
| Access | robots.txt rules for search and AI crawlers, llms.txt, sitemap and lastmod, pages that only render with JavaScript |
| Meta data | titles, descriptions, canonical, robots tags, language, Open Graph |
| Schema | JSON-LD that parses, fits the page type and matches what the page shows |
| Structure | one H1, heading order, question headings, tables and lists |
| Content | answer first, quotable sections, specific facts with sources, prices as text |
| Trust | authors, dates, about and contact pages, outbound sources |

### Before you start: connect the AirPulse MCP

Create a token in AirPulse: **Settings > API Keys > MCP Access Tokens**. The server URL ends with a slash.

```bash
# Claude Code
claude mcp add --transport http airpulse https://prod-api.airpulse.ai/mcp/ \
  --header "Authorization: Bearer <your token>"

# Codex
export AIRPULSE_MCP_TOKEN=<your token>
codex mcp add airpulse --url https://prod-api.airpulse.ai/mcp/ --bearer-token-env-var AIRPULSE_MCP_TOKEN
```

Cursor (`~/.cursor/mcp.json`):

```json
{ "mcpServers": { "airpulse": {
  "url": "https://prod-api.airpulse.ai/mcp/",
  "headers": { "Authorization": "Bearer <your token>" } } } }
```

Keep the token out of your repository. The skill checks the connection first and stops if it cannot reach your AirPulse account.

### What it does not do

- It does not edit files without asking, and it does not invent prices, reviews, authors or dates.
- It does not change which crawlers you allow. That is your decision.
- It sends no code anywhere. It calls your AirPulse MCP and reads your own public pages.
- Its one script, `page_facts.py`, uses only the Python standard library (3.9 or newer). With `--rendered` it opens your pages in your local headless Chrome or Edge.

### Requirements

An AirPulse account with the MCP enabled, Python 3.9 or newer, and optionally Chrome or Edge. Learn more about the [AirPulse MCP](https://airpulse.ai/product/mcp?utm_source=github&utm_medium=referral&utm_campaign=airpulse-site-review&utm_content=mcp).

### Update or remove

```bash
npx skills update
npx skills remove airpulse-site-review
```

## License

Copyright AirPulse. Free to install and use with an AirPulse account. See [LICENSE](LICENSE).
