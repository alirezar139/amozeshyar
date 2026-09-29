/**
 * Total unread chat messages for the sidebar badge. One shared poller per
 * app (not per component), every 20s while logged in and the tab is visible.
 */
export function useUnreadMessages() {
  const total = useState('unread-messages', () => 0)
  const authStore = useAuthStore()
  const { request } = useApi()

  async function refresh() {
    if (!authStore.isAuthenticated) {
      total.value = 0
      return
    }
    try {
      total.value = (await request<{ total: number }>('/conversations/unread/')).total
    } catch {
      /* keep the last known count */
    }
  }

  function startPolling() {
    if (!import.meta.client) return
    const nuxtApp = useNuxtApp() as any
    if (nuxtApp._unreadTimer) return
    refresh()
    nuxtApp._unreadTimer = setInterval(() => {
      if (document.visibilityState === 'visible') refresh()
    }, 20000)
  }

  return { total, refresh, startPolling }
}
