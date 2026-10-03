/**
 * Dev-only live error log. Catches JS errors, unhandled promise rejections,
 * Vue render/lifecycle errors and failed API calls; shows them in the
 * on-page panel (DevLiveLogPanel) and sends them to the backend's
 * logs/live.log, next to the server's own errors.
 */
import type { LiveLogEntry } from '~/composables/useLiveLog'

export default defineNuxtPlugin((nuxtApp) => {
  if (!import.meta.dev) return

  const config = useRuntimeConfig()
  const { entries } = useLiveLog()
  const authStore = useAuthStore()
  const endpoint = `${config.public.apiBase}/dev/client-log/`
  let nextId = 1

  function report(entry: Omit<LiveLogEntry, 'id' | 'at'>) {
    const item = { ...entry, id: nextId++, at: new Date().toLocaleTimeString('fa-IR') }
    entries.value = [item, ...entries.value].slice(0, 50)
    // The logging call itself must never raise or log (no loops).
    navigator.sendBeacon?.(endpoint, new Blob([JSON.stringify({
      level: entry.level,
      kind: entry.kind,
      message: entry.message,
      detail: entry.detail,
      url: location.pathname + location.search,
      user: authStore.user?.email,
    })], { type: 'application/json' }))
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
      if (response.status === 401 || url.endsWith('/auth/refresh/') || url.endsWith('/dev/client-log/')) return
      const body = response._data
      report({
        level: response.status >= 500 ? 'error' : 'warning',
        kind: 'api',
        message: `${(options.method || 'GET').toUpperCase()} ${url.replace(config.public.apiBase, '')} → ${response.status}`,
        detail: body ? (typeof body === 'string' ? body.slice(0, 800) : JSON.stringify(body).slice(0, 800)) : undefined,
      })
    },
  }) as typeof $fetch
})
