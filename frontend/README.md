# Frontend (Nuxt 3 / Vue.js)

## Rendering strategy

Defined per route group in `nuxt.config.ts` -> `routeRules`:

- `/` — prerendered at build time
- `/courses/**`, `/instructors/**` — SWR (stale-while-revalidate), so public/marketing pages stay crawlable and fast without a full rebuild per content change
- `/dashboard/**`, `/instructor-panel/**` — pure SPA (`ssr: false`), since these are authenticated, non-indexed screens

## Structure

```
pages/              # file-based routing
components/
├── ui/               # design-system primitives
├── course/, instructor/, player/, layout/
composables/         # useApi (auth-aware fetch wrapper), useAuth
stores/              # Pinia (auth, cart, player)
middleware/          # auth.global.ts route guard
layouts/             # default (public), dashboard, instructor
```

Note: files live at the project root (`pages/`, `components/`, ...), not under an `app/` subdirectory — this project pins Nuxt 3 (not 4), whose default convention doesn't use the `app/` srcDir.

## Local development

```bash
cp .env.example .env
npm install
npm run dev
```

## Language

Persian only for now (RTL, `Vazirmatn` font). An earlier attempt at bilingual (fa/en) support via `@nuxtjs/i18n` was reverted — the module version compatible with our Nuxt 3.21/unhead v2 stack turned out not to exist (every `@nuxtjs/i18n` release past 8.5.6 requires `unhead@^3`, which Nuxt 3 doesn't ship), and 8.5.6 itself called a `unhead` v1-only API that crashed the whole app at runtime. Revisit this once the ecosystem lines up, or via a lighter hand-rolled approach if bilingual support is needed sooner.

## Auth

The access token lives only in the Pinia `auth` store (memory, not `localStorage`) to limit XSS blast radius; the refresh token is an httpOnly cookie the browser sends automatically. `useApi()` retries once through `/auth/refresh/` on a 401 before giving up.
