export type BackgroundStyle = 'aurora' | 'gradient' | 'waves' | 'particles' | 'image' | 'plain'

export interface SiteBackground {
  style: BackgroundStyle
  colors: string[]
  image: string | null
  motion: boolean
}

export const BACKGROUND_STYLES: { value: BackgroundStyle; label: string; hint: string }[] = [
  { value: 'aurora', label: 'شفق', hint: 'لکه‌های نور رنگی که آرام جابه‌جا می‌شوند' },
  { value: 'gradient', label: 'گرادیان روان', hint: 'رنگ‌ها آرام در هم جریان دارند' },
  { value: 'waves', label: 'موج', hint: 'موج‌های لایه‌لایه در پایین صفحه' },
  { value: 'particles', label: 'ذرات شناور', hint: 'ذره‌های نور که آرام بالا می‌روند' },
  { value: 'image', label: 'عکس دلخواه', hint: 'عکس خودتان با زوم و حرکت آرام' },
  { value: 'plain', label: 'ساده', hint: 'بدون حرکت و تزئین' },
]

/**
 * The site-wide background: what the owner saved, overridden by an unsaved
 * draft while they're editing it in site settings, so every choice
 * previews live on the real page behind the form.
 */
export function useSiteBackground() {
  const { owner } = useSite()
  const draft = useState<SiteBackground | null>('site-background-draft', () => null)

  const background = computed<SiteBackground>(() => draft.value ?? {
    style: (owner.value?.background_style as BackgroundStyle) || 'aurora',
    colors: owner.value?.background_colors ?? [],
    image: owner.value?.background_image ?? null,
    motion: owner.value?.background_motion ?? true,
  })

  return { background, draft }
}
