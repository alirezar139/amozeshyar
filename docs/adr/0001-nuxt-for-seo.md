# ADR 0001: Nuxt (SSR) instead of a plain Vue SPA

## Status
Accepted

## Context
The product requirement explicitly calls for strong SEO on the public course and instructor marketing pages — these pages are the platform's advertising surface for instructors, so search visibility and social-share link previews matter commercially, not just as a technical nicety. A client-only Vue SPA renders an empty `<div id="app">` to crawlers that don't execute JavaScript and produces no usable Open Graph metadata for link previews.

## Decision
Use Nuxt (currently 3.21.x) instead of a bare Vue + Vite SPA. Nuxt is still Vue underneath — no framework switch, just an SSR-capable meta-framework — and its `routeRules` let us mix rendering strategies per route:
- Public marketing/catalog pages: prerendered or SWR (server-rendered, crawlable, fast).
- Authenticated dashboard/instructor-panel: `ssr: false` (pure SPA), since SEO doesn't apply there and skipping SSR keeps them cheap to serve.

## Consequences
- Slightly more operational surface than a static SPA (a Node server process, or prerendering step).
- Full access to `useSeoMeta`, JSON-LD injection, and the `@nuxtjs/sitemap`/`@nuxtjs/robots` modules used to satisfy the SEO requirement.
