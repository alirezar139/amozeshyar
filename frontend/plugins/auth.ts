/**
 * Restores the session from the httpOnly refresh cookie.
 *
 * Runs on both server and client: during SSR the cookie is forwarded by
 * hand (see useApi.ts) since there's no browser to attach it for us, so a
 * page rendered on first load already reflects the real auth state
 * (is_enrolled, progress, etc.) instead of always looking logged-out
 * until a client-side refetch. On the client we skip re-running this if
 * hydration already gave us a session (Pinia state ships in the SSR
 * payload), and otherwise fall back to it — e.g. for a client-only route
 * or if the SSR-side refresh attempt failed for some transient reason.
 */
export default defineNuxtPlugin(async () => {
  const authStore = useAuthStore()
  if (import.meta.client && authStore.accessToken) return

  const { request, refreshSession } = useApi()
  const refreshed = await refreshSession()
  if (!refreshed) return

  try {
    const user = await request<any>('/auth/me/')
    authStore.setSession(authStore.accessToken!, user)

    // Sync the account's saved colors onto this device (client only —
    // there's no localStorage/DOM to touch during SSR, and the inline
    // script already applied whatever this device remembers locally for
    // the first paint). Not persisting back: this is a read, not a change.
    if (import.meta.client && user?.primary_color && user?.accent_color) {
      useTheme().setColors({ primary: user.primary_color, accent: user.accent_color }, { persist: false })
    }
  } catch {
    authStore.clearSession()
  }
})
