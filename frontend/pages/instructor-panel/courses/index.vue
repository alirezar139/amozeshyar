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
        data-tour="new-course"
        class="rounded-md bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-500"
      >
        دوره‌ی جدید
      </NuxtLink>
    </div>

    <div v-if="pending" class="mt-6 text-gray-500">در حال بارگذاری...</div>
    <div v-else class="glass mt-6 overflow-x-auto rounded-xl p-2">
      <table class="w-full min-w-[560px] text-sm">
        <thead>
          <tr class="text-start text-gray-600 dark:text-gray-400">
            <th class="px-3 py-2">عنوان</th>
            <th class="px-3 py-2">وضعیت</th>
            <th class="px-3 py-2">قیمت</th>
            <th class="px-3 py-2" />
          </tr>
        </thead>
        <tbody>
          <tr v-for="course in courses" :key="course.id" class="border-t border-white/30 dark:border-white/10">
            <td class="px-3 py-2 text-gray-900 dark:text-white">{{ course.title }}</td>
            <td class="px-3 py-2 text-gray-600 dark:text-gray-400">{{ statusLabels[course.status] }}</td>
            <td class="px-3 py-2 text-gray-600 dark:text-gray-400">{{ Number(course.price).toLocaleString('fa-IR') }}</td>
            <td class="px-3 py-2">
              <NuxtLink :to="`/instructor-panel/courses/${course.id}/lessons`" data-tour="manage-lessons-link" class="text-sm font-medium text-primary-600 hover:underline dark:text-primary-400">
                مدیریت سرفصل‌ها و ویدیو
              </NuxtLink>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="courses && courses.length === 0" class="p-4 text-gray-600 dark:text-gray-400">هنوز دوره‌ای نساخته‌اید.</p>
    </div>
  </div>
</template>
