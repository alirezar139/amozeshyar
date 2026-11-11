// The PWA manifest, built per request from the site settings so each
// instructor's install shows its own name on the phone's home screen.
export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const apiBase = config.apiBaseServer || config.public.apiBase
  // Straight to the backend container over plain HTTP: without X-Forwarded-Proto Django's
  // SSL redirect sends it to https://backend:8000, which hangs ~20 s and falls back to the
  // default name (and fails the container's healthcheck, which fetches this route). Bounded,
  // so a slow backend never makes the frontend look down.
  // The visitor's IP (from nginx's X-Real-IP), as useApi.ts sends it: otherwise every
  // visitor's manifest counts against the frontend container's one IP in the API throttle.
  const realIp = getRequestHeader(event, 'x-real-ip')
  const owner = await $fetch<{ site_name?: string; display_name?: string; headline?: string }>(`${apiBase}/site/`, {
    headers: { 'X-Forwarded-Proto': 'https', ...(realIp ? { 'X-Forwarded-For': realIp } : {}) },
    timeout: 3000,
  }).catch(() => null)
  const name = owner?.site_name || owner?.display_name || 'مدرس‌یار'

  setResponseHeader(event, 'Content-Type', 'application/manifest+json; charset=utf-8')
  setResponseHeader(event, 'Cache-Control', 'public, max-age=3600')
  return {
    name,
    short_name: name,
    description: owner?.headline || name,
    lang: 'fa',
    dir: 'rtl',
    start_url: '/',
    scope: '/',
    display: 'standalone',
    background_color: '#157E6C',
    theme_color: '#157E6C',
    icons: [
      { src: '/icons/icon-192.png', sizes: '192x192', type: 'image/png' },
      { src: '/icons/icon-512.png', sizes: '512x512', type: 'image/png' },
      { src: '/icons/maskable-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
    ],
  }
})
