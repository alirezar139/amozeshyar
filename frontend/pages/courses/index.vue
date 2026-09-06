<script setup lang="ts">
const { request } = useApi()

useSeoMeta({
  title: 'دوره‌ها | آموزش‌یار',
  description: 'مرور همه‌ی دوره‌های آموزشی منتشرشده روی آموزش‌یار.',
})

const { data: courses, pending, error } = await useAsyncData('courses-list', async () => {
  const page = await request<{ results: any[] }>('/courses/')
  return page.results
})
</script>

<template>
  <div class="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
    <h1 class="text-2xl font-bold text-gray-900 dark:text-white">دوره‌های آموزشی</h1>

    <div v-if="pending" class="mt-8 text-center text-gray-500">در حال بارگذاری...</div>
    <div v-else-if="error" class="mt-8 text-center text-red-600">خطا در دریافت دوره‌ها.</div>
    <div
      v-else
      class="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
    >
      <CourseCard v-for="course in courses" :key="course.slug" :course="course" />
      <p v-if="courses && courses.length === 0" class="col-span-full text-center text-gray-500">
        دوره‌ای برای نمایش وجود ندارد.
      </p>
    </div>
  </div>
</template>
