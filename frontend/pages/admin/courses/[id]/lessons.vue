<script setup lang="ts">
definePageMeta({ layout: 'admin' })
const route = useRoute()
const courseId = Number(route.params.id)
const { request } = useApi()

const { data: course } = await useAsyncData(`admin-course-${courseId}`, () =>
  request<{ title: string; slug: string; status: string }>(`/courses/manage/${courseId}/`).catch(() => null),
)
</script>

<template>
  <div class="max-w-5xl">
    <NuxtLink to="/admin/courses" class="text-sm text-primary-600 hover:underline dark:text-primary-400">→ همه‌ی دوره‌ها</NuxtLink>
    <div class="mt-2 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 class="text-2xl font-extrabold text-gray-900 dark:text-white">{{ course?.title ?? 'محتوای دوره' }}</h1>
        <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
          جلسه‌ها، ویدیوها و فایل‌های دوره. ویدیو بعد از آپلود خودکار پردازش می‌شود و یک کلیپ پیش‌نمایش رایگان از آن ساخته می‌شود.
        </p>
      </div>
      <NuxtLink
        v-if="course?.slug"
        :to="`/courses/${course.slug}`"
        target="_blank"
        class="glass shrink-0 rounded-xl px-4 py-2 text-sm font-medium text-gray-800 dark:text-gray-100"
      >
        دیدن صفحه‌ی دوره ↗
      </NuxtLink>
    </div>

    <CourseLessonManager :course-id="courseId" data-tour="lesson-manager" class="mt-6" />

    <h2 class="mt-12 text-lg font-bold text-gray-900 dark:text-white">زمان‌بندی دوره‌های آنلاین</h2>
    <CourseClassSessionManager :course-id="courseId" data-tour="class-session-manager" class="mt-4" />
  </div>
</template>
