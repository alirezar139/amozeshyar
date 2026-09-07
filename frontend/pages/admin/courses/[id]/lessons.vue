<script setup lang="ts">
definePageMeta({ layout: 'admin' })
const route = useRoute()
const courseId = Number(route.params.id)
</script>

<template>
  <div>
    <h1 class="text-xl font-bold text-gray-900 dark:text-white">مدیریت سرفصل‌ها و ویدیو</h1>
    <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
      بعد از آپلود، ویدیو به‌صورت خودکار پردازش می‌شود و یک کلیپ پیش‌نمایش رایگان از آن ساخته می‌شود.
    </p>
    <CourseLessonManager :course-id="courseId" data-tour="lesson-manager" class="mt-6" />

    <h2 class="mt-10 text-lg font-bold text-gray-900 dark:text-white">زمان‌بندی کلاس‌های زنده</h2>
    <CourseClassSessionManager :course-id="courseId" data-tour="class-session-manager" class="mt-6" />
  </div>
</template>
