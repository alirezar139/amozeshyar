export interface SiteOwner {
  slug: string
  display_name: string
  site_name: string
  logo: string | null
  background_style: string
  background_colors: string[]
  background_image: string | null
  background_motion: boolean
  background_speed: string
  headline: string
  bio: string
  credentials: { title: string; issuer?: string; year?: string | number }[]
  cover_image: string | null
  avatar: string | null
  social_links: Record<string, string>
  rating_avg: string
  total_students: number
  phone_number: string
  allow_peer_chat: boolean
}

/**
 * The instructor this install belongs to. Each instructor gets their own
 * copy of the software, so this is the site's identity. `siteName` is the
 * brand (header, footer, page titles) and falls back to the instructor's
 * name; `teacherName` is always the person (homepage hero, "استاد شما").
 * Fetched once and shared by key.
 */
export function useSite() {
  const { request } = useApi()
  const { data: owner, refresh } = useAsyncData('site-owner', () => request<SiteOwner>('/site/').catch(() => null), {
    // Reuse what SSR/an earlier page already fetched — but never for an
    // explicit refresh(), or saving site settings would re-read the stale copy.
    getCachedData: (key, nuxtApp, ctx) =>
      ctx?.cause === 'refresh:manual' ? undefined : nuxtApp.payload.data[key] ?? nuxtApp.static.data[key],
  })
  const teacherName = computed(() => owner.value?.display_name || 'مدرس‌یار')
  const siteName = computed(() => owner.value?.site_name || teacherName.value)
  // «استاد روستا»: how the site refers to the teacher in running text.
  const teacherTitle = computed(() => `استاد ${teacherName.value.trim().split(/\s+/).pop()}`)
  return { owner, siteName, teacherName, teacherTitle, refresh }
}
