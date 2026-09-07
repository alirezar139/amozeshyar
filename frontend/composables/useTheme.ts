export interface ThemeColors {
  primary: string
  accent: string
}

// Quick-start combinations — clicking one just calls setColors() with its
// pair, so there's no separate code path from a fully free pick. These
// happen to be the palettes this feature started out as before becoming
// a free picker, kept because a curated starting point is still useful.
export const COLOR_PRESETS: { label: string; colors: ThemeColors }[] = [
  { label: 'تیل و کهربایی', colors: { primary: '#157e6c', accent: '#f98307' } },
  { label: 'آبی و صورتی', colors: { primary: '#2563eb', accent: '#db2777' } },
  { label: 'بنفش و طلایی', colors: { primary: '#7c3aed', accent: '#ca8a04' } },
  { label: 'خاکستری چندمنظوره', colors: { primary: '#475569', accent: '#f98307' } },
  { label: 'سبز و کهربایی', colors: { primary: '#16a34a', accent: '#f98307' } },
  { label: 'قرمز و طلایی', colors: { primary: '#dc2626', accent: '#ca8a04' } },
  { label: 'نارنجی و آبی', colors: { primary: '#ea580c', accent: '#2563eb' } },
]

export const DEFAULT_COLORS: ThemeColors = { primary: '#157e6c', accent: '#f98307' }

/**
 * Manual light/dark theme and primary/accent color, available to every
 * user regardless of role. Both are applied to <html> by a blocking
 * inline script (see nuxt.config.ts `app.head.script`) before Vue even
 * hydrates, to avoid a flash of the wrong theme/color — this composable
 * just keeps reactive state in sync with that and persists future
 * changes (colors also sync to the backend when logged in, so they
 * follow the account across devices; see plugins/auth.ts).
 *
 * Colors are free-form hex, not a fixed palette id: generateRamp()
 * (utils/colorRamp.ts) turns whatever the user picks into a full
 * 50-950 Tailwind-style shade ramp, applied as CSS custom properties
 * that tailwind.config.js's color functions read from at runtime.
 */
export function useTheme() {
  const theme = useState<'light' | 'dark'>('theme', () => 'light')
  const colors = useState<ThemeColors>('theme-colors', () => ({ ...DEFAULT_COLORS }))

  function apply(value: 'light' | 'dark') {
    theme.value = value
    if (import.meta.client) {
      document.documentElement.classList.toggle('dark', value === 'dark')
      localStorage.setItem('theme', value)
    }
  }

  function toggle() {
    apply(theme.value === 'dark' ? 'light' : 'dark')
  }

  function applyColorsToDom(next: ThemeColors) {
    if (!import.meta.client) return
    const root = document.documentElement.style
    const primaryRamp = generateRamp(next.primary, 'primary')
    const accentRamp = generateRamp(next.accent, 'accent')
    for (const [step, value] of Object.entries(primaryRamp)) root.setProperty(`--c-primary-${step}`, value)
    for (const [step, value] of Object.entries(accentRamp)) root.setProperty(`--c-accent-${step}`, value)
  }

  async function setColors(next: ThemeColors, opts: { persist?: boolean } = {}) {
    colors.value = next
    if (import.meta.client) {
      applyColorsToDom(next)
      localStorage.setItem('theme-colors', JSON.stringify(next))
    }
    if (opts.persist !== false) {
      const authStore = useAuthStore()
      if (authStore.isAuthenticated) {
        const { request } = useApi()
        await request('/auth/me/', {
          method: 'PATCH',
          body: { primary_color: next.primary, accent_color: next.accent },
        }).catch(() => {})
      }
    }
  }

  function syncFromDom() {
    if (!import.meta.client) return
    theme.value = document.documentElement.classList.contains('dark') ? 'dark' : 'light'
    try {
      const stored = localStorage.getItem('theme-colors')
      if (stored) colors.value = JSON.parse(stored)
    } catch {
      colors.value = { ...DEFAULT_COLORS }
    }
  }

  return { theme, toggle, apply, colors, setColors, syncFromDom }
}
