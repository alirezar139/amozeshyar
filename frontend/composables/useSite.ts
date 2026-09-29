export interface SiteOwner {
  slug: string
  display_name: string
  headline: string
  bio: string
  credentials: { title: string; issuer?: string; year?: string | number }[]
  cover_image: string | null
  social_links: Record<string, string>
  rating_avg: string
  total_students: number
  phone_number: string
}

/**
 * The instructor this install belongs to. Each instructor gets their own
 * copy of the software, so this is the site's identity: header brand,
 * homepage hero, footer, SEO titles. Fetched once and shared by key.
 */
export function useSite() {
  const { request } = useApi()
  const { data: owner, refresh } = useAsyncData('site-owner', () => request<SiteOwner>('/site/').catch(() => null), {
    getCachedData: (key, nuxtApp) => nuxtApp.payload.data[key] ?? nuxtApp.static.data[key],
  })
  const siteName = computed(() => owner.value?.display_name || 'آموزش‌یار')
  return { owner, siteName, refresh }
}
