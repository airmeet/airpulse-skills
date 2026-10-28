# Checks

124 checks. Run every check that applies to the page type (`site` = once per site). Record `pass`, `fail`,
`warn`, `not_applicable` or `could_not_check` with the evidence. Field names in `How to test` refer to the
output of `scripts/page_facts.py`. The same list is in `checks.json` for scripts.

AP checks describe what each AirPulse audit finding type means and how to confirm it in code before
you act on it. Match them by `finding_type`.

## Technical

### TECH-002: Search and AI answer crawlers can fetch the site: Googlebot, Bingbot, OAI-SearchBot, ChatGPT-User, Claude-SearchBot, Claude-User, PerplexityBot, Perplexity-User

Severity: critical. Pages: all.

- Why: These bots fetch pages for Google AI Overviews, Bing/Copilot, ChatGPT search, Claude and Perplexity; a block removes the site from those answers no matter how good the page is.
- Where in code: robots.txt source (see TECH-001); also edge/WAF bot rules (Cloudflare Bot Fight Mode, Vercel firewall, middleware.ts user-agent checks) that return 403/429 to these user agents.
- Rule: For each of these 8 user agents (they fetch pages to answer users), the effective robots group (its own group, else `User-agent: *`) does not contain `Disallow: /` and does not disallow the directories that hold indexable content. Googlebot or Bingbot blocked = critical fail; any of the answer bots blocked = fail. Report it and ask the owner; never edit robots rules yourself. No middleware or server config returns 403/429/503 for these user-agent strings.
- How to test: HTTP check: page_facts.py --site crawlers[] gives ALLOWED, RESTRICTED or BLOCKED per bot, with root_allowed, pages_allowed and disallowed_paths (longest-match rules). For RESTRICTED, check whether the disallowed paths hold content. Repo: grep -rniE "GPTBot|ClaudeBot|PerplexityBot|OAI-SearchBot|ChatGPT-User|bingbot|user-agent" middleware.* src/ server/ vercel.json netlify.toml _headers nginx*.conf .htaccess. Optional live probe: curl -A '<bot UA>' -o /dev/null -w '%{http_code}' on 3 key URLs.

### TECH-005: Indexable pages carry no noindex, noai or bot-specific block in meta robots or X-Robots-Tag

Severity: critical. Pages: all.

