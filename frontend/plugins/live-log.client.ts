/**
 * Live error log. Catches JS errors, unhandled promise rejections, Vue
 * render/lifecycle errors and failed API calls; keeps the last 50 for the
 * on-page panel (DevLiveLogPanel, dev mode and the developer account) and for
 * support reports, and sends them to the backend's monitoring log, next to the
 * server's own errors. In production only signed-in users' errors are sent.
 */
import type { LiveLogEntry } from '~/composables/useLiveLog'

export default defineNuxtPlugin((nuxtApp) => {
  const config = useRuntimeConfig()
  const { entries } = useLiveLog()
  const authStore = useAuthStore()
  const endpoint = `${config.public.apiBase}/monitoring/client-log/`
  let nextId = 1

  function send(entry: Omit<LiveLogEntry, 'id' | 'at'>) {
    const body = JSON.stringify({
      level: entry.level,
      kind: entry.kind,
      message: entry.message,
      detail: entry.detail,
      url: location.pathname + location.search,
    })
    if (import.meta.dev) {
      navigator.sendBeacon?.(endpoint, new Blob([body], { type: 'application/json' }))
      return
    }
    // Production accepts reports from signed-in users only; a beacon can't carry the token.
    if (!authStore.accessToken) return
    fetch(endpoint, {
      method: 'POST',
      keepalive: true,
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${authStore.accessToken}` },
      body,
    }).catch(() => {})
  }

  // `serverSeen`: an API error response the backend has already recorded itself, so it only
  // goes to the on-page list (and support reports), not to the server a second time.
  function report(entry: Omit<LiveLogEntry, 'id' | 'at'>, serverSeen = false) {
    const item = { ...entry, id: nextId++, at: new Date().toLocaleTimeString('fa-IR') }
    entries.value = [item, ...entries.value].slice(0, 50)
    if (serverSeen && !import.meta.dev) return
    // The logging call itself must never raise or log (no loops).
    try {
      send(entry)
    } catch {}
  }

  const describe = (err: any) => (err instanceof Error ? `${err.name}: ${err.message}` : String(err))

  window.addEventListener('error', (e) => {
    report({ level: 'error', kind: 'js', message: e.message || describe(e.error), detail: e.error?.stack })
  })
  window.addEventListener('unhandledrejection', (e) => {
    report({ level: 'error', kind: 'promise', message: describe(e.reason), detail: e.reason?.stack })
  })

  const previousHandler = nuxtApp.vueApp.config.errorHandler
  nuxtApp.vueApp.config.errorHandler = (err, instance, info) => {
    const component = instance?.$options?.__name || instance?.$options?.name || 'component'
    report({ level: 'error', kind: 'vue', message: `${describe(err)} (in <${component}> ${info})`, detail: (err as any)?.stack })
    previousHandler?.(err, instance, info)
  }

  // Every API call goes through the global $fetch (see useApi): log failed
  // responses with what the server said.
  globalThis.$fetch = $fetch.create({
    onRequestError({ request, error }) {
      report({ level: 'error', kind: 'api', message: `${String(request).replace(config.public.apiBase, '')} → سرور در دسترس نیست`, detail: error?.message })
    },
    onResponseError({ request, response, options }) {
      const url = String(request)
      // 401 = expired access token; useApi refreshes it and retries on its own.
      if (response.status === 401 || url.endsWith('/auth/refresh/') || url.endsWith('/monitoring/client-log/')) return
      const body = response._data
      report({
        level: response.status >= 500 ? 'error' : 'warning',
        kind: 'api',
        message: `${(options.method || 'GET').toUpperCase()} ${url.replace(config.public.apiBase, '')} → ${response.status}`,
        detail: body ? (typeof body === 'string' ? body.slice(0, 800) : JSON.stringify(body).slice(0, 800)) : undefined,
      }, true)
    },
  }) as typeof $fetch
})
