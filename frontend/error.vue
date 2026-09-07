<script setup lang="ts">
const props = defineProps<{
  error: { statusCode: number; statusMessage?: string; message?: string; stack?: string }
}>()

// Dev-only: the whole point of a friendly "something went wrong" screen
// is to hide this from real users, but while actively debugging a hard-
// to-reproduce crash, reading the actual message/stack here (instead of
// having to separately open DevTools) is the fastest way to diagnose it.
const showDetails = import.meta.dev

const is404 = computed(() => props.error.statusCode === 404)

const title = computed(() => (is404.value ? 'صفحه پیدا نشد' : 'مشکلی پیش آمد'))
const description = computed(() =>
  is404.value
    ? 'صفحه‌ای که دنبالش بودید وجود نداره یا جابه‌جا شده.'
    : 'یه خطای غیرمنتظره رخ داد. تیم فنی از این موضوع مطلع شد.'
)

function goHome() {
  clearError({ redirect: '/' })
}
</script>

<template>
  <div class="flex min-h-screen items-center justify-center px-4">
    <LayoutAmbientBackground />
    <div class="glass relative z-10 w-full max-w-md rounded-2xl p-8 text-center">
      <p class="text-6xl font-extrabold text-primary-600">{{ error.statusCode }}</p>
      <h1 class="mt-4 text-xl font-bold text-gray-900 dark:text-white">{{ title }}</h1>
      <p class="mt-2 text-sm text-gray-600 dark:text-gray-300">{{ description }}</p>

      <details v-if="showDetails && error.message" class="mt-4 text-start" open>
        <summary class="cursor-pointer text-xs font-medium text-red-600 dark:text-red-400">
          جزئیات خطا (فقط حالت توسعه)
        </summary>
        <p class="mt-2 whitespace-pre-wrap break-words rounded-md bg-black/10 p-3 text-xs text-gray-800 dark:bg-white/5 dark:text-gray-200">{{ error.message }}</p>
        <pre v-if="error.stack" class="mt-2 max-h-64 overflow-auto whitespace-pre-wrap break-words rounded-md bg-black/10 p-3 text-[10px] leading-relaxed text-gray-600 dark:bg-white/5 dark:text-gray-400">{{ error.stack }}</pre>
      </details>

      <button
        class="mt-6 rounded-md bg-primary-600 px-6 py-2 text-sm font-semibold text-white hover:bg-primary-500"
        @click="goHome"
      >
        بازگشت به صفحه اصلی
      </button>
    </div>
  </div>
</template>
