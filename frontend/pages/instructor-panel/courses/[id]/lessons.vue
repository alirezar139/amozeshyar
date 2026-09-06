<script setup lang="ts">
definePageMeta({ layout: 'instructor' })
const route = useRoute()
const courseId = Number(route.params.id)
</script>

<template>
  <div>
    <h1 class="text-xl font-bold text-gray-900 dark:text-white">مدیریت سرفصل‌ها و ویدیو</h1>
    <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
      بعد از آپلود، ویدیو به‌صورت خودکار پردازش می‌شود و یک کلیپ پیش‌نمایش رایگان از آن ساخته می‌شود.
    </p>
    <CourseLessonManager :course-id="courseId" class="mt-6" />

    <h2 class="mt-10 text-lg font-bold text-gray-900 dark:text-white">زمان‌بندی کلاس‌های زنده</h2>
    <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
      برای جلساتی که به‌صورت زنده برگزار می‌شوند (نه ویدیوی ضبط‌شده)؛ دانشجوهای ثبت‌نام‌شده آن را در تقویم خودشان می‌بینند.
    </p>
    <CourseClassSessionManager :course-id="courseId" class="mt-6" />
  </div>
</template>
