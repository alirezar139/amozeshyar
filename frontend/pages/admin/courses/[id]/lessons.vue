<script setup lang="ts">
definePageMeta({ layout: 'admin' })
const route = useRoute()
const courseId = Number(route.params.id)
const justCreated = route.query.new === '1'
const { request } = useApi()

const { data: course } = await useAsyncData(`admin-course-${courseId}`, () =>
  request<{ title: string; slug: string; status: string; cover_image: string | null }>(`/courses/manage/${courseId}/`).catch(() => null),
)
</script>

<template>
  <div class="max-w-5xl">
    <NuxtLink to="/admin/courses" class="text-sm text-primary-600 hover:underline dark:text-primary-400">→ همه‌ی دوره‌ها</NuxtLink>
    <div class="mt-2 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 class="text-2xl font-extrabold text-gray-900 dark:text-white">{{ course?.title ?? 'محتوای دوره' }}</h1>
        <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
          هر جلسه ویدیو و فایل‌های خودش را دارد: جلسه را اضافه کنید، بعد ویدیو را روی کارت همان جلسه آپلود کنید. ویدیو بعد از آپلود خودکار پردازش می‌شود و یک کلیپ پیش‌نمایش رایگان از آن ساخته می‌شود.
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

    <div v-if="justCreated" class="mt-5 rounded-2xl bg-emerald-500/10 px-5 py-4 text-sm text-emerald-800 ring-1 ring-emerald-500/25 dark:text-emerald-200">
      <p class="font-semibold">دوره ساخته و منتشر شد.</p>
      <p class="mt-1">قدم بعد: پایین همین صفحه اولین جلسه را اضافه کنید. روی کارت هر جلسه جای آپلود ویدیو و فایل‌های همان جلسه هست.</p>
    </div>

    <CourseLessonManager :course-id="courseId" data-tour="lesson-manager" class="mt-6" />

    <CourseCoverEditor
      v-if="course"
      :course-id="courseId"
      :src="course.cover_image"
      class="mt-12"
      @changed="(src) => course && (course.cover_image = src)"
    />

    <h2 class="mt-12 text-lg font-bold text-gray-900 dark:text-white">زمان‌بندی دوره‌های آنلاین</h2>
    <CourseClassSessionManager :course-id="courseId" data-tour="class-session-manager" class="mt-4" />
  </div>
</template>
