// The PWA manifest, built per request from the site settings so each
// instructor's install shows its own name on the phone's home screen.
export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const apiBase = config.apiBaseServer || config.public.apiBase
  const owner = await $fetch<{ site_name?: string; display_name?: string; headline?: string }>(`${apiBase}/site/`).catch(
    () => null,
  )
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
