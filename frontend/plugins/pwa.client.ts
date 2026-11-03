// Registers the service worker (public/sw.js) that makes the site
// installable. Production only: in dev it would get in the way of HMR.
export default defineNuxtPlugin(() => {
  if (import.meta.dev || !('serviceWorker' in navigator)) return
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {})
  })
})
