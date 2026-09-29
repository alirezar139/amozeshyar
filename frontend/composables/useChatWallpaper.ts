export type ChatWallpaper = 'dots' | 'plain' | 'gradient' | 'doodle' | 'waves' | 'grid'

export const CHAT_WALLPAPERS: { value: ChatWallpaper; label: string }[] = [
  { value: 'dots', label: 'نقطه‌ها' },
  { value: 'doodle', label: 'طرح درسی' },
  { value: 'gradient', label: 'رنگین' },
  { value: 'waves', label: 'موج' },
  { value: 'grid', label: 'دفتر شطرنجی' },
  { value: 'plain', label: 'ساده' },
]

/** The chat background is a personal preference, remembered per browser. */
export function useChatWallpaper() {
  const wallpaper = useState<ChatWallpaper>('chat-wallpaper', () => 'dots')
  onMounted(() => {
    try {
      const saved = localStorage.getItem('chat-wallpaper') as ChatWallpaper | null
      if (saved && CHAT_WALLPAPERS.some((w) => w.value === saved)) wallpaper.value = saved
    } catch {
      /* storage unavailable: keep the default */
    }
  })
  function setWallpaper(value: ChatWallpaper) {
    wallpaper.value = value
    try {
      localStorage.setItem('chat-wallpaper', value)
    } catch {
      /* ignore */
    }
  }
  return { wallpaper, setWallpaper }
}
