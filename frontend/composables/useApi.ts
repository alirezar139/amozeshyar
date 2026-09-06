/**
 * Thin wrapper around $fetch: attaches the in-memory access token and
 * transparently retries once via the refresh-cookie endpoint on a 401,
 * so callers never have to think about token expiry.
 */
export function useApi() {
  const config = useRuntimeConfig()
  const authStore = useAuthStore()

  async function request<T>(path: string, options: Parameters<typeof $fetch>[1] = {}): Promise<T> {
    const headers = new Headers(options.headers as HeadersInit)
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
        const refreshed = await tryRefresh()
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

  async function tryRefresh(): Promise<boolean> {
    try {
      const data = await $fetch<{ access: string }>(`${config.public.apiBase}/auth/refresh/`, {
        method: 'POST',
        credentials: 'include',
      })
      authStore.accessToken = data.access
      return true
    } catch {
      return false
    }
  }

  return { request }
}
