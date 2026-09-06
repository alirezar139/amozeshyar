<script setup lang="ts">
definePageMeta({ layout: 'admin' })
const { request } = useApi()
const authStore = useAuthStore()

const { data: pendingCourses } = await useAsyncData('admin-overview-courses', async () => {
  const page = await request<{ count: number }>('/courses/moderation/')
  return page.count
})

const { data: pendingInstructors } = await useAsyncData('admin-overview-instructors', async () => {
  const page = await request<{ results: any[] }>('/instructors/moderation/')
  return page.results.filter((i) => i.status === 'pending_review').length
})
</script>

<template>
  <div>
    <h1 class="text-xl font-bold text-gray-900 dark:text-white">
      خوش آمدید{{ authStore.user ? '، ' + authStore.user.first_name : '' }}
    </h1>
    <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">مدیریت تاییدیه‌های پلتفرم آموزش‌یار</p>

    <div class="mt-6 grid grid-cols-1 gap-5 sm:grid-cols-2">
      <NuxtLink
        to="/admin/courses"
        class="glass group flex items-center gap-4 rounded-2xl p-6 transition hover:-translate-y-0.5 hover:shadow-lg"
      >
        <div class="glass flex h-12 w-12 shrink-0 items-center justify-center rounded-xl text-primary-700 dark:text-primary-300">
          <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
          </svg>
        </div>
        <div>
          <p class="text-sm text-gray-600 dark:text-gray-400">دوره‌های در انتظار تایید</p>
          <p class="mt-1 text-3xl font-bold text-gray-900 dark:text-white">{{ pendingCourses ?? 0 }}</p>
        </div>
      </NuxtLink>
      <NuxtLink
        to="/admin/instructors"
        class="glass group flex items-center gap-4 rounded-2xl p-6 transition hover:-translate-y-0.5 hover:shadow-lg"
      >
        <div class="glass flex h-12 w-12 shrink-0 items-center justify-center rounded-xl text-accent-700 dark:text-accent-300">
          <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M17 20h5v-2a4 4 0 00-3-3.87M9 20H4v-2a4 4 0 013-3.87m6-4.13a4 4 0 10-4-4 4 4 0 004 4zm6 0a4 4 0 10-4-4" />
          </svg>
        </div>
        <div>
          <p class="text-sm text-gray-600 dark:text-gray-400">مدرس‌های در انتظار تایید</p>
          <p class="mt-1 text-3xl font-bold text-gray-900 dark:text-white">{{ pendingInstructors ?? 0 }}</p>
        </div>
      </NuxtLink>
    </div>
  </div>
</template>
