<script setup lang="ts">
// iPhone/iPad Safari never offers to install a site, so we explain how:
// Share → «Add to Home Screen». Shown once in a while to visitors who
// haven't installed it yet; closing it hides it for a month.
const DISMISS_KEY = 'ios-install-hint-dismissed'
const HIDE_FOR_MS = 30 * 24 * 60 * 60 * 1000

const route = useRoute()
const { siteName } = useSite()
const visible = ref(false)

onMounted(() => {
  const ua = navigator.userAgent
  // iPadOS reports itself as a Mac; touch support gives it away.
  const isIos = /iPhone|iPad|iPod/.test(ua) || (ua.includes('Macintosh') && navigator.maxTouchPoints > 1)
  const installed = (navigator as any).standalone === true || matchMedia('(display-mode: standalone)').matches
  if (!isIos || installed || route.path.startsWith('/admin')) return
  try {
    const dismissedAt = Number(localStorage.getItem(DISMISS_KEY) || 0)
    if (Date.now() - dismissedAt < HIDE_FOR_MS) return
  } catch {
    // Private mode: just show it.
  }
  setTimeout(() => (visible.value = true), 15000)
})

function dismiss() {
  visible.value = false
  try {
    localStorage.setItem(DISMISS_KEY, String(Date.now()))
  } catch {
    // Nothing to remember it in; it'll show again next visit.
  }
}
</script>

<template>
  <Transition
    enter-from-class="translate-y-6 opacity-0"
    enter-active-class="transition duration-300"
    leave-to-class="translate-y-6 opacity-0"
    leave-active-class="transition duration-200"
  >
    <div
      v-if="visible"
      role="dialog"
      aria-label="نصب اپ روی آیفون"
      class="glass fixed inset-x-4 bottom-28 z-[90] mx-auto max-w-sm rounded-2xl p-4 shadow-xl"
    >
      <button
        type="button"
        aria-label="بستن"
        class="absolute end-2 top-2 rounded-full p-1.5 text-gray-500 hover:bg-black/5 dark:text-gray-400 dark:hover:bg-white/10"
        @click="dismiss"
      >
        <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
      </button>
      <div class="flex items-start gap-3 pe-6">
        <img src="/icons/icon-192.png" alt="" class="h-12 w-12 shrink-0 rounded-xl">
        <div class="text-sm">
          <p class="font-bold text-gray-900 dark:text-white">{{ siteName }} را روی گوشی نصب کنید</p>
          <p class="mt-1 leading-6 text-gray-600 dark:text-gray-300">
            در Safari دکمه‌ی اشتراک‌گذاری
            <svg class="inline h-4 w-4 align-text-bottom text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" aria-label="Share"><path stroke-linecap="round" stroke-linejoin="round" d="M12 3v12M8 7l4-4 4 4M5 12v7a2 2 0 002 2h10a2 2 0 002-2v-7" /></svg>
            را بزنید و «Add to Home Screen» را انتخاب کنید.
          </p>
        </div>
      </div>
    </div>
  </Transition>
</template>
