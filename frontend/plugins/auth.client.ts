/**
 * Runs once on app start. The access token only ever lives in memory, so a
 * hard refresh loses it — but the httpOnly refresh cookie survives, so we
 * use it to silently re-establish the session before route middleware
 * decides whether the current page needs a login redirect.
 */
export default defineNuxtPlugin(async () => {
  const { request } = useApi()
  const authStore = useAuthStore()

  try {
    const data = await request<{ access: string }>('/auth/refresh/', { method: 'POST' })
    authStore.accessToken = data.access
    const user = await request<any>('/auth/me/')
    authStore.setSession(data.access, user)
  } catch {
    // No valid refresh cookie (never logged in, or it expired) — stay logged out.
  }
})
