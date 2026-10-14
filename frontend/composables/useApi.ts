import { appendResponseHeader } from 'h3'

// The refresh in flight in this browser tab, shared by every request that hits a 401 meanwhile.
// Client only: on the server this module is shared by every visitor's SSR request.
let clientRefresh: Promise<boolean> | null = null

/**
 * Thin wrapper around $fetch: attaches the in-memory access token and
 * transparently retries once via the refresh-cookie endpoint on a 401,
 * so callers never have to think about token expiry.
 */
export function useApi() {
  const config = useRuntimeConfig()
  const authStore = useAuthStore()
  // Must be captured synchronously here, not inside an async function
  // after an `await` — Nuxt's composable context doesn't survive that.
  const requestEvent = import.meta.server ? useRequestEvent() : null

  // During SSR there is no browser to attach the httpOnly refresh cookie
  // for us (`credentials: 'include'` only does anything in an actual
  // browser fetch) — so forward the incoming request's cookie header by
  // hand. This is a plain server-to-server call, not a browser one, so
  // none of the CORS/SameSite rules that motivate the httpOnly cookie
  // in the first place apply here.
  function forwardedCookie(): string | undefined {
    if (!import.meta.server) return undefined
    return useRequestHeaders(['cookie']).cookie
  }

  // The backend rotates the refresh cookie on every use (see
  // apps/accounts/views.py) so replay of an old token fails. When the SSR
  // side calls /auth/refresh/ on the browser's behalf, the rotated cookie
  // comes back on that internal server-to-server response — which the
  // browser never sees unless we relay it onto our own response. Skipping
  // this would leave the browser holding an already-blacklisted cookie
  // after the very first SSR-triggered refresh, breaking the *next*
  // reload's session restore.
  // SSR requests leave from the frontend container, so without help every visitor would share
  // that one IP in the backend's per-IP throttles (100 anonymous calls an hour would take the
  // site down for everyone). Talk to the backend over the internal network and pass along the
  // visitor's IP from X-Real-IP, which nginx sets from the TCP peer and clients can't forge.
  const baseUrl = import.meta.server && config.apiBaseServer ? config.apiBaseServer : config.public.apiBase

  // Read now, like requestEvent above: request() may run after the caller has awaited something.
  const incoming = import.meta.server ? useRequestHeaders(['x-real-ip', 'host']) : {}

  function addServerSideHeaders(headers: Headers) {
    if (!import.meta.server || !config.apiBaseServer) return
    if (incoming['x-real-ip']) headers.set('X-Forwarded-For', incoming['x-real-ip'])
    if (incoming.host) headers.set('X-Forwarded-Host', incoming.host)
    headers.set('X-Forwarded-Proto', 'https')
  }

  function relaySetCookie(headers: Headers) {
    if (!requestEvent) return
    const setCookieValues = typeof (headers as any).getSetCookie === 'function' ? (headers as any).getSetCookie() : []
    for (const value of setCookieValues as string[]) {
      appendResponseHeader(requestEvent, 'set-cookie', value)
    }
  }

  async function request<T>(path: string, options: Parameters<typeof $fetch>[1] = {}): Promise<T> {
    const headers = new Headers(options.headers as HeadersInit)
    const cookie = forwardedCookie()
    if (cookie) headers.set('cookie', cookie)
    addServerSideHeaders(headers)
    if (authStore.accessToken) {
      headers.set('Authorization', `Bearer ${authStore.accessToken}`)
    }

    try {
      return await $fetch<T>(`${baseUrl}${path}`, {
        ...options,
        headers,
        credentials: 'include',
      })
    } catch (error: any) {
      if (error?.response?.status === 401 && authStore.accessToken) {
        const refreshed = await refreshSession()
        if (refreshed) {
          headers.set('Authorization', `Bearer ${authStore.accessToken}`)
          return await $fetch<T>(`${baseUrl}${path}`, {
            ...options,
            headers,
            credentials: 'include',
          })
        }
        authStore.clearSession()
      }
      throw error
    }
  }

  // The backend rotates the refresh cookie and revokes the old one on every use. When the
  // access token expires, a page that fires several requests at once (the messenger does)
  // used to start one refresh per request with the same cookie: the first won, the rest were
  // refused, and that refusal logged the user out. Now concurrent callers share one refresh,
  // and a refusal is retried once after a moment, by which time the browser holds the cookie
  // that a parallel refresh (say, in another tab) just received.
  async function refreshSession(): Promise<boolean> {
    if (import.meta.server) return refreshOnce()
    if (!clientRefresh) {
      clientRefresh = (async () => {
        if (await refreshOnce()) return true
        await new Promise((resolve) => setTimeout(resolve, 400))
        return refreshOnce()
      })().finally(() => {
        clientRefresh = null
      })
    }
    return clientRefresh
  }

  async function refreshOnce(): Promise<boolean> {
    try {
      const headers = new Headers()
      const cookie = forwardedCookie()
      if (cookie) headers.set('cookie', cookie)
      addServerSideHeaders(headers)
      const res = await $fetch.raw<{ access: string }>(`${baseUrl}/auth/refresh/`, {
        method: 'POST',
        credentials: 'include',
        headers,
      })
      relaySetCookie(res.headers)
      if (!res._data) return false
      authStore.accessToken = res._data.access
      return true
    } catch {
      return false
    }
  }

  return { request, refreshSession }
}
