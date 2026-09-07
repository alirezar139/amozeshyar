/** @type {import('tailwindcss').Config} */

// Builds a Tailwind color function backed by a CSS custom property, so the
// actual value can change at runtime (a user's own freely-picked color,
// not a fixed palette) instead of being frozen at build time — see
// assets/css/main.css for the default `--c-primary-*`/`--c-accent-*`
// values, and utils/colorRamp.ts + useTheme.ts for how a picked hex color
// gets turned into a full shade ramp and applied. Still supports
// Tailwind's opacity modifiers (`bg-primary-600/30`) since we return the
// `rgb(... / a)` form.
function fromVar(name) {
  return ({ opacityValue }) =>
    opacityValue === undefined ? `rgb(var(${name}))` : `rgb(var(${name}) / ${opacityValue})`
}

export default {
  content: [
    './components/**/*.{vue,js,ts}',
    './layouts/**/*.vue',
    './pages/**/*.vue',
    './plugins/**/*.{js,ts}',
    './app.vue',
    './error.vue',
  ],
  // 'class' (not 'media') so the theme is a user choice, not just the OS
  // setting — see components/layout/ThemeToggle.vue and useTheme.ts.
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Vazirmatn', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      colors: {
        primary: {
          50: fromVar('--c-primary-50'),
          100: fromVar('--c-primary-100'),
          200: fromVar('--c-primary-200'),
          300: fromVar('--c-primary-300'),
          400: fromVar('--c-primary-400'),
          500: fromVar('--c-primary-500'),
          600: fromVar('--c-primary-600'),
          700: fromVar('--c-primary-700'),
          800: fromVar('--c-primary-800'),
          900: fromVar('--c-primary-900'),
          950: fromVar('--c-primary-950'),
        },
        accent: {
          50: fromVar('--c-accent-50'),
          100: fromVar('--c-accent-100'),
          200: fromVar('--c-accent-200'),
          300: fromVar('--c-accent-300'),
          400: fromVar('--c-accent-400'),
          500: fromVar('--c-accent-500'),
          600: fromVar('--c-accent-600'),
          700: fromVar('--c-accent-700'),
          800: fromVar('--c-accent-800'),
          900: fromVar('--c-accent-900'),
        },
        // Two more independent roles, same mechanism: `header` styles the
        // top bar / sidebar brand mark, `nav` styles navigation link
        // hover/active state — kept separate from primary/accent so a
        // user can recolor "the buttons" without also recoloring "the
        // header" or vice versa.
        header: {
          50: fromVar('--c-header-50'),
          100: fromVar('--c-header-100'),
          200: fromVar('--c-header-200'),
          300: fromVar('--c-header-300'),
          400: fromVar('--c-header-400'),
          500: fromVar('--c-header-500'),
          600: fromVar('--c-header-600'),
          700: fromVar('--c-header-700'),
          800: fromVar('--c-header-800'),
          900: fromVar('--c-header-900'),
          950: fromVar('--c-header-950'),
        },
        nav: {
          50: fromVar('--c-nav-50'),
          100: fromVar('--c-nav-100'),
          200: fromVar('--c-nav-200'),
          300: fromVar('--c-nav-300'),
          400: fromVar('--c-nav-400'),
          500: fromVar('--c-nav-500'),
          600: fromVar('--c-nav-600'),
          700: fromVar('--c-nav-700'),
          800: fromVar('--c-nav-800'),
          900: fromVar('--c-nav-900'),
          950: fromVar('--c-nav-950'),
        },
      },
    },
  },
  plugins: [],
}
