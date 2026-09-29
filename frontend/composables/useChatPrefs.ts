export type ChatWallpaper =
  | 'dots' | 'doodle' | 'sunset' | 'ocean' | 'lavender' | 'mint' | 'night' | 'grid' | 'waves' | 'plain'
export type ChatFontSize = 'sm' | 'md' | 'lg'

export const CHAT_WALLPAPERS: { value: ChatWallpaper; label: string }[] = [
  { value: 'dots', label: 'نقطه‌ها' },
  { value: 'doodle', label: 'طرح درسی' },
  { value: 'sunset', label: 'غروب' },
  { value: 'ocean', label: 'اقیانوس' },
  { value: 'lavender', label: 'اسطوخودوس' },
  { value: 'mint', label: 'نعنایی' },
  { value: 'night', label: 'شب پرستاره' },
  { value: 'grid', label: 'دفتر شطرنجی' },
  { value: 'waves', label: 'موج' },
  { value: 'plain', label: 'ساده' },
]

export const CHAT_FONT_SIZES: { value: ChatFontSize; label: string }[] = [
  { value: 'sm', label: 'کوچک' },
  { value: 'md', label: 'متوسط' },
  { value: 'lg', label: 'بزرگ' },
]

interface ChatPrefs {
  wallpaper: ChatWallpaper
  fontSize: ChatFontSize
  enterToSend: boolean
  sound: boolean
}
const DEFAULTS: ChatPrefs = { wallpaper: 'dots', fontSize: 'md', enterToSend: true, sound: true }
const KEY = 'chat-prefs'

/** Personal messenger preferences, remembered per browser. */
export function useChatPrefs() {
  const prefs = useState<ChatPrefs>('chat-prefs', () => ({ ...DEFAULTS }))
  const loaded = useState('chat-prefs-loaded', () => false)
  if (import.meta.client && !loaded.value) {
    loaded.value = true
    try {
      const saved = JSON.parse(localStorage.getItem(KEY) || '{}')
      prefs.value = {
        ...DEFAULTS,
        ...saved,
        wallpaper: CHAT_WALLPAPERS.some((w) => w.value === saved.wallpaper) ? saved.wallpaper : DEFAULTS.wallpaper,
      }
    } catch {
      /* storage unavailable: keep defaults */
    }
  }
  function update(patch: Partial<ChatPrefs>) {
    prefs.value = { ...prefs.value, ...patch }
    try {
      localStorage.setItem(KEY, JSON.stringify(prefs.value))
    } catch {
      /* ignore */
    }
  }
  return { prefs, update }
}

/** A short, soft two-note chime for incoming messages (no audio file needed). */
export function playChatChime() {
  try {
    const Ctx = window.AudioContext || (window as any).webkitAudioContext
    const ctx = new Ctx()
    const now = ctx.currentTime
    for (const [i, freq] of [880, 1320].entries()) {
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.type = 'sine'
      osc.frequency.value = freq
      gain.gain.setValueAtTime(0, now + i * 0.09)
      gain.gain.linearRampToValueAtTime(0.08, now + i * 0.09 + 0.02)
      gain.gain.exponentialRampToValueAtTime(0.0001, now + i * 0.09 + 0.35)
      osc.connect(gain).connect(ctx.destination)
      osc.start(now + i * 0.09)
      osc.stop(now + i * 0.09 + 0.4)
    }
    setTimeout(() => ctx.close(), 800)
  } catch {
    /* audio blocked until the user interacts with the page — fine */
  }
}
