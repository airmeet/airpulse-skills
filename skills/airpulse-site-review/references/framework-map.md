# Where page metadata and content live, by framework

Use this to map a page URL from an AirPulse finding to the file that produces it. Detect the framework from the repo first (`package.json` dependencies, config files), then look in the places below. When a fix lives in a CMS or plugin setting instead of code, say so and do not edit code for it.

| Framework | How to detect | Title, description, canonical, robots | JSON-LD | robots.txt, sitemap, llms.txt | Built HTML to scan |
|---|---|---|---|---|---|
| Next.js, App Router | `next` dep, `app/` folder | `export const metadata` or `generateMetadata()` in `app/**/page.tsx` and `layout.tsx` (`alternates.canonical`, `robots`) | `<script type="application/ld+json">` rendered in the page or layout component | `app/robots.ts`, `app/sitemap.ts`, or files in `public/`; `public/llms.txt` | `.next/server/app/**/*.html` for static routes, or `next build && next start` then fetch |
| Next.js, Pages Router | `next` dep, `pages/` folder | `<Head>` from `next/head`, or `next-seo` (`<NextSeo>`, `DefaultSeo` in `_app`) | `<Head>` script tag or `next-seo` JSON-LD components | `public/robots.txt`, `next-sitemap.config.js`, `pages/sitemap.xml.ts` | `out/` after `next export`, or run and fetch |
| Astro | `astro` dep | `<head>` in `src/layouts/*.astro`, props passed from `src/pages/**` | inline `<script type="application/ld+json" set:html=...>` | `public/`, `@astrojs/sitemap` in `astro.config.*` | `dist/` |
| Nuxt | `nuxt` dep | `useHead()` / `useSeoMeta()` in pages, `app.head` in `nuxt.config` | `useHead({ script: [{ type: 'application/ld+json' ... }] })`, `nuxt-schema-org` | `public/`, `@nuxtjs/sitemap`, `nuxt-simple-robots` | `.output/public/` after `nuxi generate` |
| SvelteKit | `@sveltejs/kit` dep | `<svelte:head>` in `+page.svelte` / `+layout.svelte` | `{@html}` JSON-LD inside `<svelte:head>` | `static/`, `src/routes/sitemap.xml/+server.ts` | `build/` with adapter-static |
| Remix / React Router 7 | `@remix-run/*` or `react-router` v7 | `export const meta` in route modules | rendered in route component or `meta` (`"script:ld+json"`) | `public/`, resource routes | run and fetch |
| Gatsby | `gatsby` dep | `export const Head` in pages/templates, `gatsby-plugin-react-helmet` | inside `Head` / Helmet | `static/`, `gatsby-plugin-sitemap` | `public/` |
| Vite / CRA single-page app | `vite` or `react-scripts`, one `index.html` | `index.html`, `react-helmet(-async)` | Helmet | `public/` | `dist/` or `build/`. Warning: bots that do not run JavaScript only see `index.html`. Check with `looks_client_rendered`. |
| Hugo | `hugo.toml` / `config.toml` | `layouts/partials/head.html`, front matter | partial templates | `static/`, `layouts/robots.txt`, built-in sitemap | `public/` |
| Jekyll | `_config.yml` | `_includes/head.html`, `jekyll-seo-tag` | includes | root files, `jekyll-sitemap` | `_site/` |
| WordPress theme | `style.css` theme header, `functions.php` | `header.php`, `wp_head` hooks; usually Yoast / Rank Math settings, not code | plugin settings or `functions.php` filters | plugin or `robots_txt` filter; `llms.txt` via plugin or file in web root | fetch live or staging URLs |
| Shopify theme | `layout/theme.liquid`, `sections/` | `theme.liquid` `<head>`, `snippets/meta-tags.liquid` | `snippets/*schema*.liquid`, product/article templates | `templates/robots.txt.liquid`; sitemap is automatic | fetch live or preview URLs |
| Webflow, Wix, Framer, Squarespace | no code repo | page settings in the builder | custom code embed | builder settings | fetch live URLs; fixes are instructions, not diffs |
| Plain HTML | `.html` files only | each file's `<head>` | inline | root files | the repo itself |

## Matching a URL to a file

1. Strip the origin and query string. Map `/` to the index route.
2. Look for a static route first (`app/pricing/page.tsx`, `src/pages/pricing.astro`), then dynamic routes (`app/blog/[slug]/page.tsx`). For a dynamic route the fix usually goes in the shared template, not the content entry, unless the problem is the content itself.
3. If the content comes from a CMS (MDX folder, Contentful, Sanity, Strapi, WordPress API), name the content entry and the template separately in the report.
4. If you cannot find the file, record the finding as `could_not_map` and move on. Do not guess.
