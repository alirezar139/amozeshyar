// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: true },

  css: ['~/assets/css/main.css'],

  modules: [
    '@pinia/nuxt',
    '@nuxtjs/tailwindcss',
    '@nuxtjs/sitemap',
    '@nuxtjs/robots',
    '@nuxt/image',
  ],

  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8000/api/v1',
    },
  },

  // Rendering strategy per route group (the core of the SEO plan):
  // public marketing/catalog pages are pre-rendered or SSR'd for crawlers
  // and social-share previews; authenticated dashboards are pure SPA since
  // SEO doesn't apply there and skipping SSR keeps them cheap to serve.
  routeRules: {
    '/': { prerender: true },
    // Course pages embed the viewing student's own enrollment/progress
    // (see courses/serializers.py `is_enrolled`, `progress_seconds`) —
    // `swr` is a *shared* cache keyed by URL only, so caching these would
    // leak one user's purchase/progress state into what another visitor's
    // browser renders for the same course. Plain per-request SSR instead.
    '/courses': {},
    '/courses/**': {},
    '/instructors/**': { swr: 3600 },
    '/dashboard/**': { ssr: false },
    '/instructor-panel/**': { ssr: false },
    '/admin/**': { ssr: false },
  },

  site: {
    url: process.env.NUXT_PUBLIC_SITE_URL || 'http://localhost:3300',
  },

  app: {
    head: {
      htmlAttrs: { lang: 'fa', dir: 'rtl' },
      link: [
        { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
        { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' },
        {
          rel: 'stylesheet',
          href: 'https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;500;600;700;800&display=swap',
        },
      ],
      // Applies the saved theme (or the OS preference) before Vue even
      // hydrates, so there's no flash of the wrong theme on load. Kept as
      // a raw inline script (not a composable) specifically because it
      // must run before anything else.
      script: [
        {
          innerHTML: `(function(){try{var t=localStorage.getItem('theme');if(!t){t=window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'}if(t==='dark')document.documentElement.classList.add('dark')}catch(e){}})()`,
        },
      ],
    },
  },
})
