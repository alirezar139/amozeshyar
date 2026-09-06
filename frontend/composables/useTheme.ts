export type Palette = 'teal' | 'blue' | 'purple' | 'mono'

export const PALETTE_LABELS: Record<Palette, string> = {
  teal: 'تیل و کهربایی',
  blue: 'آبی و صورتی',
  purple: 'بنفش و طلایی',
  mono: 'خاکستری چندمنظوره',
}

/**
 * Manual light/dark theme and accent-color palette, available to every
 * user regardless of role. Both are applied to <html> by a blocking
 * inline script (see nuxt.config.ts `app.head.script`) before Vue even
 * hydrates, to avoid a flash of the wrong theme/color — this composable
 * just keeps reactive state in sync with that and persists future
 * changes (palette also syncs to the backend when logged in, so it
 * follows the account across devices; see plugins/auth.ts).
 */
export function useTheme() {
  const theme = useState<'light' | 'dark'>('theme', () => 'light')
  const palette = useState<Palette>('palette', () => 'teal')

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

  async function setPalette(value: Palette, opts: { persist?: boolean } = {}) {
    palette.value = value
    if (import.meta.client) {
      if (value === 'teal') {
        document.documentElement.removeAttribute('data-palette')
      } else {
        document.documentElement.setAttribute('data-palette', value)
      }
      localStorage.setItem('palette', value)
    }
    if (opts.persist !== false) {
      const authStore = useAuthStore()
      if (authStore.isAuthenticated) {
        const { request } = useApi()
        await request('/auth/me/', { method: 'PATCH', body: { color_theme: value } }).catch(() => {})
      }
    }
  }

  function syncFromDom() {
    if (!import.meta.client) return
    theme.value = document.documentElement.classList.contains('dark') ? 'dark' : 'light'
    palette.value = (document.documentElement.getAttribute('data-palette') as Palette | null) ?? 'teal'
  }

  return { theme, toggle, apply, palette, setPalette, syncFromDom }
}
