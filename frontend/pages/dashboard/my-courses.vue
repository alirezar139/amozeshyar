<script setup lang="ts">
definePageMeta({ layout: 'dashboard' })
const { request } = useApi()

const { data: enrollments, pending } = await useAsyncData('my-enrollments', async () => {
  const page = await request<{ results: any[] }>('/enrollments/')
  return page.results
})

// In-progress first, then not started, then finished.
const sorted = computed(() =>
  [...(enrollments.value ?? [])].sort((a, b) => rank(a) - rank(b)),
)
function rank(e: any) {
  const p = e.progress.percent
  return p === 100 ? 2 : p > 0 ? 0 : 1
}
</script>

<template>
  <div>
    <h1 class="text-xl font-bold text-gray-900 dark:text-white">دوره‌های من</h1>
    <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">روی هر دوره بزنید تا وارد کلاس درسش شوید.</p>

    <div v-if="pending" class="mt-6 text-gray-500">در حال بارگذاری...</div>

    <div v-else-if="!enrollments?.length" class="glass mt-6 rounded-2xl px-6 py-12 text-center">
      <p class="font-semibold text-gray-800 dark:text-gray-100">هنوز در دوره‌ای ثبت‌نام نکرده‌اید</p>
      <NuxtLink to="/courses" class="mt-4 inline-block rounded-xl bg-primary-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-primary-500">
        دیدن دوره‌ها
      </NuxtLink>
    </div>

    <div v-else data-tour="my-courses-grid" class="mt-6 grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">
      <NuxtLink
        v-for="e in sorted"
        :key="e.id"
        :to="`/dashboard/courses/${e.course.slug}`"
        class="glass group flex flex-col overflow-hidden rounded-2xl transition hover:-translate-y-1 hover:shadow-xl"
      >
        <div class="relative aspect-video overflow-hidden bg-gradient-to-br from-primary-500/20 to-accent-500/20">
          <img
            v-if="e.course.cover_image"
            :src="e.course.cover_image"
            :alt="e.course.title"
            class="h-full w-full object-cover transition duration-500 group-hover:scale-105"
            loading="lazy"
          >
          <span
            v-if="e.progress.percent === 100"
            class="absolute start-3 top-3 flex items-center gap-1 rounded-full bg-emerald-500 px-2.5 py-0.5 text-[11px] font-semibold text-white"
          >
            <svg class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" /></svg>
            تمام شد
          </span>
          <span class="absolute inset-0 flex items-center justify-center bg-black/0 opacity-0 transition group-hover:bg-black/25 group-hover:opacity-100">
            <span class="flex h-12 w-12 items-center justify-center rounded-full bg-white/90 shadow-lg">
              <svg class="h-5 w-5 text-primary-700" fill="currentColor" viewBox="0 0 20 20"><path d="M6 4l10 6-10 6V4z" /></svg>
            </span>
          </span>
        </div>
        <div class="flex flex-1 flex-col p-5">
          <p v-if="e.course.category_name" class="text-xs text-gray-500 dark:text-gray-400">{{ e.course.category_name }}</p>
          <h2 class="mt-1 line-clamp-2 font-bold text-gray-900 dark:text-white">{{ e.course.title }}</h2>
          <div class="mt-auto pt-4">
            <div class="flex items-center justify-between text-xs text-gray-600 dark:text-gray-400">
              <span>{{ e.progress.completed_lessons.toLocaleString('fa-IR') }} از {{ e.progress.total_lessons.toLocaleString('fa-IR') }} جلسه</span>
              <span class="font-bold text-gray-900 dark:text-white">{{ e.progress.percent.toLocaleString('fa-IR') }}٪</span>
            </div>
            <div class="mt-1.5 h-2 overflow-hidden rounded-full bg-black/5 dark:bg-white/10">
              <div
                :class="['h-full rounded-full transition-[width] duration-700', e.progress.percent === 100 ? 'bg-emerald-500' : 'bg-gradient-to-l from-primary-500 to-accent-500']"
                :style="{ width: `${e.progress.percent}%` }"
              />
            </div>
            <p class="mt-3 text-sm font-semibold text-primary-600 dark:text-primary-400">
              {{ e.progress.percent === 0 ? 'شروع دوره ←' : e.progress.percent === 100 ? 'مرور دوره ←' : 'ادامه ←' }}
            </p>
          </div>
        </div>
      </NuxtLink>
    </div>
  </div>
</template>
