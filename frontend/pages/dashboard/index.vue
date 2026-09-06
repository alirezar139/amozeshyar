<script setup lang="ts">
definePageMeta({ layout: 'dashboard' })
const authStore = useAuthStore()
const { request } = useApi()

const { data: continueLearning } = await useAsyncData('dashboard-continue', () =>
  request<any>('/enrollments/continue/').catch(() => null)
)
</script>

<template>
  <div>
    <h1 class="text-xl font-bold text-gray-900 dark:text-white">
      خوش آمدید{{ authStore.user ? '، ' + authStore.user.first_name : '' }}
    </h1>
    <p class="mt-2 text-gray-600 dark:text-gray-400">از منوی کناری دوره‌ها و سفارش‌های خود را مدیریت کنید.</p>

    <NuxtLink
      v-if="continueLearning"
      :to="`/courses/${continueLearning.course_slug}`"
      data-tour="continue-learning"
      class="glass mt-6 flex items-center justify-between gap-4 rounded-2xl p-6 transition hover:-translate-y-0.5 hover:shadow-lg"
    >
      <div>
        <p class="text-xs font-medium text-primary-600 dark:text-primary-400">ادامه‌ی یادگیری</p>
        <p class="mt-1 font-semibold text-gray-900 dark:text-white">{{ continueLearning.course_title }}</p>
        <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">{{ continueLearning.lesson_title }}</p>
      </div>
      <span class="glass flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-primary-700 dark:text-primary-300">
        <svg class="h-5 w-5" fill="currentColor" viewBox="0 0 20 20"><path d="M6 4l10 6-10 6V4z" /></svg>
      </span>
    </NuxtLink>
  </div>
</template>
