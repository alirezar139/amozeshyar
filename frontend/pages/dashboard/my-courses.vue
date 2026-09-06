<script setup lang="ts">
definePageMeta({ layout: 'dashboard' })
const { request } = useApi()

const { data: enrollments, pending } = await useAsyncData('my-enrollments', async () => {
  const page = await request<{ results: any[] }>('/enrollments/')
  return page.results
})
</script>

<template>
  <div>
    <h1 class="text-xl font-bold text-gray-900 dark:text-white">دوره‌های من</h1>
    <div v-if="pending" class="mt-6 text-gray-500">در حال بارگذاری...</div>
    <div v-else class="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <CourseCard v-for="e in enrollments" :key="e.id" :course="e.course" />
      <p v-if="enrollments && enrollments.length === 0" class="text-gray-500">هنوز در دوره‌ای ثبت‌نام نکرده‌اید.</p>
    </div>
  </div>
</template>