- Why: A page-level noindex or noai overrides an open robots.txt and silently drops the page from search and AI answers.
- Where in code: Next.js app router: `metadata` export or `generateMetadata` in app/**/page.tsx and layout.tsx; pages router: next/head in pages/** or _document; Nuxt: useHead/useSeoMeta or nuxt.config app.head; Astro: <head> in src/layouts/*.astro; Remix: `meta` export; WordPress: theme header.php, wp_head hooks, Yoast/Rank Math settings; static: <head> of each .html file. Headers: next.config.js `headers()`, middleware.ts, vercel.json/netlify.toml/_headers, nginx/Apache config, WordPress Yoast/Rank Math per-post 'Allow search engines' toggle and Settings > Reading 'Discourage search engines'.
- Rule: On every page meant to be indexed: robots_meta does not contain noindex, none, noai or noimageai; no <meta name="GPTBot|googlebot|bingbot|.."> with noindex; x_robots_tag header does not contain noindex, none or noai. nofollow on a whole page is flagged (blocks link discovery). noindex is allowed only on login, cart, checkout, account, search-results, thank-you and staging pages.
- How to test: page_facts.py: robots_meta, x_robots_tag per page. Repo: grep -rniE "noindex|robots:\s*\{|index:\s*false|X-Robots-Tag|noai" across app/ pages/ src/ config files.

### TECH-007: Main content, H1 and internal links are present in the initial server HTML

Severity: critical. Pages: all. AirPulse finding types: low_citability.

- Why: GPTBot, ClaudeBot and PerplexityBot read the raw response and do not run JavaScript; content that appears only after hydration does not exist for them.
- Where in code: Route rendering mode: Next.js app router server components vs 'use client' at page level and client-side data fetching (useEffect/SWR/React Query) for body copy; pages router getServerSideProps/getStaticProps vs client fetch; Nuxt ssr:false or <ClientOnly>; Astro client:only islands; Angular without SSR (@angular/ssr); CRA/Vite SPA with a single index.html; Gatsby/Remix loaders; WordPress themes or page builders that load content via AJAX.
- Rule: For each page type: word_count in initial HTML >= 150 (500+ with title, meta, canonical, H1 and valid JSON-LD is strong); text_in_initial_html_ratio >= 0.8; h1_count >= 1 in raw HTML; the first paragraph, prices, product specs, FAQ answers and review text are in the raw HTML, not loaded by client-side fetch, infinite scroll or a third-party widget; nav and in-content links are <a href> elements in raw HTML. Fail if the body is an empty #root/#app/#__next shell or text_in_initial_html_ratio < 0.4.
- How to test: page_facts.py --rendered: word_count, rendered_word_count, text_in_initial_html_ratio, h1_count vs rendered_h1_count, internal_links, looks_client_rendered, has_noscript_content. Repo: grep -rn "'use client'" app/**/page.tsx; grep for ssr: false, client:only, ClientOnly, useEffect(() => fetch; check package.json for SPA-only setups (react-scripts, vite without SSR plugin, Angular without @angular/ssr).

### AP-002: AI search crawlers named in the finding can fetch the site

Severity: high. Pages: all. AirPulse finding types: ai_crawler_blocked.

- Why: Confirms an AirPulse audit finding in code before you act on it.
- Where in code: public/robots.txt or app/robots.ts rules[] (Next.js), WordPress robots filter / SEO plugin, CDN-injected robots (Cloudflare 'AI bots' managed robots).
- Rule: Pass if each crawler in evidence.detail.bots may fetch '/'. Blocking training-only crawlers (GPTBot, ClaudeBot, Google-Extended, Applebot-Extended, CCBot) can be a deliberate policy: confirm with the owner, never change robots rules yourself.
- How to test: Read the robots source and evaluate each bot with longest-match rules. Compare with the live file (a CDN can add rules). page_facts --site lists access per crawler. Compare with the evidence in get_audit_finding. Use TECH-002 and TECH-003 for the full test.

### AP-007: The homepage's main copy is in the server HTML

Severity: high. Pages: home. AirPulse finding types: client_side_rendered_homepage.

- Why: Confirms an AirPulse audit finding in code before you act on it.
- Where in code: Next.js: 'use client' at page/layout level, dynamic(..., {ssr:false}), client-only data fetch; CRA/Vite SPA index.html; Nuxt ssr:false; Angular without SSR/prerender.
- Rule: Pass if the first HTML response carries the headline and main copy without JavaScript. Fail if the page is an empty app shell (#root, #__next, #app) filled in by scripts. Confirm on the current build before proposing any rendering change.
- How to test: page_facts: word_count and looks_client_rendered on the homepage. In the repo, check the home route for 'use client' at the top, dynamic(..., { ssr: false }) or content loaded in useEffect. Compare with the evidence in get_audit_finding. Use TECH-007 for the full test.

### TECH-001: robots.txt is served at the site root, parses cleanly and points to the sitemap

Severity: high. Pages: site. AirPulse finding types: missing_robots_txt.

- Why: Every crawler, AI or not, reads robots.txt first; a missing, HTML-returning or malformed file leaves access to each bot's default guess.
- Where in code: public/robots.txt or static/robots.txt; Next.js app/robots.ts (MetadataRoute.Robots); Nuxt @nuxtjs/robots config; Astro public/ or astro-robots-txt integration; WordPress virtual robots.txt (Settings > Reading, Yoast/Rank Math file editor) or a physical file in the web root; CDN/edge rules that rewrite /robots.txt.
- Rule: GET /robots.txt returns 200 with Content-Type text/plain (not text/html, not a redirect to the homepage). Every Allow/Disallow line sits under a User-agent line. At least one `Sitemap:` line with an absolute https URL that returns 200. Any `Crawl-delay` for an AI or search bot is flagged for review.
- How to test: HTTP check: fetch /robots.txt, record status and Content-Type, page_facts.py --site: robots_txt_status, robots_txt_content_type, crawl_delays, sitemaps_in_robots (consecutive User-agent lines share one rule block). Repo: locate the generator (grep -r "robots" app/ public/ static/ next.config.* nuxt.config.* astro.config.*).

### TECH-004: robots.txt has no blanket block and does not disallow content paths or rendering assets

Severity: high. Pages: all.

- Why: A stray `Disallow: /`, a wildcard over /blog or /products, or blocked JS/CSS bundles hides content from every bot that respects the wildcard group.
- Where in code: robots.txt source (see TECH-001).
- Rule: `User-agent: *` group has no `Disallow: /`. No Disallow pattern matches a URL listed in sitemap.xml or a top-level nav URL. No Disallow on framework asset paths (/_next/, /_nuxt/, /assets/, /wp-content/, /wp-includes/*.js|css) needed to render pages.
- How to test: HTTP check: parse robots.txt, then test every sitemap URL (or a 50-URL sample) and the nav hrefs against each Disallow pattern (support * and $). Repo: list the nav and route directories and compare.

### TECH-006: Staging-only crawl blocks cannot leak into the production build

Severity: high. Pages: all.

- Why: Sites often ship a 'Disallow: /' robots.txt or global noindex meant for preview environments; one wrong env var takes the whole site out of AI answers.
- Where in code: Env-conditional code in app/robots.ts, next.config.js headers(), middleware.ts, nuxt.config robots module, astro.config, WordPress wp-config.php (WP_ENVIRONMENT_TYPE) and blog_public option; CI/CD env files (.env.production, vercel.json, netlify.toml).
- Rule: Any code path that emits Disallow: / or noindex is gated on an explicit non-production condition (e.g. VERCEL_ENV !== 'production', NODE_ENV, hostname check) and the production value of that condition is set so the block is off. Fail if the block is unconditional or keyed on a variable not defined for production.
- How to test: Repo: grep -rnE "noindex|Disallow: /\s*$|disallow: ['\"]/['\"]" and read the surrounding condition; check .env.production / deployment env for the gating variable. HTTP check on production: robots.txt and one page's X-Robots-Tag.

### TECH-008: Title, meta description, canonical, robots and Open Graph tags are in the server HTML, not set by client JavaScript

Severity: high. Pages: all.

- Why: Non-rendering crawlers take metadata from the raw <head>; tags written by react-helmet or document.title after load are invisible to them and can contradict the raw values.
- Where in code: Next.js app router: `metadata` export or `generateMetadata` in app/**/page.tsx and layout.tsx; pages router: next/head in pages/** or _document; Nuxt: useHead/useSeoMeta or nuxt.config app.head; Astro: <head> in src/layouts/*.astro; Remix: `meta` export; WordPress: theme header.php, wp_head hooks, Yoast/Rank Math settings; static: <head> of each .html file. Anti-patterns: react-helmet/vue-meta in a client-only SPA, document.title or document.head.appendChild in useEffect/mounted, tag manager scripts writing meta tags.
- Rule: title, meta_description, canonical and og:title are non-empty in the raw HTML and equal (whitespace-normalised) to the values in the rendered DOM. No source file sets document.title or inserts <meta>/<link rel=canonical> from client-side code.
- How to test: page_facts.py raw vs rendered: title, meta_description, canonical, og. Repo: grep -rnE "document\.title|document\.head|createElement\(['\"](meta|link)" src/ app/ components/.

### TECH-010: Every indexable page has exactly one unique <title> of 15-65 characters

Severity: high. Pages: all.

- Why: The title is the first label an engine attaches to a page when choosing which source to cite; missing, duplicate or template titles blur pages together.
- Where in code: Next.js app router: `metadata` export or `generateMetadata` in app/**/page.tsx and layout.tsx; pages router: next/head in pages/** or _document; Nuxt: useHead/useSeoMeta or nuxt.config app.head; Astro: <head> in src/layouts/*.astro; Remix: `meta` export; WordPress: theme header.php, wp_head hooks, Yoast/Rank Math settings; static: <head> of each .html file. Also check title templates (Next.js metadata.title.template, Yoast title patterns) that append long brand suffixes.
- Rule: Exactly one <title> in <head>; length 15-65 characters after trimming; no two indexable URLs share the same title; not a generic placeholder ("Home", "Untitled", framework default such as "Create Next App", "React App", "Vite + React").
- How to test: page_facts.py: title for each sampled page; compare across pages for duplicates. Repo: grep -rnE "Create Next App|React App|Vite \+|<title>" for defaults.

### TECH-012: Each indexable page has one absolute, self-referencing canonical that resolves to a 200 page

Severity: high. Pages: all.

- Why: The canonical tells engines which URL to credit; a wrong or missing canonical splits signals or points citations at the wrong page.
- Where in code: Next.js app router: `metadata` export or `generateMetadata` in app/**/page.tsx and layout.tsx; pages router: next/head in pages/** or _document; Nuxt: useHead/useSeoMeta or nuxt.config app.head; Astro: <head> in src/layouts/*.astro; Remix: `meta` export; WordPress: theme header.php, wp_head hooks, Yoast/Rank Math settings; static: <head> of each .html file. Next.js metadata.alternates.canonical and metadataBase; Yoast/Rank Math canonical field; Shopify theme canonical_url.
- Rule: Exactly one <link rel="canonical">; absolute https URL; equals the page's own preferred URL (same host, protocol, trailing-slash form) on unique pages; target returns 200 and is not noindexed; no chain (canonical target does not canonicalise elsewhere); deep pages never canonicalise to the homepage; any HTTP Link: rel=canonical header agrees with the HTML tag.
- How to test: page_facts.py: canonical per page, compared with the fetched URL; HTTP check: HEAD the canonical target. Repo: confirm metadataBase / site URL constant is the production https host and that canonical is set per route, not once in the root layout.

### TECH-014: Missing pages return a real 404 or 410, not a 200 'not found' page

Severity: high. Pages: all.

- Why: Soft 404s look like real pages, so engines may index or cite empty 'not found' content and waste crawl time on it.
- Where in code: Next.js notFound() in pages/routes and app/not-found.tsx; pages router getStaticProps/getServerSideProps returning { notFound: true }; SPA catch-all routes and server fallbacks to index.html; WordPress 404.php; dynamic [slug] routes that render an empty template when data is missing.
- Rule: GET of a random non-existent path (e.g. /this-page-does-not-exist-<random>) and of a non-existent dynamic slug (e.g. /blog/<random>) returns 404 or 410. Dynamic routes call the framework's not-found mechanism when the record is missing.
- How to test: HTTP check: curl -s -o /dev/null -w '%{http_code}' on both probes. Repo: read each dynamic route ([slug], [...slug], _id) and confirm a not-found branch exists.

### TECH-015: sitemap.xml is valid and lists only canonical, indexable, 200-status URLs

Severity: high. Pages: site.

- Why: The sitemap is how crawlers and AI agents find the pages that matter; listing redirects, noindexed or blocked URLs wastes their visits and muddies the signal.
- Where in code: Next.js app/sitemap.ts or next-sitemap config; Nuxt @nuxtjs/sitemap; Astro @astrojs/sitemap; Gatsby gatsby-plugin-sitemap; WordPress core wp-sitemap.xml or Yoast/Rank Math sitemap_index.xml; static public/sitemap.xml.
- Rule: /sitemap.xml (or the URL in robots.txt) returns 200 with valid XML (<urlset> or <sitemapindex>). Each child file <= 50,000 URLs. Every <loc> is absolute https on the canonical host. A sample of 20 URLs (or all if fewer) all return 200, self-canonicalise, are not noindexed and are not disallowed in robots.txt. Count of URLs is within a sensible range of the site's real indexable pages (no tag/search/parameter bloat).
- How to test: HTTP check: page_facts.py --site sitemap (is_index, children, urls, url_with_lastmod, sample), then request a sample of 20 URLs. Repo: read the sitemap generator to see which collections/routes it includes and excludes.

### AP-003: The site serves /llms.txt

Severity: medium. Pages: site. AirPulse finding types: missing_llms_txt.

- Why: Confirms an AirPulse audit finding in code before you act on it.
- Where in code: public/llms.txt, app/llms.txt/route.ts, static/, WordPress plugin or uploads root, edge rewrite.
- Rule: Pass if /llms.txt returns 200 with content on the canonical host. If the file is live but the audit could not read it, a firewall, bot protection or a www/apex split is the usual cause: report it as already_fixed or false_positive with that reason.
- How to test: Search the repo for llms.txt (file or route). Check with a normal browser user agent: curl -A 'Mozilla/5.0' -s -o /dev/null -w '%{http_code}' <origin>/llms.txt. Compare with the evidence in get_audit_finding. Use TECH-017 and TECH-018 for the full test.

### TECH-003: Training and secondary AI crawlers follow a deliberate policy: GPTBot, ClaudeBot, Google-Extended, Applebot-Extended, Amazonbot, Meta, GoogleOther

Severity: medium. Pages: all.

- Why: These control Gemini, Apple Intelligence, Alexa and Meta AI use of the site; blocking them narrows where the brand can be described, with little upside for a brand that wants to be cited.
- Where in code: robots.txt source (see TECH-001).
- Rule: Report the status of GPTBot, ClaudeBot, anthropic-ai, Google-Extended, Applebot-Extended, Amazonbot, GoogleOther, FacebookBot, Meta-ExternalAgent, CCBot, cohere-ai and Bytespider. Blocking these mostly affects model training and some assistants, so it is a business decision: PASS if allowed, or if blocked with a documented reason (a robots.txt comment, a policy page or the owner's answer). Otherwise WARN and add a question for the owner. Never fail the page for it and never change the rules yourself.
- How to test: HTTP check: page_facts.py --site crawlers[]; report each bot's status.

### TECH-009: Content in tabs, accordions, 'read more' and mobile layouts is in the DOM at load

Severity: medium. Pages: all.

- Why: Crawlers do not click; answers hidden in a tab that fetches on click, or removed from the mobile render, are never read. Google crawls only as a mobile device.
- Where in code: Tab/accordion/FAQ components (components/**/Accordion*, Tabs*, FAQ*), 'load more' handlers, responsive components using useMediaQuery/isMobile/window.innerWidth to unmount content, WordPress page-builder toggles.
- Rule: Text inside tabs, accordions and 'read more' panels is in the server HTML (it must not be mounted only when open, as in {isOpen && <Panel/>}, or fetched on click) (hidden with CSS/`hidden`/<details> is fine). No main-content component is conditionally unmounted based on viewport or user agent. 'Load more' lists also expose plain <a href> pagination.
- How to test: Repo: read accordion/tab components and check whether panel content is fetched in an onClick/onOpen handler or rendered conditionally ({open && <Panel/>}); grep -rnE "useMediaQuery|isMobile|innerWidth" and check what is unmounted. page_facts.py --rendered: faq.jsonld_questions equals rendered_faq_questions, and hidden_word_count shows text that is in the HTML but collapsed.

### TECH-011: Every indexable page has one unique meta description of 70-160 characters

Severity: medium. Pages: all.

- Why: Engines use the description as a ready-made summary of the page; a specific one improves how the page is described and chosen.
- Where in code: Next.js app router: `metadata` export or `generateMetadata` in app/**/page.tsx and layout.tsx; pages router: next/head in pages/** or _document; Nuxt: useHead/useSeoMeta or nuxt.config app.head; Astro: <head> in src/layouts/*.astro; Remix: `meta` export; WordPress: theme header.php, wp_head hooks, Yoast/Rank Math settings; static: <head> of each .html file.
- Rule: Exactly one <meta name="description"> with non-empty content; 70-160 characters; unique across indexable pages; not copied from the title or a site-wide default.
- How to test: page_facts.py: meta_description per page; duplicate check across the sample. Repo: find the default description in the root layout and check whether page types override it.

### TECH-013: URL variants 301 to one canonical form in a single hop, with no redirect chains or loops

Severity: medium. Pages: all.

- Why: http/https, www/non-www and trailing-slash duplicates spread one page across several addresses; chains slow crawlers and can stop them.
- Where in code: next.config.js redirects() and trailingSlash; middleware.ts; vercel.json/netlify.toml/_redirects; nginx/Apache rewrite rules and .htaccess; WordPress permalink settings and redirect plugins; CDN page rules.
- Rule: http->https, non-preferred host->preferred host, and wrong trailing-slash form each return 301 or 308 directly to the final URL (max 1 hop). No redirect loops. Permanent moves use 301/308, not 302/307. Internal links and sitemap URLs already use the final form (no internal link hits a redirect).
- How to test: HTTP check: curl -sIL on http://, http://www., https://www. and slash/no-slash variants of / and 2 inner URLs, count hops and codes. Repo: read redirect configs for 302/307 used on permanent moves and for rules that chain.

### TECH-017: /llms.txt is served at the root as plain text with no redirect

Severity: medium. Pages: site. AirPulse finding types: missing_llms_txt.

- Why: llms.txt gives AI systems a short, curated map of the site's key pages and facts in one fetch.
- Where in code: public/llms.txt or static/llms.txt; Next.js route handler app/llms.txt/route.ts; WordPress plugin or physical file in the web root; Shopify default llms.txt (often generic).
- Rule: GET /llms.txt returns 200 directly (no 3xx, not 403), Content-Type text/plain or text/markdown, non-empty, not an HTML page. Not disallowed for AI bots in robots.txt.
- How to test: HTTP check: page_facts.py --site llms.txt (status, final_url, content_type, looks_like_html) and agents.md. Repo: look for the file or route.

### TECH-018: llms.txt is curated: H1 name, one-line summary, H2 sections and at least 5 absolute links to the brand's own key pages

Severity: medium. Pages: site. AirPulse finding types: missing_llms_txt, missing_llms_full_txt, missing_agents_md.

- Why: A generic or boilerplate llms.txt (for example a platform default that only advertises the platform) adds nothing an engine can use to describe or cite the brand.
- Where in code: The llms.txt source file or generator (see TECH-017).
- Rule: First line is `# <brand name>`; a `> ` blockquote summary under 200 chars follows; at least one `## ` section; >= 5 Markdown links whose host is the brand's own domain; every link is absolute https and returns 200; each entry has a description after the colon; covers home, about, pricing (if any), top product/service pages and contact. Not a platform-generated default file (looks_like_platform_default). llms-full.txt and agents.md are optional extras and do not fail this check.
- How to test: HTTP check: page_facts.py --site llms.txt (starts_with_h1, has_blockquote_summary, h2_sections, own_domain_links, looks_like_platform_default); request each listed URL.

### TECH-019: <html> has a valid lang attribute that matches the page language

Severity: medium. Pages: all.

- Why: The declared language helps engines match the page to queries in that language and pick the right locale version to cite.
- Where in code: Next.js app/layout.tsx <html lang>; pages/_document.tsx; Nuxt app.head.htmlAttrs; Astro layout <html lang>; WordPress language_attributes() in header.php; static .html files.
- Rule: lang is present on <html>, is a valid BCP 47 code (e.g. en, en-IN, hi), and matches the language of the main content. Multi-locale sites set lang per locale, not one hard-coded value.
- How to test: page_facts.py: lang. Repo: grep -rn "<html" app/ pages/ src/layouts/ and check whether lang is dynamic for i18n routes.

### TECH-020: Multi-locale sites use complete, reciprocal hreflang with x-default and self-canonicals per locale

Severity: medium. Pages: all.

- Why: Broken hreflang makes engines drop locale pairs or cite the wrong country version of a page.
- Where in code: Next.js metadata.alternates.languages (does not add the self entry automatically) or i18n config; next-intl/next-i18next; Nuxt i18n module; WordPress WPML/Polylang; sitemap <xhtml:link> generators.
- Rule: Applies only when hreflang or locale routes exist. Every locale page lists itself plus all alternates; every pair is reciprocal; codes are ISO 639-1 with optional ISO 3166-1 region (en-GB, never en-UK); an x-default entry exists; every target returns 200, is indexable and equals its own canonical; canonical never points to another locale; HTML and sitemap annotations do not conflict; no IP or Accept-Language auto-redirects on content URLs.
- How to test: page_facts.py: hreflang and canonical per locale page; cross-check reciprocity across fetched pages. Repo: read i18n config and middleware for geo/Accept-Language redirects.

### TECH-021: Pages declare a responsive viewport meta tag

Severity: medium. Pages: all.

- Why: Google crawls with a mobile agent only; a page without a responsive viewport is treated as a poor mobile page and its content may be judged unreadable.
- Where in code: Next.js app router sets a default viewport (check for overrides in the `viewport` export); pages/_document.tsx or _app; Nuxt app.head; Astro layouts; WordPress header.php; static <head>.
- Rule: Exactly one <meta name="viewport"> whose content includes width=device-width and initial-scale=1. No fixed pixel width. user-scalable=no / maximum-scale=1 is flagged as an accessibility issue.
- How to test: Raw HTML grep for <meta name="viewport" on each page type; repo grep -rn "viewport".

### TECH-026: Key pages are within 3 clicks of the homepage, no page is orphaned, and link text is descriptive

Severity: medium. Pages: all.

- Why: Crawlers and AI agents find and weigh pages through internal links; buried or unlinked pages are fetched rarely and cited less.
- Where in code: Header/footer navigation components, hub/category templates, related-posts and breadcrumb components, CMS menus, WordPress menus and widgets.
- Rule: Every sitemap URL is reachable from / in <= 3 clicks via <a href> links present in raw HTML. Every indexable page has >= 1 inbound internal link from another page. Anchor text is not generic ('click here', 'read more', 'learn more' alone). Long-form pages link out to related pages. No internal link points to a 3xx or 4xx URL.
- How to test: page_facts.py: internal_links per page; BFS from / over the sample to compute depth; diff the sitemap URL set against the set of linked URLs to find orphans. Repo: read nav/footer components.

### TECH-027: Paginated lists are crawlable through plain links and each page keeps its own canonical

Severity: medium. Pages: category.

- Why: Items that are only reachable through infinite scroll or a JS 'load more' button are never discovered by crawlers.
- Where in code: Blog index, category and product listing templates; pagination components; infinite-scroll hooks; WordPress archive templates.
- Rule: Page 2+ of a listing has a unique URL (/page/2 or ?page=2) linked with <a href> from page 1; page 2+ is not noindexed; each paginated page self-canonicalises. Infinite scroll is backed by these links.
- How to test: page_facts.py on page 1 and page 2: internal_links includes the next-page URL; canonical and robots_meta on page 2. Repo: read pagination and infinite-scroll components.

### AP-001: The site serves robots.txt at the root

Severity: low. Pages: site. AirPulse finding types: missing_robots_txt.

- Why: Confirms an AirPulse audit finding in code before you act on it.
- Where in code: public/robots.txt, app/robots.ts (Next.js), static/robots.txt, WordPress virtual robots (Settings > Reading or SEO plugin), CDN/edge rule.
- Rule: Pass if /robots.txt returns 200 with rules. If the file is live but the audit could not read it, a firewall, bot protection or a www/apex split is the usual cause: report it as already_fixed or false_positive with that reason.
- How to test: Find robots.txt, app/robots.ts or the robots route in the repo. Check with a normal browser user agent: curl -A 'Mozilla/5.0' -s -o /dev/null -w '%{http_code}' <origin>/robots.txt. Compare with the evidence in get_audit_finding. Use TECH-001 for the full test.

### AP-004: Optional: the site serves /llms-full.txt

Severity: low. Pages: site. AirPulse finding types: missing_llms_full_txt.

- Why: Confirms an AirPulse audit finding in code before you act on it.
- Where in code: Same places as llms.txt.
- Rule: Optional. Never a defect when llms.txt is present and complete.
- How to test: Search the repo for llms-full. If it exists, check it is not empty. Compare with the evidence in get_audit_finding.

### AP-005: Optional: /.well-known/ai-plugin.json

Severity: low. Pages: all. AirPulse finding types: missing_ai_plugin_json.

- Why: Confirms an AirPulse audit finding in code before you act on it.
- Where in code: public/.well-known/ai-plugin.json (do not create).
- Rule: Optional and low priority. The major AI search engines do not read this file today, so do not create it as part of this review. Offer to mark the finding acknowledged.
- How to test: No code check. Compare with the evidence in get_audit_finding.

### AP-006: The site sends standard security headers

Severity: low. Pages: home. AirPulse finding types: missing_security_headers.

- Why: Confirms an AirPulse audit finding in code before you act on it.
- Where in code: next.config.js headers(), middleware.ts, vercel.json headers, netlify.toml / _headers, nginx/Apache conf, Cloudflare Transform Rules, WordPress security plugin.
- Rule: Pass if the headers in evidence.detail.missing appear on the live GET response. They may be set at the CDN, not in the repo. Low priority next to content and schema work. Propose a Content-Security-Policy in report-only mode first; never ship a strict one without testing.
- How to test: Search next.config, vercel.json, middleware, _headers, nginx or server config for each header name. Compare curl -sI and curl -s -D - -o /dev/null on the URL. Compare with the evidence in get_audit_finding. Use TECH-028 for the full test.

### TECH-022: Open Graph and Twitter card tags are complete and consistent with the canonical

Severity: low. Pages: all.

- Why: Share cards and many AI tools read og: tags as a clean title, summary and image for the page; mismatched og:url creates a second address for the same page.
- Where in code: Next.js app router: `metadata` export or `generateMetadata` in app/**/page.tsx and layout.tsx; pages router: next/head in pages/** or _document; Nuxt: useHead/useSeoMeta or nuxt.config app.head; Astro: <head> in src/layouts/*.astro; Remix: `meta` export; WordPress: theme header.php, wp_head hooks, Yoast/Rank Math settings; static: <head> of each .html file. Next.js metadata.openGraph / metadata.twitter; Yoast/Rank Math social tab.
- Rule: og:title, og:description, og:type, og:url and og:image are present; og:url equals the canonical; og:image is an absolute https URL that returns 200 (ideally 1200x630); twitter:card is present (summary or summary_large_image). Values are page-specific, not one site-wide set on every page.
- How to test: page_facts.py: og, twitter, canonical. HTTP check: HEAD og:image.

### TECH-025: URLs are clean slugs, and parameter variants do not create duplicate indexable pages

Severity: low. Pages: all.

- Why: Readable, stable URLs are easier for engines to cite and match to a topic; sort, filter and tracking parameters otherwise multiply one page into many.
- Where in code: Route folder names (app/, pages/, src/pages/), CMS slug fields and slugify helpers, WordPress permalink structure, faceted navigation and filter components, link builders that append query strings.
- Rule: Indexable URL paths are lowercase, hyphen-separated, contain no spaces, underscores, session IDs or numeric-only IDs, and do not embed publish dates for evergreen content. Uppercase variants 301 to lowercase. URLs with sort/filter/utm/session parameters either canonicalise to the clean URL or are not linked/indexable.
- How to test: Sitemap and internal_links: regex for [A-Z], _, %20, ?sid=, /\d{4}/\d{2}/, /p/\d+$. page_facts.py: canonical on a parameterised URL equals the clean URL. Repo: read slug generation.

## Schema

### AP-009: JSON-LD on the homepage: Organization OR SoftwareApplication OR LocalBusiness

Severity: high. Pages: home. AirPulse finding types: missing_jsonld_for_homepage.

- Why: Confirms an AirPulse audit finding in code before you act on it.
- Where in code: Next.js app router metadata / layout.tsx <script type=application/ld+json>, pages router <Head>, Astro layouts, WordPress theme or Yoast/RankMath, static HTML <head>; page template for this route.
- Rule: Pass if the page's JSON-LD includes Organization OR SoftwareApplication OR LocalBusiness as a top-level item or a member of @graph. If the page already has it, the audit may predate the fix: report already_fixed. A subtype such as Corporation also describes an Organization; if the finding remains, add Organization to its @type list. The markup must match what the page shows.
- How to test: page_facts jsonld_types on the built page and the live URL, compared with evidence.detail.expected and found. Look in the route or layout that renders the page for 'application/ld+json' and '@type'. Validate with the Schema.org validator before shipping. Compare with the evidence in get_audit_finding.

### AP-010: JSON-LD on pricing pages: Product OR Offer OR SoftwareApplication

Severity: high. Pages: pricing. AirPulse finding types: missing_jsonld_for_pricing.

- Why: Confirms an AirPulse audit finding in code before you act on it.
- Where in code: Next.js app router metadata / layout.tsx <script type=application/ld+json>, pages router <Head>, Astro layouts, WordPress theme or Yoast/RankMath, static HTML <head>; page template for this route.
- Rule: Pass if the page's JSON-LD includes Product OR Offer OR SoftwareApplication as a top-level item or a member of @graph. If the page already has it, the audit may predate the fix: report already_fixed.
- How to test: page_facts jsonld_types on the built page and the live URL, compared with evidence.detail.expected and found. Look in the route or layout that renders the page for 'application/ld+json' and '@type'. Validate with the Schema.org validator before shipping. Compare with the evidence in get_audit_finding.

### AP-014: JSON-LD on product and feature pages: Product OR SoftwareApplication

Severity: high. Pages: product. AirPulse finding types: missing_jsonld_for_product.

- Why: Confirms an AirPulse audit finding in code before you act on it.
- Where in code: Next.js app router metadata / layout.tsx <script type=application/ld+json>, pages router <Head>, Astro layouts, WordPress theme or Yoast/RankMath, static HTML <head>; page template for this route.
- Rule: Pass if the page's JSON-LD includes Product OR SoftwareApplication as a top-level item or a member of @graph. If the page already has it, the audit may predate the fix: report already_fixed.
- How to test: page_facts jsonld_types on the built page and the live URL, compared with evidence.detail.expected and found. Look in the route or layout that renders the page for 'application/ld+json' and '@type'. Validate with the Schema.org validator before shipping. Compare with the evidence in get_audit_finding.

### SCHEMA-001: JSON-LD is in the server HTML, not injected by client JavaScript or a tag manager

Severity: high. Pages: all. AirPulse finding types: missing_jsonld_for_homepage, missing_jsonld_for_blog_post, missing_jsonld_for_pricing, missing_jsonld_for_faq.

- Why: Non-rendering AI crawlers only see structured data that is in the raw response; JS-injected markup is processed late or not at all.
- Where in code: Next.js: <script type="application/ld+json"> rendered in a server component or page (not inside a 'use client' component that mounts later, and not via next/script with afterInteractive/lazyOnload); pages router next/head; Nuxt useHead({ script }); Astro <script type="application/ld+json" set:html>; WordPress Yoast/Rank Math/theme functions.php (wp_head); Google Tag Manager custom HTML tags (anti-pattern).
- Rule: Every JSON-LD block that appears in the rendered DOM also appears in the raw HTML. No JSON-LD is created in useEffect/mounted hooks, next/script with a non-beforeInteractive strategy, or GTM.
- How to test: page_facts.py --rendered: render_only_jsonld_types must be empty. Repo: grep -rn "application/ld+json" and check each hit's component is server-rendered; grep GTM containers/exports for ld+json.

### SCHEMA-002: Every JSON-LD block parses as JSON, uses the schema.org context and is safely escaped

Severity: high. Pages: all.

- Why: A single syntax error makes parsers throw away the whole block, so the page looks like it has no structured data at all.
- Where in code: Schema helper components (JsonLd.tsx, Schema.astro, seo/*.ts), dangerouslySetInnerHTML / set:html / v-html calls that serialise schema objects, hand-written JSON in templates, CMS fields that paste raw schema.
- Rule: jsonld_errors is empty on every page. Each block has "@context": "https://schema.org" (or a @graph under it) and every node has a valid schema.org @type. Serialisation escapes '<' (e.g. JSON.stringify(x).replace(/</g, '\\u003c')) so content containing </script> cannot break the tag. No template placeholders ({{ }}, undefined, null, NaN, empty strings) in required values.
- How to test: page_facts.py: jsonld_errors, jsonld_types. Repo: grep -rnE "ld\+json" and inspect the serialiser; grep rendered HTML for "undefined"|"null" inside ld+json.

### SCHEMA-003: Each page type carries its expected primary schema type

Severity: high. Pages: all. AirPulse finding types: missing_jsonld_for_homepage, missing_jsonld_for_blog_post, missing_jsonld_for_pricing, missing_jsonld_for_faq.

- Why: The page-type schema tells engines what kind of thing the page is (a company, an article, a product, a place); without it the page is just text.
- Where in code: Per-template schema: home/root layout, blog post template, product template, pricing page, FAQ page, about/contact pages, location pages, category/listing templates.
- Rule: Minimum @type set by page type: home = Organization (or subtype) + WebSite; article = Article/BlogPosting/NewsArticle; product = Product; pricing = Product or Offer or SoftwareApplication (with offers); faq = FAQPage; about = AboutPage or Organization; contact = ContactPage or Organization with contactPoint; location = LocalBusiness (or subtype); category = CollectionPage or ItemList; every page except home = BreadcrumbList. Fail when none of the expected types is present (other types may be present).
- How to test: page_facts.py: jsonld_types per sampled page, mapped against the table above; classify page type from route/template.

### SCHEMA-004: Organization schema has name, url, logo and a stable @id

Severity: high. Pages: home, about. AirPulse finding types: incomplete_organization.

- Why: Organization is how engines identify who the brand is; an incomplete node weakens entity matching across pages and other sites.
- Where in code: Root layout or homepage schema component; WordPress Yoast/Rank Math 'Organization' knowledge graph settings; Shopify theme.
- Rule: On the homepage (and about page), an Organization or subtype node has: name (matches the brand name used on the site), url (canonical homepage), logo (absolute URL or ImageObject, returns 200), and @id (e.g. https://<host>/#organization). Recommended and reported: description, contactPoint, address, foundingDate, knowsAbout (3+ topics), sameAs (see SCHEMA-005).
- How to test: page_facts.py: jsonld on home and about; check properties. HTTP check: HEAD the logo URL.

### SCHEMA-007: Article/BlogPosting has headline, image, author, datePublished, dateModified and publisher

Severity: high. Pages: article. AirPulse finding types: missing_jsonld_for_blog_post, missing_author_signal.

- Why: Engines weigh who wrote a piece and how current it is when choosing what to cite; these fields state both explicitly.
- Where in code: Blog/news post template (app/blog/[slug]/page.tsx, src/layouts/BlogPost.astro, single.php), CMS fields for author and dates.
- Rule: Required: headline (matches the H1), image (absolute URL), datePublished, dateModified, description, author (Person with name and url; Organization only for genuinely unsigned content) and publisher (Organization with logo, or an @id reference). mainEntityOfPage or url equals the canonical. The author can be nested in the Article or a separate @graph item referenced by @id; both are valid.
- How to test: page_facts.py on 3+ article pages: jsonld_types, the Article object in jsonld, h1, author_jsonld, canonical.

### SCHEMA-009: Product and pricing pages have Product/SoftwareApplication with offers carrying price, priceCurrency and availability

Severity: high. Pages: product, pricing. AirPulse finding types: missing_jsonld_for_pricing.

- Why: Prices and plans are among the facts AI answers quote most; machine-readable offers reduce wrong or outdated prices in answers.
- Where in code: Product detail template (PDP), pricing page, plan data source (pricing.ts, CMS plan collection, Shopify product JSON).
- Rule: Product pages: Product with name, image, description, brand, sku or gtin/mpn, and offers (Offer or AggregateOffer) with price (number, matches visible price), priceCurrency (ISO 4217, e.g. INR), availability (schema.org URL) and url. Pricing pages for SaaS: SoftwareApplication or Product with offers per plan (name, price, priceCurrency); applicationCategory and operatingSystem for SoftwareApplication. aggregateRating/review only when ratings are visible on the page.
- How to test: page_facts.py on product and pricing pages: jsonld_types and offer fields; compare price with visible price text.

### SCHEMA-012: Location pages use LocalBusiness with full address, telephone, opening hours and geo

Severity: high. Pages: location, contact.

- Why: Local answers ('near me', city queries) rely on exact address and hours; structured NAP data avoids engines guessing or mixing branches.
- Where in code: Location/store/branch templates, contact page, store-locator data files, Google Business Profile sync code.
- Rule: Each physical location page has a LocalBusiness (or specific subtype) node with name, address (PostalAddress: streetAddress, addressLocality, addressRegion, postalCode, addressCountry), telephone, openingHoursSpecification, and geo (latitude, longitude). Values match the visible address/phone on the page and are identical across pages that mention the same branch. parentOrganization references the Organization @id.
- How to test: page_facts.py on location/contact pages: jsonld fields vs visible text.

### SCHEMA-014: Ratings markup only where the page shows real reviews

Severity: high. Pages: all. AirPulse finding types: missing_organization_aggregaterating.

- Why: Markup that claims prices, ratings, dates or authors the reader cannot see is ignored or penalised, and it can make engines repeat false facts.
- Where in code: Wherever schema values are sourced: check they come from the same data object as the visible UI, not a separate hard-coded block.
- Rule: Add AggregateRating only to a Product or SoftwareApplication on a page that shows real third-party review data with its source. Do not mark up ratings for the brand's own Organization from nothing, and never invent values. If the brand has no such reviews, offer to mark the finding acknowledged.
- How to test: page_facts.py: compare jsonld values to title, headings, author, last_modified and visible text. Repo: confirm schema and UI read the same props.

### AP-011: JSON-LD on FAQ pages: FAQPage

Severity: medium. Pages: faq. AirPulse finding types: missing_jsonld_for_faq.

- Why: Confirms an AirPulse audit finding in code before you act on it.
- Where in code: Next.js app router metadata / layout.tsx <script type=application/ld+json>, pages router <Head>, Astro layouts, WordPress theme or Yoast/RankMath, static HTML <head>; page template for this route.
- Rule: Pass if the page's JSON-LD includes FAQPage as a top-level item or a member of @graph. If the page already has it, the audit may predate the fix: report already_fixed.
- How to test: page_facts jsonld_types on the built page and the live URL, compared with evidence.detail.expected and found. Look in the route or layout that renders the page for 'application/ld+json' and '@type'. Validate with the Schema.org validator before shipping. Compare with the evidence in get_audit_finding.

### AP-012: JSON-LD on blog posts: (Article OR BlogPosting OR NewsArticle)

Severity: medium. Pages: article. AirPulse finding types: missing_jsonld_for_blog_post.

- Why: Confirms an AirPulse audit finding in code before you act on it.
- Where in code: Next.js app router metadata / layout.tsx <script type=application/ld+json>, pages router <Head>, Astro layouts, WordPress theme or Yoast/RankMath, static HTML <head>; page template for this route.
- Rule: Pass if the page's JSON-LD includes (Article OR BlogPosting OR NewsArticle) AND Person as a separate top-level item as a top-level item or a member of @graph. If the page already has it, the audit may predate the fix: report already_fixed. The author may be nested in the Article; to satisfy this finding too, also give the Person its own @graph item and reference it from Article.author by @id.
- How to test: page_facts jsonld_types on the built page and the live URL, compared with evidence.detail.expected and found. Look in the route or layout that renders the page for 'application/ld+json' and '@type'. Validate with the Schema.org validator before shipping. Compare with the evidence in get_audit_finding.

### AP-013: JSON-LD on case studies: Article OR CaseStudy

Severity: medium. Pages: article. AirPulse finding types: missing_jsonld_for_case_study_detail.

- Why: Confirms an AirPulse audit finding in code before you act on it.
- Where in code: Next.js app router metadata / layout.tsx <script type=application/ld+json>, pages router <Head>, Astro layouts, WordPress theme or Yoast/RankMath, static HTML <head>; page template for this route.
- Rule: Pass if the page's JSON-LD includes Article OR CaseStudy as a top-level item or a member of @graph. If the page already has it, the audit may predate the fix: report already_fixed.
- How to test: page_facts jsonld_types on the built page and the live URL, compared with evidence.detail.expected and found. Look in the route or layout that renders the page for 'application/ld+json' and '@type'. Validate with the Schema.org validator before shipping. Compare with the evidence in get_audit_finding.

### AP-015: JSON-LD on author pages: Person OR ProfilePage

Severity: medium. Pages: about. AirPulse finding types: missing_jsonld_for_author.

- Why: Confirms an AirPulse audit finding in code before you act on it.
- Where in code: Next.js app router metadata / layout.tsx <script type=application/ld+json>, pages router <Head>, Astro layouts, WordPress theme or Yoast/RankMath, static HTML <head>; page template for this route.
- Rule: Pass if the page's JSON-LD includes Person OR ProfilePage as a top-level item or a member of @graph. If the page already has it, the audit may predate the fix: report already_fixed.
- How to test: page_facts jsonld_types on the built page and the live URL, compared with evidence.detail.expected and found. Look in the route or layout that renders the page for 'application/ld+json' and '@type'. Validate with the Schema.org validator before shipping. Compare with the evidence in get_audit_finding.

### AP-016: Organization JSON-LD links the brand's real profiles with sameAs

Severity: medium. Pages: home. AirPulse finding types: incomplete_organization.

- Why: Confirms an AirPulse audit finding in code before you act on it.
- Where in code: Next.js app router metadata / layout.tsx <script type=application/ld+json>, pages router <Head>, Astro layouts, WordPress theme or Yoast/RankMath, static HTML <head>; global layout Organization block.
- Rule: Pass if sameAs lists the brand's real profiles. Only add a URL the owner confirms exists and belongs to the brand; never add a platform the brand is not on.
- How to test: Search the repo for 'sameAs' and compare with evidence.detail.missing. Footer social links are a good source; open each URL before adding it. Compare with the evidence in get_audit_finding.

### AP-018: Article JSON-LD has author, datePublished, headline and description

Severity: medium. Pages: article. AirPulse finding types: incomplete_article.

- Why: Confirms an AirPulse audit finding in code before you act on it.
- Where in code: Next.js app router metadata / layout.tsx <script type=application/ld+json>, pages router <Head>, Astro layouts, WordPress theme or Yoast/RankMath, static HTML <head>; blog post template / CMS SEO plugin Article schema.
- Rule: Pass if every Article, BlogPosting or NewsArticle item has all four, with real values from the CMS.
- How to test: Inspect the Article object in page_facts jsonld. In the template, check that each property maps to a non-empty CMS field. Compare with the evidence in get_audit_finding.

### SCHEMA-005: Organization (and author Person) sameAs lists the brand's real external profiles

Severity: medium. Pages: home, about. AirPulse finding types: incomplete_organization.

- Why: sameAs ties the site's entity to the same entity on LinkedIn, Wikipedia, Crunchbase and similar, which engines use to confirm who the brand is.
- Where in code: Organization/Person schema source (see SCHEMA-004, SCHEMA-008); site config holding social URLs (siteConfig.ts, footer links).
- Rule: sameAs is an array of absolute https URLs of profiles the brand really has: at least every profile linked in the site footer, and others only when the owner confirms them. Every URL returns 200 or redirects to the same profile; none points to the brand's own domain or another company. WARN under 3 for an established brand; never add a profile that does not exist.
- How to test: page_facts.py: jsonld on home; compare sameAs with external_link_list (footer profile links). HTTP check: HEAD each sameAs URL (some social sites block bots; treat 403/999 as 'unverified', not fail).

### SCHEMA-006: Homepage has a WebSite node with name and url linked to the Organization

Severity: medium. Pages: home. AirPulse finding types: missing_jsonld_for_homepage.

- Why: WebSite names the site itself and connects it to the publisher entity; it is the anchor other nodes reference.
- Where in code: Root layout / homepage schema component; WordPress SEO plugin.
- Rule: One WebSite node on the homepage with name, url (canonical homepage) and publisher (or @id reference) pointing to the Organization @id. potentialAction SearchAction only if the site has a working search URL; its urlTemplate must return results.
- How to test: page_facts.py: jsonld on home. HTTP check: request the SearchAction urlTemplate with a test term if present.

### SCHEMA-010: FAQPage markup only wraps Q&A that is visible on the page, with matching text

Severity: medium. Pages: faq, product, pricing, article. AirPulse finding types: missing_jsonld_for_faq.

- Why: Question-and-answer pairs are easy for engines to lift into answers; markup that differs from the page, or invents questions, is treated as spam.
- Where in code: FAQ section component, FAQ page template, CMS FAQ fields, WordPress FAQ blocks (Yoast/Rank Math FAQ block).
- Rule: When the page shows a visible Q&A list (question headings or <details> items inside main content, not menus), a FAQPage node exists, and every FAQPage has that visible Q&A. mainEntity is an array of Question nodes, each with name and acceptedAnswer (Answer with text). Every Question.name and Answer.text matches the visible question/answer text (whitespace-normalised). Only one FAQPage per URL. Note: Google limits FAQ rich results, so value is for AI parsing, not SERP snippets.
- How to test: page_facts.py: faq (question_headings, details, jsonld_questions, jsonld_answer_words), jsonld FAQ content vs visible text.

### SCHEMA-011: Non-home pages have a BreadcrumbList that mirrors the visible breadcrumb and URL path

Severity: medium. Pages: article, product, category, faq, pricing, about, contact, location.

- Why: Breadcrumbs show where a page sits in the site, which helps engines group pages by topic and give context in citations.
- Where in code: Breadcrumb component and its schema output; layout for nested routes; WordPress SEO plugin breadcrumbs.
- Rule: Every page below the homepage has one BreadcrumbList; itemListElement entries are ListItem with position starting at 1 and increasing by 1, name, and item (absolute URL) for all but the last entry; trail matches the visible breadcrumb (if shown) and the URL hierarchy; each item URL returns 200.
- How to test: page_facts.py: jsonld BreadcrumbList on inner pages; compare with URL path segments and visible breadcrumb links.

### SCHEMA-013: Schema forms one connected graph with no conflicting duplicate entities

Severity: medium. Pages: all. AirPulse finding types: incomplete_organization.

- Why: Two Organization nodes with different names, or a theme and a plugin both emitting schema, give engines contradictory facts about the same brand.
- Where in code: All schema sources together: framework components, SEO plugins (Yoast, Rank Math, AIOSEO), theme functions, Shopify apps, tag manager.
- Rule: Per page, at most one node per entity (one Organization, one WebSite, one main Article/Product). Shared entities use @id and are referenced (publisher, brand, worksFor, isPartOf) rather than re-declared with different values. Organization name, logo and url are identical on every page that includes them. Only one schema source is active per template.
- How to test: page_facts.py: jsonld_types counts per page (flag duplicates) across the sample; compare Organization name/logo/url values across pages. Repo: list every place that emits ld+json and every installed SEO/schema plugin.

### SCHEMA-015: Schema values are well-formed: absolute https URLs and ISO 8601 dates that track real edits

Severity: medium. Pages: all.

- Why: Relative URLs and malformed or build-time dates are dropped or misread, which removes freshness and link signals.
- Where in code: Schema helpers and the data fields they read (CMS publishedAt/updatedAt, siteUrl constant).
- Rule: Every url, @id, image, logo, item and sameAs value is an absolute https URL. datePublished/dateModified are ISO 8601 with time zone (e.g. 2026-10-28T10:00:00+05:30); dateModified >= datePublished; dateModified changes when content changes and is not the build or request time; enumerations use full schema.org URLs (https://schema.org/InStock).
- How to test: page_facts.py: jsonld values (regex for ^https://, ISO 8601), last_modified vs dateModified. Repo: confirm the date source field.

### AP-017: Ratings markup only where the page shows real reviews

Severity: low. Pages: home. AirPulse finding types: missing_organization_aggregaterating.

- Why: Confirms an AirPulse audit finding in code before you act on it.
- Where in code: Organization JSON-LD block (do not edit for this).
- Rule: Add AggregateRating only to a Product or SoftwareApplication on a page that shows real third-party review data with its source. Do not mark up ratings for the brand's own Organization from nothing, and never invent values. If the brand has no such reviews, offer to mark the finding acknowledged.
- How to test: No code change. Compare with the evidence in get_audit_finding.

### AP-019: HowTo markup is optional

Severity: low. Pages: article. AirPulse finding types: deprecated_jsonld_howto.

- Why: Confirms an AirPulse audit finding in code before you act on it.
- Where in code: Next.js app router metadata / layout.tsx <script type=application/ld+json>, pages router <Head>, Astro layouts, WordPress theme or Yoast/RankMath, static HTML <head>.
- Rule: Google no longer shows HowTo rich results, but the markup still describes steps. Do not remove it unless the owner wants to.
- How to test: Search templates for '"HowTo"'. No change required. Compare with the evidence in get_audit_finding.

### SCHEMA-016: Structured data uses JSON-LD and contains no retired types

Severity: low. Pages: all.

- Why: JSON-LD is the format AI and search parsers handle most reliably; retired types add noise and can signal a stale site.
- Where in code: Templates with itemscope/itemprop (Microdata) or typeof/property/vocab (RDFa), legacy theme markup, old plugins.
- Rule: Primary entities are expressed in JSON-LD. Microdata/RDFa-only pages fail; mixed formats are flagged. No SpecialAnnouncement nodes. HowTo and FAQPage are allowed but are not expected to earn Google rich results. VideoObject contentUrl, when present, points to a video file, not the page URL.
- How to test: Raw HTML grep for itemscope|itemtype|typeof=|vocab=; page_facts.py: jsonld_types for SpecialAnnouncement.

## Content

### CONTENT-001: Homepage and About page say who the brand is and what it does in the first paragraph

Severity: high. Pages: home, about. AirPulse finding types: no_answer_in_hero.

- Why: Engines need an unambiguous entity statement to resolve the brand name to a category; without it they guess, or confuse it with a namesake.
- Where in code: Body copy: Next.js app/**/page.tsx or pages/*.tsx plus the components they render, and MDX/Markdown under content/ or posts/; Astro src/pages and src/content collections; WordPress post_content, single.php/page.php, template-parts and ACF fields; Shopify sections/*.liquid and templates/*.json; Webflow/static HTML exports. Homepage hero + first content section; About page intro. Also the <title> and meta description in the layout/metadata export.
- Rule: Within the first 60 words after the H1 (page_facts first_60_words) on the homepage and About page there must be one sentence containing the exact brand name, a category noun ('is a payroll platform', 'is a Mumbai real-estate developer') and the audience or location served. FAIL if the brand name is only in the logo image, or the first paragraph is a tagline with no category noun.
- How to test: page_facts.py title, meta_description, headings, first_60_words, first_paragraph; check that brand string appears as text (not only <img alt>) and matches /<Brand>\s+(is|helps|builds|makes|offers)\b/.

### CONTENT-005: No important text lives only inside images (pricing tables, spec sheets, infographics, banner headlines)

Severity: high. Pages: all.

- Why: Engines read HTML text; words baked into an image are lost, and alt text is not a substitute for a table or a paragraph.
- Where in code: Body copy: Next.js app/**/page.tsx or pages/*.tsx plus the components they render, and MDX/Markdown under content/ or posts/; Astro src/pages and src/content collections; WordPress post_content, single.php/page.php, template-parts and ACF fields; Shopify sections/*.liquid and templates/*.json; Webflow/static HTML exports. Static image folders (public/, assets/, wp-content/uploads) and hero/banner components.
- Rule: FAIL if an <img>/<picture>/CSS background carries text that is not repeated in HTML near it: price lists, comparison charts, spec tables, infographics, certificates, review screenshots, or the hero headline. Signals: filename or alt containing pricing|price|table|chart|infographic|specs|comparison|review|testimonial, or alt over 125 characters. Each such image needs an HTML <table>/<p> equivalent on the page.
- How to test: page_facts.py images (src, alt) and img_without_alt; grep filenames/alt with /pric|table|chart|infographic|spec|compar|review|testimonial/i and check for a nearby <table> or matching text.

### CONTENT-007: No two substantive pages are near-duplicates (5-word shingle Jaccard below 0.85)

Severity: high. Pages: all. AirPulse finding types: duplicate_content.

- Why: Near-duplicate pages split citations and make engines pick one at random, or neither.
- Where in code: Templated routes (Next.js dynamic segments [city], [service]; Astro getStaticPaths; WordPress custom post types; Shopify product variants as separate URLs) and any CMS copy-paste pages.
- Rule: For every pair of indexable pages with >=200 main-content words, Jaccard similarity on 5-word shingles must be below 0.85. Treat 0.80-0.85 as WARN. Pages above the threshold need a canonical to one URL, a merge, or distinct content.
- How to test: Run page_facts.py on all pages in one call: the final 'duplicates' line lists pairs at 0.80 or more (5-word shingles, pages of 200+ words). Check canonical and hreflang on each flagged pair.

### CONTENT-008: Programmatic pages from one template differ by more than swapped variables

Severity: high. Pages: location, article, category, product. AirPulse finding types: duplicate_content.

- Why: City-name or product-name swaps are thin content; engines and Google treat them as doorway pages and cite neither.
- Where in code: Template file plus its data source: Next.js generateStaticParams + data JSON/CMS; Astro content collections; WordPress page builders with shortcodes; Airtable/CSV-fed pages.
- Rule: Pick 3 pages built from the same template. After removing the shared template text (header, footer, CTA blocks, repeated paragraphs), each page must keep >=40% of its main-content words unique to it and include at least one page-specific data block (local prices, regulations, inventory, specs, integration steps, testimonials from that segment). Also FAIL if the template text is identical with only {city}/{product} tokens changed.
- How to test: Repo: open the template and list which fields come from data vs hard-coded strings. HTML: diff main text of 3 sibling pages; compute share of sentences that appear on only one page.

### CONTENT-010: Product pages state what the product is, who it is for, key specs in a table or <dl>, price as text, and an FAQ

Severity: high. Pages: product.

- Why: Product questions in AI answers are built from specs, price and fit; pages missing these get replaced by marketplaces and review sites.
- Where in code: Product template: Shopify sections/main-product.liquid + metafields; WooCommerce single-product.php; Next.js app/products/[slug]/page.tsx; headless commerce product components.
- Rule: PASS if the product page has: (1) a first-paragraph sentence naming the product and its category and use, (2) >=5 specs in a <table> or <dl> (dimensions, materials, compatibility, limits), (3) price and currency as text (TRUST-001), (4) availability/stock text, (5) >=3 FAQ items, (6) >=300 main-content words. FAIL if description is only manufacturer boilerplate shared across products (CONTENT-007).
- How to test: page_facts.py tables, lists, faq (question_headings, details, jsonld_answer_words), word_count; regex for currency; grep the template for spec/metafield rendering into <table>/<dl>.

### CONTENT-011: Pricing page lists every plan with numeric price, currency, billing period, limits and inclusions as text

Severity: high. Pages: pricing.

- Why: AI buying agents skip vendors whose prices they cannot read; 'contact sales' only or JS-toggled prices are filtered out of comparisons.
- Where in code: Pricing route (app/pricing/page.tsx, pages/pricing.astro, page-pricing.php) and plan data (plans.ts/json, CMS pricing collection). Monthly/annual toggles are a common source of JS-only prices.
- Rule: PASS if each plan shows: name, numeric price with currency symbol/code, billing period (per month/year/user), key limits (seats, usage, quotas) and included features, all in server HTML; both monthly and annual prices exist in HTML even if one is visually hidden; a 'prices as of' or last-updated date is shown. Enterprise-only 'contact us' is fine only if other tiers have numbers. Bonus: /pricing.md or /pricing.txt exists and matches the page.
- How to test: Raw HTML regex for currency+number near each plan name; check toggle components render both price sets; HTTP GET /pricing.md and /pricing.txt.

### CONTENT-012: Location pages carry real local facts: full address, phone, hours, service area and location-specific detail

Severity: high. Pages: location.

- Why: Local AI answers are assembled from name-address-phone facts plus local specifics; a city-swapped page gives none.
- Where in code: Location template (app/locations/[city]/page.tsx, Astro getStaticPaths, WordPress location CPT, store-locator data JSON).
- Rule: PASS if the page shows as HTML text: business name, street address with postcode, phone, opening hours, area served, and >=2 location-specific facts (local prices, team members, nearby landmarks, local regulations, project list). Map embeds must be accompanied by the address in text. FAIL if address/hours are only in an iframe, image, or JS store locator.
- How to test: Regex for phone and postcode patterns in raw HTML; check for <address> or text block; diff against a sibling location page for CONTENT-008.

### TECH-023: One H1 per page and a heading outline with no skipped levels

Severity: high. Pages: all.

- Why: Engines split pages into passages by heading; a clear H1 and H2/H3 outline lets them lift a self-contained answer and know what it is about.
- Where in code: Page templates and layout components: hero/banner components that render the H1, logo wrapped in <h1> in the header, CMS rich-text renderers, components that use headings for styling.
- Rule: h1_count == 1 on every indexable page, in raw HTML, with non-empty text that names the page topic (not the logo or 'Welcome'). Heading levels never jump down by more than one (no H1 -> H3, no H2 -> H4). Headings are real <h1>-<h6> elements, not styled <div>s; heading tags are not used for non-heading UI text (prices, badges).
- How to test: page_facts.py: h1_count, headings (ordered list of level + text); check for level jumps. Repo: grep -rn "<h1" components/ to find a site-wide header H1.

### AP-008: The homepage has enough text in the server HTML

Severity: medium. Pages: home. AirPulse finding types: thin_homepage_content.

- Why: Confirms an AirPulse audit finding in code before you act on it.
- Where in code: Homepage hero/sections component, CMS homepage entry.
- Rule: Pass if the server HTML of the homepage has at least about 120 words (800 characters) of visible text. Adding copy is the owner's decision: propose an outline, do not write marketing claims.
- How to test: page_facts word_count on the homepage. Compare with the evidence in get_audit_finding. Use TECH-007 and CONTENT-002 for the full test.

### AP-025: Pages do not repeat each other's content

Severity: medium. Pages: all. AirPulse finding types: duplicate_content.

- Why: Confirms an AirPulse audit finding in code before you act on it.
- Where in code: Route definitions, CMS duplicates, locale/paginated variants, <link rel=canonical>.
- Rule: The finding names two URLs (page_url and evidence.detail.url_b). Fine when they are deliberate language or region variants with correct canonical or hreflang. Never delete, redirect or canonicalize pages yourself: propose it to the owner.
- How to test: page_facts canonical and hreflang on both URLs; compare the two bodies. Compare with the evidence in get_audit_finding. Use CONTENT-007 for the full test.

### CONTENT-002: Pages meet word-count floors for their type

Severity: medium. Pages: all. AirPulse finding types: thin_homepage_content.

- Why: Thin pages give engines too little to quote or to trust; the floors are minimums, not targets.
- Where in code: Body copy: Next.js app/**/page.tsx or pages/*.tsx plus the components they render, and MDX/Markdown under content/ or posts/; Astro src/pages and src/content collections; WordPress post_content, single.php/page.php, template-parts and ACF fields; Shopify sections/*.liquid and templates/*.json; Webflow/static HTML exports.
- Rule: Main-content words (exclude nav/footer/boilerplate) must meet: home 500, blog post 1,500, pillar guide 2,000, product 300, service 500, about 300, FAQ page 500. Homepage also needs >=800 characters of visible body text in the raw (pre-JS) HTML. WARN for location, comparison and category pages under 300 words. Do not flag pages above the floor for being short of the 'ideal' range.
- How to test: page_facts.py word_count per page, bucketed by page type; for the homepage, word_count of the server HTML (about 120 words is 800 characters); compare main_word_count to exclude navigation.

### CONTENT-006: Key documents linked as PDFs also exist as HTML pages

Severity: medium. Pages: all.

- Why: Gated or PDF-only content is weak for most engines, even though Perplexity does read public PDFs; an HTML version gets both.
- Where in code: Links to .pdf in nav, footer, product and resource templates; WordPress media library; /public/*.pdf in Next.js/Astro.
- Rule: For every PDF linked from a core page (brochure, price list, menu, spec sheet, whitepaper, rate card, policy), an HTML page with the same core content must exist and be linked. PDFs behind a form (lead gate) FAIL unless an ungated HTML summary exists. Keep the PDF public too (do not remove it).
- How to test: page_facts.py internal_links filtered on /\.pdf($|\?)/i; for each, search the sitemap/routes for an HTML page with a matching title.

### CONTENT-013: Comparison and alternatives pages have a criteria table, a 'best for' verdict per option, and a visible review date

Severity: medium. Pages: article.

- Why: Engines cite comparisons that are structured and even-handed; one-sided pages without dates get skipped or contradicted.
- Where in code: Compare/vs/alternatives templates (/compare/[a]-vs-[b], /alternatives/[x]) and their data files.
- Rule: PASS if the page has: a <table> with >=5 criteria rows including price and a 'best for' row, a short verdict per option naming who should pick it, at least one stated strength of each competitor, and a visible 'last reviewed' date. FAIL if the competitor column contains only negatives or blanks, or prices have no date.
- How to test: page_facts.py tables (row count, header text), headings; regex for 'best for' and a date near the table.

### AP-024: Posts avoid stock filler phrases

Severity: low. Pages: article. AirPulse finding types: ai_content_pattern_density.

- Why: Confirms an AirPulse audit finding in code before you act on it.
- Where in code: CMS content.
- Rule: A writing-quality signal, not a code defect. Short posts can trip it with a few transitions. Point out the phrases; editing copy is the owner's call.
- How to test: Search the post body for filler such as 'in conclusion', 'moreover', 'furthermore', 'delve into'. Compare with the evidence in get_audit_finding. Use CONTENT-009 for the full test.

### CONTENT-009: Filler and template-AI phrases stay under 6 per 1,000 words

Severity: low. Pages: article. AirPulse finding types: ai_content_pattern_density.

- Why: Generic phrasing signals low effort and adds words with no facts, which lowers both trust and extractability.
- Where in code: Body copy: Next.js app/**/page.tsx or pages/*.tsx plus the components they render, and MDX/Markdown under content/ or posts/; Astro src/pages and src/content collections; WordPress post_content, single.php/page.php, template-parts and ACF fields; Shopify sections/*.liquid and templates/*.json; Webflow/static HTML exports.
- Rule: On pages with >=400 words, count phrases such as 'in conclusion,', 'moreover,', 'furthermore,', "it's worth noting that", "in today's fast-paced", 'in the digital age', 'delve into', 'navigate the complexities', 'leverage the power of', 'in the realm of'. FAIL at >=6 per 1,000 words. This is a surface heuristic, not an AI detector.
- How to test: page_facts.py filler_phrases and filler_per_1k (pages of 400+ words).

## Citability

### CITE-001: Page opens with a direct answer to its main query in the first 60 words of main content

Severity: high. Pages: home, article, product, pricing, location, faq. AirPulse finding types: no_answer_in_hero.

- Why: Engines quote the opening of a page most often; a lead that states what the page answers gives them a ready sentence to lift.
- Where in code: Body copy: Next.js app/**/page.tsx or pages/*.tsx plus the components they render, and MDX/Markdown under content/ or posts/; Astro src/pages and src/content collections; WordPress post_content, single.php/page.php, template-parts and ACF fields; Shopify sections/*.liquid and templates/*.json; Webflow/static HTML exports. Hero/intro components (Hero.tsx, hero.liquid, the first block in the CMS page builder) are where this usually fails.
- Rule: Take the first 60 words of visible main content (exclude nav, header, cookie banners, breadcrumbs). PASS if they contain a declarative sentence that names the page subject and states what it is, costs, does or answers (e.g. 'X is a ..', 'X costs ..', 'To do X, ..'). FAIL if they are only a slogan, a question, a CTA, or filler such as 'Welcome to', 'In this article', 'Have you ever wondered'.
- How to test: page_facts.py headings + main text: slice the first 60 words after the H1. Repo: open the hero/intro component and the CMS field it renders. Grep the first paragraph for /^(Welcome|In this (article|post|guide)|Have you ever|Are you looking)/i.

### CITE-002: Each question-shaped H2/H3 is followed by a 40-60 word direct answer before any elaboration

Severity: high. Pages: article, faq, product, pricing, home. AirPulse finding types: content_buried_answer.

- Why: Answer engines match a sub-question to a heading and then take the first sentences under it; if the answer is buried, a competitor's page gets quoted instead.
- Where in code: Body copy: Next.js app/**/page.tsx or pages/*.tsx plus the components they render, and MDX/Markdown under content/ or posts/; Astro src/pages and src/content collections; WordPress post_content, single.php/page.php, template-parts and ACF fields; Shopify sections/*.liquid and templates/*.json; Webflow/static HTML exports. In CMS-driven sites, check the rich-text renderer and any 'section' component that wraps H2 + body.
- Rule: For every H2/H3 that is phrased as a question, the first <p> (or first <li> group) after it must answer the question in its first 1-2 sentences, with the answer complete within 60 words. FAIL if the first paragraph restates the question, gives background, or the answer first appears after 60 words. Also FAIL the page if its main answer first appears after word 600 of main content.
- How to test: page_facts.py headings: for each question heading, read the next sibling text node(s); count words to the first sentence that contains the heading's key noun plus a verb of state (is/are/costs/takes/means/requires) or a number.

### CITE-009: Comparisons of 3+ items or attributes are real <table> elements with a <th> header row

Severity: high. Pages: article, pricing, product.

- Why: Engines lift table rows with high accuracy; the same data laid out in div grids, cards or images is much harder to parse.
- Where in code: Body copy: Next.js app/**/page.tsx or pages/*.tsx plus the components they render, and MDX/Markdown under content/ or posts/; Astro src/pages and src/content collections; WordPress post_content, single.php/page.php, template-parts and ACF fields; Shopify sections/*.liquid and templates/*.json; Webflow/static HTML exports. Pricing/compare components (PricingTable.tsx, ComparisonGrid, Elementor/Webflow grid widgets) often render div grids instead of tables.
- Rule: Comparison, pricing and spec pages: PASS if comparison data is in a <table> with <thead>/<th> column headers and a first-column row label. FAIL if the comparison is built with CSS grid/flex divs, is an <img>, or is split across cards with no table. Articles that compare 3+ named options must contain at least one <table>.
- How to test: page_facts.py tables (count and header presence). Repo grep for comparison components and check they output <table>, <th>; flag className~=/grid|compare|pricing-card/ wrappers with no <table>.

### CITE-003: Informational pages use at least 3 H2/H3 headings phrased the way people ask

Severity: medium. Pages: article, faq, product, pricing, location.

- Why: Question-form headings line up with the prompts users type into ChatGPT or Perplexity and with Google's fan-out sub-queries.
- Where in code: Body copy: Next.js app/**/page.tsx or pages/*.tsx plus the components they render, and MDX/Markdown under content/ or posts/; Astro src/pages and src/content collections; WordPress post_content, single.php/page.php, template-parts and ACF fields; Shopify sections/*.liquid and templates/*.json; Webflow/static HTML exports.
- Rule: Count H2/H3 headings that end in '?' or begin with what, how, why, when, where, which, who, can, does, is, are, should. Articles and FAQ pages: PASS at >=3, full credit at >=5. Product, pricing and location pages: PASS at >=2 (usually inside the FAQ block).
- How to test: page_facts.py headings (filter levels 2-3) and a regex /\?$|^(what|how|why|when|where|which|who|can|does|is|are|should)\b/i.

### CITE-004: Pages about a term, product or category contain an explicit 'X is a/an ...' definition sentence

Severity: medium. Pages: article, product, home, category, about. AirPulse finding types: low_citability.

- Why: Definition sentences are the easiest thing for a model to quote verbatim for 'what is X' prompts.
- Where in code: Body copy: Next.js app/**/page.tsx or pages/*.tsx plus the components they render, and MDX/Markdown under content/ or posts/; Astro src/pages and src/content collections; WordPress post_content, single.php/page.php, template-parts and ACF fields; Shopify sections/*.liquid and templates/*.json; Webflow/static HTML exports. Glossary/learn templates (/glossary/[term], /learn/[slug]) and product/category intro fields.
- Rule: PASS if the main content contains at least one sentence matching '<Subject> is a|an|the ..', '<Subject> refers to ..', or '<Subject> (is )?defined as ..' where <Subject> is the H1 topic or brand/product name, and it appears in the first 150 words. Glossary pages FAIL without it in the first sentence.
- How to test: Regex over main text: /\b[A-Z][\w-]+(?:\s+[A-Z][\w-]*)*\s+(is (a|an|the)|refers? to|(is )?defined as)\b/ and confirm the subject matches the H1 noun.

### CITE-005: Section openings name their subject instead of leaning on pronouns or connectives

Severity: medium. Pages: article, faq, product, home. AirPulse finding types: low_citability.

- Why: A passage lifted out of the page must still make sense; one that starts with 'It' or 'However' loses its subject when quoted alone.
- Where in code: Body copy: Next.js app/**/page.tsx or pages/*.tsx plus the components they render, and MDX/Markdown under content/ or posts/; Astro src/pages and src/content collections; WordPress post_content, single.php/page.php, template-parts and ACF fields; Shopify sections/*.liquid and templates/*.json; Webflow/static HTML exports.
- Rule: For each H2/H3 section, take the first sentence. FAIL the section if it starts with It, This, That, These, Those, They, He, She, But, However, And, So, Also. FAIL the page if more than 20% of sections fail. Secondary: pronoun ratio (it/they/them/their/this/that/these/those/he/she/his/her per word) per section should be below 0.04.
- How to test: page_facts.py sections[].first_sentence and sections[].pronoun_led (it applies the regex /^(It|This|That|These|Those|They|He|She|But|However|And|So|Also)\b/); read pronoun_ratio per section and pronoun_led_section_ratio for the page.

### CITE-006: Sections are citable blocks: 1+ block of 134-167 words, none over 400 words, paragraphs of 2-4 sentences

Severity: medium. Pages: article, faq. AirPulse finding types: low_citability.

- Why: Long unbroken sections are hard to excerpt and very short ones lack context; the AirPulse audit rewards blocks in the 134-167 word band.
- Where in code: Body copy: Next.js app/**/page.tsx or pages/*.tsx plus the components they render, and MDX/Markdown under content/ or posts/; Astro src/pages and src/content collections; WordPress post_content, single.php/page.php, template-parts and ACF fields; Shopify sections/*.liquid and templates/*.json; Webflow/static HTML exports.
- Rule: Segment main content at H2/H3. PASS if >=1 block has 134-167 words and no block exceeds 400 words. WARN if every block is under 30 words (fragmented). Note: apply 40-60 words to the opening answer (CITE-002) and 134-167 to the whole block. Paragraph rule: FAIL any <p> with more than 5 sentences or more than 120 words; WARN if average sentence length is outside 10-25 words.
- How to test: page_facts.py headings + text per section; read sections[].words, answer_blocks_134_167 and max_section_words (sections under 20 words are not scored). long_paragraphs lists <p> elements over 120 words or 5 sentences.

### CITE-007: Claims use specific numbers: at least 1 statistic per 500 words, target 3+

Severity: medium. Pages: article, product, home, pricing. AirPulse finding types: low_citability.

- Why: Engines prefer passages with exact figures they can attribute; vague quantifiers give them nothing to quote.
- Where in code: Body copy: Next.js app/**/page.tsx or pages/*.tsx plus the components they render, and MDX/Markdown under content/ or posts/; Astro src/pages and src/content collections; WordPress post_content, single.php/page.php, template-parts and ACF fields; Shopify sections/*.liquid and templates/*.json; Webflow/static HTML exports.
- Rule: Count statistics in main content: percentages, currency amounts, counts with a unit (users, customers, days, km, etc.), dated figures. PASS at >=1 per 500 words; full credit at >=3 per 500 words. Independently FAIL any sentence that uses 'studies show', 'experts agree', 'many', 'most', 'a lot of', 'significant' as the only support for a claim with no number or named source in the same sentence.
- How to test: Regex over main text: /\d+(\.\d+)?\s*%/, /[$€£₹]\s?[\d,]+/, /\b\d[\d,]*\s+(users|customers|people|companies|days|hours|months|years|times)\b/i; vague-phrase regex /\b(studies show|research shows|experts (say|agree))\b/i without a link or capitalised source name in the sentence.

### CITE-008: Every third-party statistic and quote names its source in the same sentence or links to it

Severity: medium. Pages: article.

- Why: Attributed figures and named-expert quotes are the two largest content-side lifts in published GEO research (Aggarwal et al., 2023).
- Where in code: Body copy: Next.js app/**/page.tsx or pages/*.tsx plus the components they render, and MDX/Markdown under content/ or posts/; Astro src/pages and src/content collections; WordPress post_content, single.php/page.php, template-parts and ACF fields; Shopify sections/*.liquid and templates/*.json; Webflow/static HTML exports. Look for a <Quote>/<Blockquote>/<Stat> component and whether it has source/author props.
- Rule: For each statistic not about the site's own business, the same sentence or paragraph must contain 'according to <Name>', a capitalised organisation/study name with year, or an <a href> to the source. For each <blockquote> or quoted sentence, the person's name and role/organisation must be present. PASS if >=80% of third-party stats and 100% of quotes are attributed.
- How to test: For each stat matched in CITE-007, inspect its parent <p>/<li> for an external_links entry or /according to|per |\(\w+ \d{4}\)/; for each <blockquote>, require a <cite>, <figcaption> or adjacent name + title.

### CITE-010: Step-by-step processes use an ordered list (<ol>) with at least 3 steps written as text

Severity: medium. Pages: article, faq, product.

- Why: 'How to' prompts are answered with numbered steps; an <ol> gives engines the order without guessing.
- Where in code: Body copy: Next.js app/**/page.tsx or pages/*.tsx plus the components they render, and MDX/Markdown under content/ or posts/; Astro src/pages and src/content collections; WordPress post_content, single.php/page.php, template-parts and ACF fields; Shopify sections/*.liquid and templates/*.json; Webflow/static HTML exports. Docs/how-to templates and any Steps/Timeline component.
- Rule: Pages or sections whose heading starts with 'How to' or contains 'steps' MUST contain an <ol> with >=3 <li>, each starting with an action verb. FAIL if steps are numbered by hand inside <p> or <div>, shown only as images, or only inside a video. How-to/help pages additionally need a prerequisites list, an expected-outcome sentence, a time or effort estimate, screenshots with descriptive alt (not 'screenshot', 'image1'), and code in <pre><code>, not images.
- How to test: page_facts.py lists (type=ordered, item counts) cross-checked with headings matching /how to|steps?/i.

### CITE-011: FAQ block has 5+ real questions with 50-100 word answers, visible in the HTML

Severity: medium. Pages: faq, product, pricing, location, home. AirPulse finding types: faq_schema_missing.

- Why: FAQ blocks map one-to-one onto conversational prompts; Perplexity in particular cites pages with Q&A content more often.
- Where in code: Body copy: Next.js app/**/page.tsx or pages/*.tsx plus the components they render, and MDX/Markdown under content/ or posts/; Astro src/pages and src/content collections; WordPress post_content, single.php/page.php, template-parts and ACF fields; Shopify sections/*.liquid and templates/*.json; Webflow/static HTML exports. FAQ/Accordion components, WordPress FAQ blocks (Yoast/RankMath), Shopify FAQ sections, CMS 'faq' collections.
- Rule: FAQ pages and the FAQ section on product, pricing, service and location pages: PASS if >=5 questions, each a heading, <summary> or <dt> ending in '?', each answer 50-100 words whose first sentence answers directly. All answers must be present in the initial HTML (see CONTENT-003). If FAQPage JSON-LD exists, its question/answer text must match the visible text.
- How to test: page_facts.py faq (question_headings, details, jsonld_answer_words) (count, answer word counts) and jsonld_types; compare JSON-LD mainEntity[].acceptedAnswer.text with visible answer text.

### CITE-012: Pages that claim original insight show it: first-party data with sample size, date range and method

Severity: medium. Pages: article. AirPulse finding types: low_citability.

- Why: Original data is what makes a page the necessary citation; engines favour primary sources over pages that summarise others.
- Where in code: Body copy: Next.js app/**/page.tsx or pages/*.tsx plus the components they render, and MDX/Markdown under content/ or posts/; Astro src/pages and src/content collections; WordPress post_content, single.php/page.php, template-parts and ACF fields; Shopify sections/*.liquid and templates/*.json; Webflow/static HTML exports. Research/report/case-study templates and their data components (charts should also have HTML data tables).
- Rule: Research, report, benchmark and case-study pages: PASS if the text contains a first-party marker ('our data', 'we surveyed', 'we analysed', 'our customers') together with a number N, a date range, and a short method paragraph. Charts must have the underlying numbers in HTML text or a <table>, not only in an image or canvas.
- How to test: Regex /\bour (research|study|data|analysis|survey|report)\b|\bwe (found|surveyed|analy[sz]ed|measured)\b/i (same patterns as the AirPulse scorer); check for N=/sample/respondents and a <table> near any <img>/<canvas> chart.

### CITE-013: Blog and case-study pages have quotable sections (citability_score 40 or more)

Severity: medium. Pages: article. AirPulse finding types: low_citability.

- Why: A quick editor's guide to which sections are easy for an engine to quote.
- Where in code: Body copy: Next.js app/**/page.tsx or pages/*.tsx plus the components they render, and MDX/Markdown under content/ or posts/; Astro src/pages and src/content collections; WordPress post_content, single.php/page.php, template-parts and ACF fields; Shopify sections/*.liquid and templates/*.json; Webflow/static HTML exports.
- Rule: page_facts.py citability_score is a rough 0-100 guide built from section length, a definition sentence, specific figures, first-hand research and sentence count. PASS at 40 or more. Below 40, point to the weakest long sections. It is a guide for editors, not a ranking factor: never rewrite content only to raise it.
- How to test: page_facts.py citability_score and sections[].score. Read the lowest-scoring long sections to suggest edits.

### AP-020: Articles contain passages an AI engine can quote

Severity: low. Pages: article. AirPulse finding types: low_citability.

- Why: Confirms an AirPulse audit finding in code before you act on it.
- Where in code: CMS content (markdown/MDX/WordPress post body), not template code.
- Rule: Look for a direct answer near the top, a one-sentence definition, specific facts with sources, and passages that make sense on their own. This is a content judgement: suggest edits, never rewrite posts automatically. Does not apply to listing pages.
- How to test: Read the post body; see the CITE and CONTENT checks for concrete tests. Compare with the evidence in get_audit_finding. Use CITE-006 and CITE-013 for the full test.

## Expertise and authorship (E-E-A-T)

### EEAT-001: Every article shows a visible author byline with a one-line credential, linked to an author page

Severity: high. Pages: article. AirPulse finding types: author_byline_missing, missing_author_signal.

- Why: Named, linked authors are a basic expertise signal; unattributed content is one of the formats engines under-cite.
- Where in code: Article/post template: Next.js app/blog/[slug]/page.tsx or a PostLayout component; Astro src/layouts/BlogPost.astro; WordPress single.php / template-parts/content-single.php; Ghost post.hbs; Hugo layouts/_default/single.html; frontmatter in .md/.mdx. Author fields: frontmatter author, WordPress post_author / get_the_author_meta, CMS author reference.
- Rule: PASS if the article template renders the author's name as text near the H1 or the article end, wrapped in a link to a dedicated author URL on the same domain. FAIL if there is no byline, the byline is a generic 'Admin', 'Team', 'Staff' or the brand name, or the name is not linked. The byline must also show the author's role or qualification as text (e.g. 'Priya Shah, CA, Head of Tax'), not only on hover or on the author page.
- How to test: page_facts.py author_visible, author_jsonld and internal_link_list; regex for /^(admin|team|staff|editor)$/i. Repo: confirm the template outputs the author component on all post types. Sample 3+ posts, not the blog index.

### EEAT-003: Health, finance and legal pages show a named reviewer with a credential, a review date and a disclaimer

Severity: high. Pages: article, product, faq.

- Why: On high-stakes topics engines lean hardest on verified expertise; an expert reviewer line is the clearest on-page proof.
- Where in code: Article/post template: Next.js app/blog/[slug]/page.tsx or a PostLayout component; Astro src/layouts/BlogPost.astro; WordPress single.php / template-parts/content-single.php; Ghost post.hbs; Hugo layouts/_default/single.html; frontmatter in .md/.mdx. Look for reviewedBy / medicalReviewer fields in the CMS schema.
- Rule: For pages about medical, financial, investment, tax, insurance, legal or safety topics: PASS if the page shows 'Reviewed by <Name>, <credential>' with a review date, links the reviewer to a profile, and shows a disclaimer that the content is informational (and, for legal, the jurisdiction). FAIL if any of the three is missing.
- How to test: Classify the page by keywords in title/headings; regex /reviewed by|medically reviewed|fact[- ]checked by/i and a date within 50 words; regex /not (financial|medical|legal) advice|for informational purposes/i.

### AP-022: Articles name their author in a way crawlers can read

Severity: medium. Pages: article. AirPulse finding types: missing_author_signal.

- Why: Confirms an AirPulse audit finding in code before you act on it.
- Where in code: Post template <head> (meta name=author, article:author), byline component, CMS author field.
- Rule: Pass if the page has a visible byline, Article.author in JSON-LD, and <meta name="author">. Add the meta tag when the byline and JSON-LD already exist; it is a one-line template fix.
- How to test: page_facts author_meta and the jsonld author. Search the template for name="author", article:author and '"author"'. Compare with the evidence in get_audit_finding. Use EEAT-001 for the full test.

### EEAT-002: Author pages give role, relevant credentials, a bio of 50+ words, a photo, external profile links and the author's articles

Severity: medium. Pages: author, article. AirPulse finding types: missing_author_signal.

- Why: Engines judge expertise from the author page; a name with nothing behind it does not count as an expert.
- Where in code: Author archive/template: Next.js app/authors/[slug]/page.tsx; Astro authors collection; WordPress author.php; Ghost author.hbs. Use a Person with name, url, jobTitle, image and sameAs.
- Rule: Each author URL must return 200 and show: full name, job title, credentials or experience relevant to the topics they write on (degrees, certifications, years in role), a bio of >=50 words, a photo, >=1 external profile link (LinkedIn, professional registry, GitHub), and a list of their articles. FAIL if the author link 404s or points to a generic team page.
- How to test: Follow author links from EEAT-001; fetch each; page_facts.py word_count, external_links; check Person JSON-LD for jobTitle and sameAs.

### EEAT-004: Articles cite primary sources with outbound links, and those links resolve

Severity: medium. Pages: article. AirPulse finding types: broken_link.

- Why: Linking to the original study, regulator or standard shows the claim can be checked; published GEO research (Aggarwal et al., 2023) found cited sources among the strongest content signals.
- Where in code: Body copy: Next.js app/**/page.tsx or pages/*.tsx plus the components they render, and MDX/Markdown under content/ or posts/; Astro src/pages and src/content collections; WordPress post_content, single.php/page.php, template-parts and ACF fields; Shopify sections/*.liquid and templates/*.json; Webflow/static HTML exports. Rich-text link rendering (check rel attributes and that links are not stripped by the sanitiser).
- Rule: Articles over 1,000 words: PASS if they contain >=3 outbound links to primary sources (government, regulator, standards body, peer-reviewed or original research, official product docs) that are not competitors. Every outbound citation must return 2xx/3xx. FAIL if all outbound links go to aggregators or are nofollow-sponsored only.
- How to test: page_facts.py external_links (host list); classify hosts (.gov, .gov.in, .edu, .ac.*, who.int, regulator domains, doi.org); HEAD each link and flag 4xx/5xx.

### EEAT-005: Experience is shown with first-hand detail and original images, not stock photos

Severity: medium. Pages: article, product.

- Why: Engines increasingly separate pages written by people who did the thing from pages that summarise others; original evidence is the tell.
- Where in code: Body copy: Next.js app/**/page.tsx or pages/*.tsx plus the components they render, and MDX/Markdown under content/ or posts/; Astro src/pages and src/content collections; WordPress post_content, single.php/page.php, template-parts and ACF fields; Shopify sections/*.liquid and templates/*.json; Webflow/static HTML exports. Image sources in content and the media library.
- Rule: Review, case-study and how-to pages: PASS if the text contains first-person specifics ('we tested', 'we installed', 'our team measured') tied to a number, date or named product, and at least one original image or screenshot. FAIL if all images come from stock hosts (unsplash, pexels, shutterstock, istockphoto, gettyimages, freepik) or have stock-style filenames, and there is no first-person detail.
- How to test: Regex first-person patterns over main text; page_facts.py images src hosts/filenames matched against stock hosts list.

### EEAT-006: 'Best X' and ranking pages explain how items were selected and tested

Severity: medium. Pages: article.

- Why: Rankings without a method look like ads; engines treat them as low-trust and often recommend competitors from them instead.
- Where in code: Body copy: Next.js app/**/page.tsx or pages/*.tsx plus the components they render, and MDX/Markdown under content/ or posts/; Astro src/pages and src/content collections; WordPress post_content, single.php/page.php, template-parts and ACF fields; Shopify sections/*.liquid and templates/*.json; Webflow/static HTML exports. Listicle/curation templates.
- Rule: Pages whose H1 contains best|top|vs|alternatives|review: PASS if there is a 'How we chose' / 'Methodology' section of >=50 words naming the criteria, the testing done, the date of the review, and any commercial relationship with listed brands. FAIL if absent.
- How to test: page_facts.py headings regex /how we (chose|tested|picked|rank)|methodolog/i plus word count of that section; date check per FRESH-001.

### SCHEMA-008: Article authors are Person nodes with a profile URL on the site, and that author page carries Person schema

Severity: medium. Pages: article, author. AirPulse finding types: missing_author_signal.

- Why: A named, linkable author with credentials is a strong trust signal; a bare name string gives engines nothing to verify.
- Where in code: Author data model (CMS author collection, WordPress users), author byline component, author archive template (/authors/[slug], author.php).
- Rule: Article.author is a Person (not a plain string) with name and url pointing to an on-site author page that returns 200. The author page has Person schema with name, url and at least jobTitle or sameAs (LinkedIn etc.); worksFor references the Organization @id. Recommended: knowsAbout, description, image.
- How to test: page_facts.py: author_visible, author_jsonld and jsonld on article pages; follow author url; page_facts.py on the author page for Person.

### AP-023: Articles expose a publish date crawlers can read

Severity: low. Pages: article. AirPulse finding types: missing_date_signal.

- Why: Confirms an AirPulse audit finding in code before you act on it.
- Where in code: Post template <head> meta article:published_time, <time datetime>, Article JSON-LD datePublished/dateModified.
- Rule: Pass if the page has a visible date, datePublished in JSON-LD, and <meta property="article:published_time">. Add the meta tag from the same CMS field if it is missing.
- How to test: page_facts published_meta, time_datetimes, dates_in_text. Search the template for article:published_time, datePublished and <time. Compare with the evidence in get_audit_finding. Use FRESH-001 for the full test.

### AP-027: Brand facts match across pages

Severity: low. Pages: all. AirPulse finding types: cross_page_contradiction.

- Why: Confirms an AirPulse audit finding in code before you act on it.
- Where in code: Copy constants, CMS entries, pricing components, about page.
- Rule: Act only if both quoted claims (evidence.detail.page_a_claim and page_b_claim) appear on their pages as written. Otherwise mark false_positive with the owner's approval. The owner decides which value is right.
- How to test: Search the repo, content and live pages for each exact claim. Compare with the evidence in get_audit_finding. Use TRUST-006 for the full test.

### EEAT-007: Out of scope for code review: off-site authority signals

Severity: low. Pages: all. AirPulse finding types: no_wikipedia, missing_wikidata_entity, review_site_sparse.

- Why: Wikipedia/Wikidata entries, Reddit and forum mentions, review-site profiles, backlinks and press coverage drive recommendations but cannot be verified from the site's code.
- Where in code: Not in the repo. The only on-site part is sameAs links in Organization/Person JSON-LD, covered by the schema checks.
- Rule: Do not score backlinks, Wikipedia or Wikidata entries, Reddit and forum mentions, review sites or press here. The AirPulse GEO audit reports these as authority findings (AP checks). The only in-repo link is SCHEMA-005: sameAs should point to the profiles that exist.
- How to test: None in this skill.

## Trust

### TRUST-001: Prices and fees appear as HTML text with currency and unit wherever the site sells something

Severity: high. Pages: pricing, product, home, location.

- Why: Price questions are among the most common commercial prompts; prices in images, behind 'request a quote' or only after a click cannot be quoted.
- Where in code: Price components (Price.tsx, price.liquid, woocommerce_get_price_html), pricing data files, fee tables on service pages.
- Rule: If the business publishes prices or fees, they must be in the raw HTML as text with a currency symbol or ISO code and a unit (per month, per sq ft, per session). FAIL if prices are images, rendered only after location/variant selection by JS, behind login, or shown only as 'starting from' with no number. 'Price on request' is acceptable only where the industry norm makes it so; flag as a gap, not a failure, on pricing and product pages.
- How to test: Raw HTML regex /([$€£₹]|INR|USD|EUR|GBP|Rs\.?)\s?\d[\d,]*(\.\d+)?/ on pricing, product and service pages; compare with rendered DOM to detect JS-only prices.

### TRUST-002: An About page exists, is linked from header or footer, and states founding year, leadership names, location and what the company does

Severity: high. Pages: about, home.

- Why: Engines ground the brand entity from the About page; company facts there are what models repeat when asked who the brand is.
- Where in code: Site chrome: Next.js app/layout.tsx and Header/Footer components; Astro src/layouts/BaseLayout.astro; WordPress header.php/footer.php and registered nav menus; Shopify sections/header.liquid and footer.liquid. About route (/about, /about-us, /company, /team, /our-story).
- Rule: PASS if an About page is reachable from every page via header or footer and contains: a one-sentence description with category noun, founding year, named founders or leaders with roles, headquarters city/country, and >=300 words. Before failing, try /about, /about-us, /company, /who-we-are, /our-story, /team, /leadership. Sites with >=20 articles must also have an editorial standards page (review/fact-check process and how to report errors) linked from About or the article footer.
- How to test: page_facts.py internal_link_list on 3 sample pages for an about-type URL; fetch it; regex for a 4-digit founding year and person names with titles; word_count.

### TECH-028: Site is HTTPS-only with no mixed content and sends core security headers

Severity: medium. Pages: all. AirPulse finding types: missing_security_headers.

- Why: Engines and AI products prefer to cite secure, trustworthy sources; http URLs in canonicals or sitemaps also create duplicate addresses.
- Where in code: next.config.js headers(), middleware.ts, vercel.json/netlify.toml/_headers, nginx/Apache config, Cloudflare settings, WordPress security plugins; hard-coded http:// asset URLs in templates and CMS content.
- Rule: All canonical, sitemap, og and internal link URLs are https. No http:// script, style, image or iframe src on https pages. Responses include Strict-Transport-Security (max-age >= 31536000), X-Content-Type-Options: nosniff, X-Frame-Options (DENY/SAMEORIGIN) or CSP frame-ancestors, and Referrer-Policy; Content-Security-Policy and Permissions-Policy are reported as advisories.
- How to test: HTTP check: curl -sI on / and 2 inner pages for the headers. Repo: grep -rn "http://" in templates/components (excluding xmlns and schema.org context) and read header config.

### TRUST-003: Contact details (email plus phone or address) and privacy/terms pages are visible as text and linked from every footer

Severity: medium. Pages: all.

- Why: Reachable publishers are treated as more trustworthy.
- Where in code: Site chrome: Next.js app/layout.tsx and Header/Footer components; Astro src/layouts/BaseLayout.astro; WordPress header.php/footer.php and registered nav menus; Shopify sections/header.liquid and footer.liquid. Contact route and any contact form component.
- Rule: PASS if a contact page is linked from the footer and shows an email address and at least one of phone or postal address as plain text (not only a form, not an image). Local businesses must show full address and phone on every page footer or location page. Every template's footer must also link a privacy policy and terms page that return 200 with >=300 words each (not PDF-only).
- How to test: Fetch contact page; regex email /[\w.+-]+@[\w-]+\.[\w.]+/, phone, postcode; check footer links on 3 pages.

### TRUST-004: Affiliate and sponsored links are disclosed in visible text and marked rel="sponsored"

Severity: medium. Pages: article.

- Why: Undisclosed commercial links undercut trust in the whole page.
- Where in code: Body copy: Next.js app/**/page.tsx or pages/*.tsx plus the components they render, and MDX/Markdown under content/ or posts/; Astro src/pages and src/content collections; WordPress post_content, single.php/page.php, template-parts and ACF fields; Shopify sections/*.liquid and templates/*.json; Webflow/static HTML exports. Affiliate link helpers/shortcodes (ThirstyAffiliates, Pretty Links, custom <AffiliateLink>).
- Rule: If a page contains affiliate or paid links (tracking params like tag=, aff=, ref=, utm_medium=affiliate, or known affiliate hosts), PASS only if a disclosure sentence appears above the first such link and each link has rel containing 'sponsored' (or 'nofollow').
- How to test: page_facts.py external_links with href params and rel attributes; regex for /affiliate|commission|sponsored|paid partnership/i before the first affiliate link.

### TRUST-005: Testimonials and case studies are text with a named person, company and a measurable result

Severity: medium. Pages: home, product, about.

- Why: Specific, attributable proof is quotable; logo walls and review screenshots are not.
- Where in code: Testimonial/Case-study components and CMS collections; review widgets (Trustpilot, Yotpo, Judge.me) and how they render.
- Rule: PASS if each testimonial shows person name, role or company, and the quote as HTML text, and case studies state a before/after or numeric outcome with timeframe. FAIL if proof is only logos, screenshots of reviews, or a third-party widget that renders client-side (see CONTENT-004).
- How to test: Locate testimonial blocks in rendered HTML; confirm quote text exists in raw HTML; regex for a number+% or currency in case-study pages.

### TRUST-006: Core company and product facts are identical across every page that states them

Severity: medium. Pages: all. AirPulse finding types: cross_page_contradiction.

- Why: When pages disagree on founding year, customer count, location or price, engines either pick one at random or distrust both.
- Where in code: Hard-coded strings in components and copy files (constants.ts, i18n JSON, CMS fields). Best practice is one source of truth (site config) referenced everywhere.
- Rule: Extract every occurrence of: founding year, headquarters, customer/user counts, number of locations, years of experience, flagship price, contact phone. FAIL if any fact has more than one value across pages (excluding clearly dated historical statements).
- How to test: Repo grep for /founded|since \d{4}|established|customers|clients|users|offices|years of experience/i across content and component files; HTML: same regexes across sampled pages; compare values.

### TRUST-007: B2B security/trust page renders its content in HTML, not only inside a JS trust-centre widget

Severity: medium. Pages: about, home.

- Why: Buyers ask AI assistants about SOC 2, ISO 27001 and data handling; a trust vault that renders nothing for crawlers answers nothing.
- Where in code: Security/trust route (/security, /trust, /compliance) or subdomain (trust.*, security.*); embedded SafeBase/Vanta/Drata widgets.
- Rule: For B2B/SaaS sites: PASS if a security or trust page exists and its raw HTML names the certifications/frameworks held (e.g. SOC 2 Type II, ISO 27001, GDPR, DPDP), data-hosting region and a contact for security issues. FAIL if the page or subdomain renders an empty shell without JS.
- How to test: Try /security, /trust, /trust-center, /compliance and trust./security. subdomains; curl raw HTML and grep /SOC ?2|ISO ?27001|GDPR|DPDP|HIPAA|PCI/i.

### AP-026: Outgoing links resolve

Severity: low. Pages: all. AirPulse finding types: broken_link.

- Why: Confirms an AirPulse audit finding in code before you act on it.
- Where in code: Post bodies (CMS), nav/footer components, MDX files.
- Rule: Here page_url is the broken link itself, not the page that contains it. Some sites refuse automated checks (403, 429, 999): confirm with a browser user agent before calling a link broken. Replace only with a URL the owner approves.
- How to test: Search the repo and content for the URL to find where it is used. Check with a normal browser user agent: curl -A 'Mozilla/5.0' -s -o /dev/null -w '%{http_code}' <url>. Compare with the evidence in get_audit_finding.

## Freshness

### FRESH-001: Articles show a visible, specific published date in a <time datetime> element

Severity: high. Pages: article. AirPulse finding types: missing_date_signal.

- Why: Undated pages lose to dated ones for anything time-sensitive, and engines cannot tell how current an undated claim is.
- Where in code: Article/post template: Next.js app/blog/[slug]/page.tsx or a PostLayout component; Astro src/layouts/BlogPost.astro; WordPress single.php / template-parts/content-single.php; Ghost post.hbs; Hugo layouts/_default/single.html; frontmatter in .md/.mdx. Date fields: frontmatter date/pubDate, WordPress get_the_date, CMS publishedAt.
- Rule: PASS if the article shows a full date (day, month, year, e.g. '15 January 2026') near the title, wrapped in <time datetime="YYYY-MM-DD..">. FAIL if no date, only a relative date ('3 days ago') with no absolute date in HTML, or month/year only.
- How to test: Rendered HTML: <time> elements and their datetime attributes; page_facts.py last_modified and JSON-LD datePublished for comparison.

### FRESH-003: Dates come from real content data, not from the build time or the current request time

Severity: high. Pages: all. AirPulse finding types: sitemap_stale.

- Why: Templates that stamp today's date on every page make every page look fresh and none of it believable; engines and Google discount fake freshness.
- Where in code: Date rendering in templates and JSON-LD builders: new Date(), Date.now(), dayjs(), moment() without an argument, PHP date('Y-m-d') / current_time(), Liquid 'now', Hugo now, build-time env vars like BUILD_DATE.
- Rule: FAIL if any visible 'updated' date, dateModified, article:modified_time or sitemap lastmod is produced from the current time or build time instead of a stored per-page field (CMS updatedAt, frontmatter updated, git last-commit date for that file). Copyright-year footers are exempt.
- How to test: Repo grep: /new Date\(\)|Date\.now\(\)|dayjs\(\)|moment\(\)|date\(['\"]Y-m-d|current_time\(|\{\{\s*['\"]now['\"]|\.Now\b/ inside files that render dates, JSON-LD or sitemaps. HTML: fetch two different old articles; FAIL if both show today's date.

### FRESH-002: Updated pages show 'Last updated' and every date source agrees

Severity: medium. Pages: article, pricing. AirPulse finding types: last_updated_missing, article_schema_missing_date_modified, incomplete_article.

- Why: A visible update date that matches the markup is a trusted freshness signal; mismatched dates look manipulated.
- Where in code: Article/post template: Next.js app/blog/[slug]/page.tsx or a PostLayout component; Astro src/layouts/BlogPost.astro; WordPress single.php / template-parts/content-single.php; Ghost post.hbs; Hugo layouts/_default/single.html; frontmatter in .md/.mdx. Also the metadata export (article:modified_time), JSON-LD builder, and sitemap generator (next-sitemap, @astrojs/sitemap, Yoast).
- Rule: If content changed after publication, the page shows 'Last updated <full date>'. The visible updated date, JSON-LD dateModified, meta article:modified_time and the sitemap <lastmod> must be the same calendar day (allow +/-1 day for timezone). dateModified must be >= datePublished. FAIL if dateModified is missing from Article JSON-LD on dated articles.
- How to test: page_facts.py last_modified, jsonld_date_published, jsonld_date_modified, modified_meta, dates_in_text; fetch sitemap.xml lastmod for the URL; compare.

### FRESH-004: Time-sensitive pages were updated within 12 months; competitive commercial pages within 6

Severity: medium. Pages: article, pricing. AirPulse finding types: stale_content.

- Why: Engines weight recency; stale pricing, comparisons and statistics get replaced by newer sources.
- Where in code: Content data (dateModified / updatedAt fields) rather than code.
- Rule: Using dateModified (else datePublished): pricing, comparison, 'best X' and statistics-heavy pages FAIL if older than 6 months. Other articles and case studies older than 365 days are a WARN: list them for the owner to review; evergreen pages can be fine as they are. CRITICAL if a pricing or comparison page has no date at all. Never change a date without a real content update.
- How to test: page_facts.py jsonld dates or last_modified; compute age from audit date; classify page type from URL/template.

### TECH-016: Every sitemap URL has a <lastmod> taken from the content's real update date

Severity: medium. Pages: site.

- Why: lastmod tells crawlers what changed and when; a build-time timestamp on every URL teaches them to ignore it, so updated pages get re-read late.
- Where in code: Sitemap generator (see TECH-015): the field mapped to lastModified/lastmod (CMS updatedAt, file mtime, git commit date vs new Date()).
- Rule: 100% of <url> entries have <lastmod> in W3C datetime format (YYYY-MM-DD or full ISO 8601). Fail if lastmod is set from the build/request time (all entries share the same timestamp, or generator uses new Date()/now()). lastmod for article pages matches the page's dateModified (see SCHEMA-007). Optional: an IndexNow key file and ping-on-publish hook for faster Bing/ChatGPT pickup.
- How to test: HTTP check: parse sitemap, count entries with lastmod and the number of distinct values. Repo: grep the generator for lastModified|lastmod and confirm the source field.

### AP-021: Older articles show an honest last-updated date after a real review

Severity: low. Pages: article. AirPulse finding types: stale_content.

- Why: Confirms an AirPulse audit finding in code before you act on it.
- Where in code: Post template date component; meta article:published_time / article:modified_time; Article JSON-LD dateModified.
- Rule: Applies to articles more than a year old. Evergreen or archive posts can be fine as they are. Never change a date without a real content update.
- How to test: page_facts published_meta, modified_meta, time_datetimes. In the template, check article:published_time, article:modified_time and dateModified. Compare with the evidence in get_audit_finding. Use FRESH-004 for the full test.

### FRESH-005: No stale year in titles or headings, and no 'currently/latest/this year' claims without a date

Severity: low. Pages: article, pricing. AirPulse finding types: stale_content.

- Why: 'Best tools 2024' in late 2026 tells the engine the page is out of date before it reads a word.
- Where in code: Title/H1 fields in CMS and metadata exports; hard-coded years in templates.
- Rule: FAIL if the <title>, H1 or any H2 contains a year earlier than the current year on a page that is not explicitly historical. FAIL if main content uses 'currently', 'as of now', 'this year', 'the latest', 'recently' in a factual claim without an absolute date within the same paragraph.
- How to test: page_facts.py title + headings regex /\b20\d{2}\b/ and compare to the current year; main-text regex /\b(currently|as of now|this year|the latest|recently)\b/i and check the paragraph for a date.

## Accessibility

### TECH-024: Every content image has descriptive alt text; decorative images use alt=""

Severity: medium. Pages: all.

- Why: Alt text is the only description of an image a text-reading crawler gets, and it often carries product or chart facts.
- Where in code: Image components (next/image requires alt; check for alt="" or alt={undefined} on content images), CMS image fields mapped to alt, markdown renderers, WordPress media library alt field.
- Rule: img_without_alt == 0 for content images (product, article, chart, team photos). Alt text is not the file name, not 'image'/'photo', and under ~125 characters. Purely decorative images (icons, dividers) use alt="" or are CSS backgrounds.
- How to test: page_facts.py: img_without_alt per page. Repo: grep -rnE "<img(?![^>]*alt=)|alt=\{?['\"]{2}" in components and check the CMS schema has an alt field that templates actually use.

## Authority

### AP-028: Off-site, not a code fix: the brand has an English Wikipedia article

Severity: low. Pages: all. AirPulse finding types: missing_wikipedia_article.

- Why: Confirms an AirPulse audit finding in code before you act on it.
- Where in code: Not in code.
- Rule: Not a code change. If the repo links to the brand's profile (footer, sameAs) under a different URL, the profile exists: tell the owner to add it to the AirPulse brand profile and offer to mark the finding false_positive. Never create accounts or articles.
- How to test: evidence.detail.probe_url shows the URL that was checked. Search the repo for the platform's domain to find the real profile URL. Compare with the evidence in get_audit_finding.

### AP-029: Off-site, not a code fix: the brand has a Wikidata entity

Severity: low. Pages: all. AirPulse finding types: missing_wikidata_entity.

- Why: Confirms an AirPulse audit finding in code before you act on it.
- Where in code: Not in code.
- Rule: Not a code change. If the repo links to the brand's profile (footer, sameAs) under a different URL, the profile exists: tell the owner to add it to the AirPulse brand profile and offer to mark the finding false_positive. Never create accounts or articles.
- How to test: evidence.detail.probe_url shows the URL that was checked. Search the repo for the platform's domain to find the real profile URL. Compare with the evidence in get_audit_finding.

### AP-030: Off-site, not a code fix: the brand has Wikidata links to its profiles

Severity: low. Pages: all. AirPulse finding types: incomplete_wikidata_sameas.

- Why: Confirms an AirPulse audit finding in code before you act on it.
- Where in code: Not in code.
- Rule: Not a code change. If the repo links to the brand's profile (footer, sameAs) under a different URL, the profile exists: tell the owner to add it to the AirPulse brand profile and offer to mark the finding false_positive. Never create accounts or articles.
- How to test: evidence.detail.probe_url shows the URL that was checked. Search the repo for the platform's domain to find the real profile URL. Compare with the evidence in get_audit_finding.

### AP-031: Press coverage the brand has received is named in text

Severity: low. Pages: home, about. AirPulse finding types: no_press_mentions_surfaced.

- Why: Confirms an AirPulse audit finding in code before you act on it.
- Where in code: Not in code.
- Rule: Pass if the about, press or home page names real coverage in text (logos alone may not be read). Only add links the owner supplies.
- How to test: Search the repo for outlet names, /press routes and logo alt text. Compare with the evidence in get_audit_finding.

### AP-032: Off-site, not a code fix: the brand has a LinkedIn company page

Severity: low. Pages: all. AirPulse finding types: missing_linkedin_company.

- Why: Confirms an AirPulse audit finding in code before you act on it.
- Where in code: Not in code.
- Rule: Not a code change. If the repo links to the brand's profile (footer, sameAs) under a different URL, the profile exists: tell the owner to add it to the AirPulse brand profile and offer to mark the finding false_positive. Never create accounts or articles.
- How to test: evidence.detail.probe_url shows the URL that was checked. Search the repo for the platform's domain to find the real profile URL. Compare with the evidence in get_audit_finding.

### AP-033: Off-site, not a code fix: the brand has a YouTube channel

Severity: low. Pages: all. AirPulse finding types: missing_youtube_channel.

- Why: Confirms an AirPulse audit finding in code before you act on it.
- Where in code: Not in code.
- Rule: Not a code change. If the repo links to the brand's profile (footer, sameAs) under a different URL, the profile exists: tell the owner to add it to the AirPulse brand profile and offer to mark the finding false_positive. Never create accounts or articles.
- How to test: evidence.detail.probe_url shows the URL that was checked. Search the repo for the platform's domain to find the real profile URL. Compare with the evidence in get_audit_finding.

### AP-034: Off-site, not a code fix: the brand has a GitHub organization

Severity: low. Pages: all. AirPulse finding types: missing_github_org.

- Why: Confirms an AirPulse audit finding in code before you act on it.
- Where in code: Not in code.
- Rule: Not a code change. If the repo links to the brand's profile (footer, sameAs) under a different URL, the profile exists: tell the owner to add it to the AirPulse brand profile and offer to mark the finding false_positive. Never create accounts or articles.
- How to test: evidence.detail.probe_url shows the URL that was checked. Search the repo for the platform's domain to find the real profile URL. Compare with the evidence in get_audit_finding.

### AP-035: Off-site, not a code fix: the brand has a Crunchbase profile

Severity: low. Pages: all. AirPulse finding types: missing_crunchbase_profile.

- Why: Confirms an AirPulse audit finding in code before you act on it.
- Where in code: Not in code.
- Rule: Not a code change. If the repo links to the brand's profile (footer, sameAs) under a different URL, the profile exists: tell the owner to add it to the AirPulse brand profile and offer to mark the finding false_positive. Never create accounts or articles.
- How to test: evidence.detail.probe_url shows the URL that was checked. Search the repo for the platform's domain to find the real profile URL. Compare with the evidence in get_audit_finding.

### AP-036: Off-site, not a code fix: the brand has a G2 listing

Severity: low. Pages: all. AirPulse finding types: missing_g2_listing.

- Why: Confirms an AirPulse audit finding in code before you act on it.
- Where in code: Not in code.
- Rule: Not a code change. If the repo links to the brand's profile (footer, sameAs) under a different URL, the profile exists: tell the owner to add it to the AirPulse brand profile and offer to mark the finding false_positive. Never create accounts or articles.
- How to test: evidence.detail.probe_url shows the URL that was checked. Search the repo for the platform's domain to find the real profile URL. Compare with the evidence in get_audit_finding.

### AP-037: Off-site, not a code fix: the brand has a Trustpilot profile

Severity: low. Pages: all. AirPulse finding types: missing_trustpilot_profile.

- Why: Confirms an AirPulse audit finding in code before you act on it.
- Where in code: Not in code.
- Rule: Not a code change. If the repo links to the brand's profile (footer, sameAs) under a different URL, the profile exists: tell the owner to add it to the AirPulse brand profile and offer to mark the finding false_positive. Never create accounts or articles.
- How to test: evidence.detail.probe_url shows the URL that was checked. Search the repo for the platform's domain to find the real profile URL. Compare with the evidence in get_audit_finding.
