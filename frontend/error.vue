<script setup lang="ts">
const props = defineProps<{
  error: { statusCode: number; statusMessage?: string; message?: string }
}>()

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
      <button
        class="mt-6 rounded-md bg-primary-600 px-6 py-2 text-sm font-semibold text-white hover:bg-primary-500"
        @click="goHome"
      >
        بازگشت به صفحه اصلی
      </button>
    </div>
  </div>
</template>
