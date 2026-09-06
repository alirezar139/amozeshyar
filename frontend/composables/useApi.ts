import { appendResponseHeader } from 'h3'

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
    if (authStore.accessToken) {
      headers.set('Authorization', `Bearer ${authStore.accessToken}`)
    }

    try {
      return await $fetch<T>(`${config.public.apiBase}${path}`, {
        ...options,
        headers,
        credentials: 'include',
      })
    } catch (error: any) {
      if (error?.response?.status === 401 && authStore.accessToken) {
        const refreshed = await refreshSession()
        if (refreshed) {
          headers.set('Authorization', `Bearer ${authStore.accessToken}`)
          return await $fetch<T>(`${config.public.apiBase}${path}`, {
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

  async function refreshSession(): Promise<boolean> {
    try {
      const headers = new Headers()
      const cookie = forwardedCookie()
      if (cookie) headers.set('cookie', cookie)
      const res = await $fetch.raw<{ access: string }>(`${config.public.apiBase}/auth/refresh/`, {
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
