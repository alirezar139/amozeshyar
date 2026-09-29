export type BackgroundStyle =
  | 'aurora' | 'gradient' | 'waves' | 'particles' | 'stars' | 'bokeh' | 'shapes' | 'ribbons' | 'grid'
  | 'mountains' | 'clouds' | 'ocean' | 'forest' | 'dunes' | 'sakura' | 'leaves' | 'snow' | 'rain' | 'fireflies'
  | 'image' | 'plain'
export type BackgroundSpeed = 'slow' | 'normal' | 'fast'

export interface SiteBackground {
  style: BackgroundStyle
  colors: string[]
  image: string | null
  motion: boolean
  speed: BackgroundSpeed
}

export const BACKGROUND_STYLES: { value: BackgroundStyle; label: string; hint: string; group: 'nature' | 'abstract' | 'other' }[] = [
  { value: 'mountains', label: 'کوهستان', hint: 'رشته‌کوه لایه‌لایه با مه و ابر', group: 'nature' },
  { value: 'clouds', label: 'آسمان ابری', hint: 'ابرهایی که آرام می‌گذرند و پرنده‌ها', group: 'nature' },
  { value: 'ocean', label: 'دریا', hint: 'افق دریا، موج و درخشش آفتاب', group: 'nature' },
  { value: 'forest', label: 'جنگل', hint: 'درختان کاج و مه؛ شب‌ها کرم شب‌تاب', group: 'nature' },
  { value: 'dunes', label: 'کویر', hint: 'تپه‌های شنی در غروب', group: 'nature' },
  { value: 'sakura', label: 'شکوفه‌ی بهاری', hint: 'گلبرگ‌هایی که چرخان فرو می‌ریزند', group: 'nature' },
  { value: 'leaves', label: 'برگ پاییزی', hint: 'برگ‌های رنگی در حال ریزش', group: 'nature' },
  { value: 'snow', label: 'برف', hint: 'بارش آرام برف', group: 'nature' },
  { value: 'rain', label: 'باران', hint: 'قطره‌های باران', group: 'nature' },
  { value: 'fireflies', label: 'کرم شب‌تاب', hint: 'نورهای کوچکِ سرگردان', group: 'nature' },
  { group: 'abstract', value: 'aurora', label: 'شفق', hint: 'لکه‌های نور رنگی که آرام جابه‌جا می‌شوند' },
  { group: 'abstract', value: 'gradient', label: 'گرادیان روان', hint: 'رنگ‌ها آرام در هم جریان دارند' },
  { group: 'abstract', value: 'waves', label: 'موج', hint: 'موج‌های لایه‌لایه در پایین صفحه' },
  { group: 'abstract', value: 'particles', label: 'قاصدک', hint: 'دانه‌های قاصدک که آرام در هوا بالا می‌روند' },
  { group: 'abstract', value: 'stars', label: 'آسمان پرستاره', hint: 'ستاره‌های چشمک‌زن و گاهی یک شهاب' },
  { group: 'abstract', value: 'bokeh', label: 'بوکه', hint: 'دایره‌های نورِ محو که آرام شناورند' },
  { group: 'abstract', value: 'shapes', label: 'اشکال هندسی', hint: 'دایره، مثلث و مربع‌هایی که آرام می‌چرخند' },
  { group: 'abstract', value: 'ribbons', label: 'نوارهای نور', hint: 'نوارهای موج‌دار نور که آرام می‌گذرند' },
  { group: 'abstract', value: 'grid', label: 'شبکه', hint: 'شبکه‌ای که آرام به سمت شما می‌آید' },
  { group: 'other', value: 'image', label: 'عکس دلخواه', hint: 'عکس خودتان با زوم و حرکت آرام' },
  { group: 'other', value: 'plain', label: 'ساده', hint: 'بدون حرکت و تزئین' },
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
