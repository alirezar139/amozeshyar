<script setup lang="ts">
definePageMeta({ layout: 'instructor' })
const { request } = useApi()

const { data: courses, pending } = await useAsyncData('my-instructor-courses', async () => {
  const page = await request<{ results: any[] }>('/courses/mine/')
  return page.results
})

const statusLabels: Record<string, string> = {
  draft: 'پیش‌نویس',
  pending_review: 'در انتظار تایید ادمین',
  published: 'منتشرشده',
  rejected: 'رد شده',
}
</script>

<template>
  <div>
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-bold text-gray-900 dark:text-white">دوره‌های من</h1>
      <NuxtLink
        to="/instructor-panel/courses/create"
        class="rounded-md bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-500"
      >
        دوره‌ی جدید
      </NuxtLink>
    </div>

    <div v-if="pending" class="mt-6 text-gray-500">در حال بارگذاری...</div>
    <div v-else class="mt-6 overflow-x-auto">
      <table class="w-full min-w-[500px] divide-y divide-gray-200 text-sm dark:divide-gray-800">
        <thead>
          <tr class="text-start text-gray-500 dark:text-gray-400">
            <th class="py-2">عنوان</th>
            <th class="py-2">وضعیت</th>
            <th class="py-2">قیمت</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-200 dark:divide-gray-800">
          <tr v-for="course in courses" :key="course.id">
            <td class="py-2 text-gray-900 dark:text-white">{{ course.title }}</td>
            <td class="py-2 text-gray-600 dark:text-gray-400">{{ statusLabels[course.status] }}</td>
            <td class="py-2 text-gray-600 dark:text-gray-400">{{ course.price }}</td>
          </tr>
        </tbody>
      </table>
      <p v-if="courses && courses.length === 0" class="mt-4 text-gray-500">هنوز دوره‌ای نساخته‌اید.</p>
    </div>
  </div>
</template>
