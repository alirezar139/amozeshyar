/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './components/**/*.{vue,js,ts}',
    './layouts/**/*.vue',
    './pages/**/*.vue',
    './plugins/**/*.{js,ts}',
    './app.vue',
    './error.vue',
  ],
  darkMode: 'media',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Vazirmatn', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      colors: {
        // Deep teal — the platform's primary brand color (learning/growth),
        // used instead of Tailwind's default indigo to avoid the generic
        // "AI SaaS starter" look.
        primary: {
          50: '#eefcf7',
          100: '#d5f5ea',
          200: '#adebd8',
          300: '#74d9bd',
          400: '#3dbfa0',
          500: '#1f9f85',
          600: '#157e6c',
          700: '#146458',
          800: '#145047',
          900: '#12433c',
          950: '#06261f',
        },
        // Warm amber accent for highlights/CTAs that need to pop against
        // the cool primary palette.
        accent: {
          50: '#fff8ec',
          100: '#ffedc7',
          200: '#ffd889',
          300: '#ffbe4c',
          400: '#ffa41f',
          500: '#f98307',
          600: '#dd6202',
          700: '#b74405',
          800: '#94350c',
          900: '#7a2d0e',
        },
      },
    },
  },
  plugins: [],
}
