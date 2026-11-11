/**
 * Restores the session from the httpOnly refresh cookie.
 *
 * Runs on both server and client: during SSR the cookie is forwarded by
 * hand (see useApi.ts) since there's no browser to attach it for us, so a
 * page rendered on first load already reflects the real auth state
 * (is_enrolled, progress, etc.) instead of always looking logged-out
 * until a client-side refetch. On the client we skip re-running this if
 * hydration already gave us the user (Pinia state ships in the SSR
 * payload) — then it only fetches a fresh access token — and otherwise
 * restores the whole session, e.g. for a client-only route or if the
 * SSR-side refresh attempt failed for some transient reason.
 *
 * The access token itself never goes into that payload (FE-02): the page's
 * HTML would carry a bearer token, one cache layer (CDN, nginx) away from
 * being served to someone else. The server drops it once the page is
 * rendered; the browser gets its own from the httpOnly cookie before mount.
 */
export default defineNuxtPlugin(async (nuxtApp) => {
  const authStore = useAuthStore()
  if (import.meta.server) {
    nuxtApp.hook('app:rendered', () => {
      authStore.accessToken = null
    })
  }
  if (import.meta.client && authStore.accessToken) return

  // During SSR we can see the request's cookies: a visitor without the
  // refresh cookie has no session to restore, so don't spend a round trip
  // (and a guaranteed 401) finding that out on every page view.
  if (import.meta.server && !useRequestHeaders(['cookie']).cookie?.includes('refresh_token=')) return

  const { request, refreshSession } = useApi()
  const hydratedUser = import.meta.client ? authStore.user : null
  const refreshed = await refreshSession()
  if (!refreshed) {
    // The page was rendered signed in but the session is gone now: show it signed out
    // rather than a user with no token whose every request fails.
    if (hydratedUser) authStore.clearSession()
    return
  }

  try {
    // Already in the payload when the server rendered the page signed in: no second /me.
    const user = hydratedUser ?? (await request<any>('/auth/me/'))
    authStore.setSession(authStore.accessToken!, user)

    // Sync the account's saved colors onto this device (client only —
    // there's no localStorage/DOM to touch during SSR, and the inline
    // script already applied whatever this device remembers locally for
    // the first paint). Not persisting back: this is a read, not a change.
    if (import.meta.client && user?.primary_color && user?.accent_color) {
      useTheme().setColors(
        {
          primary: user.primary_color,
          accent: user.accent_color,
          header: user.header_color ?? user.primary_color,
          nav: user.nav_color ?? user.primary_color,
        },
        { persist: false }
      )
    }
  } catch {
    authStore.clearSession()
  }
})
