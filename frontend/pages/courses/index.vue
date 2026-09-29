<script setup lang="ts">
const { request } = useApi()
const route = useRoute()

const { siteName } = useSite()
useSeoMeta({
  title: () => `دوره‌ها | ${siteName.value}`,
  description: () => `همه‌ی دوره‌های ${siteName.value}`,
})

const categorySlug = computed(() => (route.query.category as string) || '')

const categoriesAsync = useAsyncData('courses-page-categories', async () => {
  const page = await request<{ results: any[] }>('/categories/')
  return page.results
})

const activeCategory = computed(() => categories.value?.find((c) => c.slug === categorySlug.value))

async function fetchCourses() {
  const qs = categorySlug.value ? `?category=${encodeURIComponent(categorySlug.value)}` : ''
  const page = await request<{ results: any[] }>(`/courses/${qs}`)
  return page.results
}

const coursesAsync = useAsyncData('courses-list', fetchCourses, {
  watch: [categorySlug],
})
// Independent fetches: started together, awaited as a group.
await Promise.all([categoriesAsync, coursesAsync])
const { data: categories } = categoriesAsync
const { data: courses, pending, error } = coursesAsync
</script>

<template>
  <div class="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-2xl font-bold text-gray-900 dark:text-white">
        {{ activeCategory ? `دوره‌های ${activeCategory.name}` : 'دوره‌های آموزشی' }}
      </h1>
      <NuxtLink
        v-if="categorySlug"
        to="/courses"
        class="glass rounded-md px-3 py-1.5 text-sm text-gray-700 dark:text-gray-200"
      >
        حذف فیلتر ✕
      </NuxtLink>
    </div>

    <div v-if="pending" class="mt-8 text-center text-gray-500">در حال بارگذاری...</div>
    <div v-else-if="error" class="mt-8 text-center text-red-600">خطا در دریافت دوره‌ها.</div>
    <div
      v-else
      data-tour="course-grid"
      class="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
    >
      <CourseCard v-for="course in courses" :key="course.slug" :course="course" />
      <p v-if="courses && courses.length === 0" class="col-span-full text-center text-gray-500">
        دوره‌ای برای نمایش وجود ندارد.
      </p>
    </div>
  </div>
</template>
