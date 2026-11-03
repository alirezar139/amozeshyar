import type { CapacitorConfig } from '@capacitor/cli'

// One build per instructor site: the app opens that site directly, so
// every change to the website reaches the app without a new release.
// SITE_URL is read when `cap sync` runs; the Android package id and name
// are passed to Gradle instead (see android/app/build.gradle).
const siteUrl = process.env.SITE_URL ?? 'https://modaresyar-org.site'

const config: CapacitorConfig = {
  appId: 'site.modaresyar.app',
  appName: 'مدرس‌یار',
  // Only shown when the site can't load (offline page); see www/index.html.
  webDir: 'www',
  server: {
    url: siteUrl,
    // Payment must stay inside the app so the buyer returns to the site
    // signed in. Any other host opens in the phone's browser.
    allowNavigation: ['*.zarinpal.com', '*.shaparak.ir'],
    errorPath: 'index.html',
  },
  plugins: {
    SplashScreen: {
      launchShowDuration: 1500,
      backgroundColor: '#0f172a',
      showSpinner: false,
    },
  },
}

export default config
