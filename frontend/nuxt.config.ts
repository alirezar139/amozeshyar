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
    '/courses': { swr: 3600 },
    '/courses/**': { swr: 3600 },
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
    },
  },
})
