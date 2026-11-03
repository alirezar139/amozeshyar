// Service worker for the installed app (PWA). Deliberately minimal: it
// never caches API responses, videos or pages — course content is
// stream-only and per-user — and only steps in when a page can't load at
// all, to show the offline screen instead of the browser's error page.
const OFFLINE = '/offline.html'
const CACHE = 'offline-v1'

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.add(OFFLINE)))
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))),
  )
  self.clients.claim()
})

self.addEventListener('fetch', (event) => {
  if (event.request.mode !== 'navigate') return
  event.respondWith(fetch(event.request).catch(() => caches.match(OFFLINE)))
})
