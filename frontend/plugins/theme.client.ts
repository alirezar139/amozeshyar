// The <html> class itself is already set correctly by the blocking inline
// script in nuxt.config.ts (before this even runs) — this just syncs the
// reactive `theme` state so the toggle button shows the right icon from
// the very first render instead of defaulting to 'light'.
export default defineNuxtPlugin(() => {
  useTheme().syncFromDom()
})
