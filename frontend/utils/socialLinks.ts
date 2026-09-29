// The site owner's social_links are stored as { label: url }. Older rows
// used English keys; they display in Persian.
const LEGACY_LABELS: Record<string, string> = {
  instagram: 'اینستاگرام', telegram: 'تلگرام', youtube: 'یوتیوب', website: 'وب‌سایت', linkedin: 'لینکدین',
}

// Badge color per known platform, matched on label or URL; anything else gets the neutral badge.
const PLATFORM_STYLES: { match: RegExp; class: string }[] = [
  { match: /اینستا|instagram/i, class: 'bg-gradient-to-br from-amber-400 via-pink-500 to-purple-600' },
  { match: /تلگرام|telegram|t\.me/i, class: 'bg-sky-500' },
  { match: /یوتیوب|youtube|youtu\.be/i, class: 'bg-red-600' },
  { match: /آپارات|aparat/i, class: 'bg-rose-600' },
  { match: /لینکدین|linkedin/i, class: 'bg-blue-700' },
  { match: /واتس|whatsapp|wa\.me/i, class: 'bg-emerald-500' },
]

export interface SocialLink {
  label: string
  url: string
}

export function socialLinkLabel(key: string): string {
  return LEGACY_LABELS[key] ?? key
}

export function socialBadgeClass(link: SocialLink): string {
  const hay = `${link.label} ${link.url}`
  return PLATFORM_STYLES.find((p) => p.match.test(hay))?.class ?? 'bg-gray-500'
}

/** Only http(s) links are rendered — the owner types these freely, and a javascript: URL would run on click. */
export function publicSocialLinks(raw: Record<string, string> | null | undefined): SocialLink[] {
  return Object.entries(raw ?? {})
    .filter(([, url]) => /^https?:\/\//i.test(String(url)))
    .map(([key, url]) => ({ label: socialLinkLabel(key), url: String(url) }))
}
