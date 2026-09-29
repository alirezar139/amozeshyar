<script setup lang="ts">
definePageMeta({ layout: 'admin' })
const { request } = useApi()
const authStore = useAuthStore()

const coursesAsync = useAsyncData('admin-overview-courses', async () => {
  const page = await request<{ results: { status: string }[] }>('/courses/manage/')
  return page.results
})
const sessionsAsync = useAsyncData('admin-overview-sessions', async () => {
  const page = await request<{ results: { starts_at: string }[] }>('/class-sessions/')
  const now = Date.now()
  return page.results.filter((s) => new Date(s.starts_at).getTime() >= now).length
})
await Promise.all([coursesAsync, sessionsAsync])
const { data: courses } = coursesAsync
const { data: upcomingSessions } = sessionsAsync

const publishedCount = computed(() => (courses.value ?? []).filter((c) => c.status === 'published').length)
const draftCount = computed(() => (courses.value ?? []).length - publishedCount.value)
</script>

<template>
  <div>
    <h1 class="text-xl font-bold text-gray-900 dark:text-white">
      خوش آمدید{{ authStore.user ? '، ' + authStore.user.first_name : '' }}
    </h1>
    <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">مدیریت دوره‌ها و دانشجوهای سایت شما</p>

    <div class="mt-6 grid grid-cols-1 gap-5 sm:grid-cols-2">
      <NuxtLink
        to="/admin/courses"
        data-tour="admin-courses-stat"
        class="glass group flex items-center gap-4 rounded-2xl p-6 transition hover:-translate-y-0.5 hover:shadow-lg"
      >
        <div class="glass flex h-12 w-12 shrink-0 items-center justify-center rounded-xl text-primary-700 dark:text-primary-300">
          <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
          </svg>
        </div>
        <div>
          <p class="text-sm text-gray-600 dark:text-gray-400">دوره‌های منتشرشده</p>
          <p class="mt-1 text-3xl font-bold text-gray-900 dark:text-white">{{ publishedCount }}</p>
          <p v-if="draftCount" class="mt-1 text-xs text-gray-500 dark:text-gray-400">{{ draftCount }} پیش‌نویس</p>
        </div>
      </NuxtLink>
      <NuxtLink
        to="/admin/calendar"
        data-tour="admin-sessions-stat"
        class="glass group flex items-center gap-4 rounded-2xl p-6 transition hover:-translate-y-0.5 hover:shadow-lg"
      >
        <div class="glass flex h-12 w-12 shrink-0 items-center justify-center rounded-xl text-accent-700 dark:text-accent-300">
          <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
        </div>
        <div>
          <p class="text-sm text-gray-600 dark:text-gray-400">دوره‌های آنلاین پیش رو</p>
          <p class="mt-1 text-3xl font-bold text-gray-900 dark:text-white">{{ upcomingSessions ?? 0 }}</p>
        </div>
      </NuxtLink>
    </div>
  </div>
</template>
