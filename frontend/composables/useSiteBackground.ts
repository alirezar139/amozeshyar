export type BackgroundStyle =
  | 'aurora' | 'gradient' | 'waves' | 'particles' | 'stars' | 'bokeh' | 'shapes' | 'ribbons' | 'grid' | 'image' | 'plain'
export type BackgroundSpeed = 'slow' | 'normal' | 'fast'

export interface SiteBackground {
  style: BackgroundStyle
  colors: string[]
  image: string | null
  motion: boolean
  speed: BackgroundSpeed
}

export const BACKGROUND_STYLES: { value: BackgroundStyle; label: string; hint: string }[] = [
  { value: 'aurora', label: 'شفق', hint: 'لکه‌های نور رنگی که آرام جابه‌جا می‌شوند' },
  { value: 'gradient', label: 'گرادیان روان', hint: 'رنگ‌ها آرام در هم جریان دارند' },
  { value: 'waves', label: 'موج', hint: 'موج‌های لایه‌لایه در پایین صفحه' },
  { value: 'particles', label: 'قاصدک', hint: 'دانه‌های قاصدک که آرام در هوا بالا می‌روند' },
  { value: 'stars', label: 'آسمان پرستاره', hint: 'ستاره‌های چشمک‌زن و گاهی یک شهاب' },
  { value: 'bokeh', label: 'بوکه', hint: 'دایره‌های نورِ محو که آرام شناورند' },
  { value: 'shapes', label: 'اشکال هندسی', hint: 'دایره، مثلث و مربع‌هایی که آرام می‌چرخند' },
  { value: 'ribbons', label: 'نوارهای نور', hint: 'نوارهای موج‌دار نور که آرام می‌گذرند' },
  { value: 'grid', label: 'شبکه', hint: 'شبکه‌ای که آرام به سمت شما می‌آید' },
  { value: 'image', label: 'عکس دلخواه', hint: 'عکس خودتان با زوم و حرکت آرام' },
  { value: 'plain', label: 'ساده', hint: 'بدون حرکت و تزئین' },
]

export const BACKGROUND_SPEEDS: { value: BackgroundSpeed; label: string }[] = [
  { value: 'slow', label: 'آرام' },
  { value: 'normal', label: 'معمولی' },
  { value: 'fast', label: 'سریع' },
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
    speed: (owner.value?.background_speed as BackgroundSpeed) || 'slow',
  })

  return { background, draft }
}
