/**
 * Manual light/dark theme, available to every user regardless of role.
 * The actual class is applied to <html> by a blocking inline script (see
 * nuxt.config.ts `app.head.script`) before Vue even hydrates, to avoid a
 * flash of the wrong theme — this composable just keeps the toggle
 * button's state in sync with that and persists future changes.
 */
export function useTheme() {
  const theme = useState<'light' | 'dark'>('theme', () => 'light')

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

  function syncFromDom() {
    if (import.meta.client) {
      theme.value = document.documentElement.classList.contains('dark') ? 'dark' : 'light'
    }
  }

  return { theme, toggle, apply, syncFromDom }
}
