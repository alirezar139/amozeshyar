<script setup lang="ts">
definePageMeta({ layout: 'admin' })
const { request } = useApi()

const { data: courses, pending, refresh } = await useAsyncData('admin-courses', async () => {
  const page = await request<{ results: any[] }>('/courses/manage/')
  return page.results
})

// Leftover pending_review/rejected rows from the old approval flow read as
// "not live", same as a draft — publishing one puts it on the site.
const statusLabels: Record<string, string> = {
  draft: 'پیش‌نویس',
  pending_review: 'پیش‌نویس',
  published: 'منتشرشده',
  rejected: 'پیش‌نویس',
}

const busyId = ref<number | null>(null)
const actionError = ref('')

async function setStatus(id: number, status: 'published' | 'draft') {
  busyId.value = id
  actionError.value = ''
  try {
    await request(`/courses/manage/${id}/`, { method: 'PATCH', body: { status } })
    await refresh()
  } catch (err) {
    actionError.value = getErrorMessage(err, 'تغییر وضعیت دوره ناموفق بود.')
  } finally {
    busyId.value = null
  }
}
</script>

<template>
  <div>
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-bold text-gray-900 dark:text-white">دوره‌ها</h1>
      <NuxtLink
        to="/admin/courses/create"
        data-tour="new-course-btn"
        class="rounded-md bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-500"
      >
        دوره‌ی جدید
      </NuxtLink>
    </div>
    <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
      دوره‌های منتشرشده در سایت نمایش داده می‌شوند و پیش‌نویس‌ها تنها در همین بخش قابل مشاهده‌اند.
    </p>
    <p v-if="actionError" class="mt-3 text-sm text-red-600">{{ actionError }}</p>

    <div v-if="pending" class="mt-6 text-gray-500">در حال بارگذاری...</div>
    <div v-else data-tour="all-courses-table" class="glass mt-6 overflow-x-auto rounded-xl p-2">
      <table class="w-full min-w-[560px] text-sm">
        <thead>
          <tr class="text-start text-gray-600 dark:text-gray-400">
            <th class="px-3 py-2">عنوان</th>
            <th class="px-3 py-2">قیمت</th>
            <th class="px-3 py-2">وضعیت</th>
            <th class="px-3 py-2" />
          </tr>
        </thead>
        <tbody>
          <tr v-for="course in courses" :key="course.id" class="border-t border-white/30 dark:border-white/10">
            <td class="px-3 py-2 text-gray-900 dark:text-white">
              <NuxtLink :to="`/admin/courses/${course.id}/lessons`" class="flex items-center gap-3">
                <img v-if="course.cover_image" :src="course.cover_image" alt="" class="aspect-video w-16 shrink-0 rounded-md object-cover">
                <span v-else class="flex aspect-video w-16 shrink-0 items-center justify-center rounded-md bg-gradient-to-br from-primary-700 to-primary-950 text-[10px] text-white/80">بدون عکس</span>
                <span class="min-w-0">{{ course.title }}</span>
              </NuxtLink>
            </td>
            <td class="px-3 py-2 text-gray-600 dark:text-gray-400">
              {{ Number(course.price) === 0 ? 'رایگان' : `${Number(course.price).toLocaleString('fa-IR')} تومان` }}
            </td>
            <td class="px-3 py-2">
              <span :class="course.status === 'published' ? 'text-emerald-600 dark:text-emerald-400' : 'text-gray-500 dark:text-gray-400'">
                {{ statusLabels[course.status] }}
              </span>
            </td>
            <td class="px-3 py-2">
              <div class="flex flex-wrap items-center justify-end gap-3">
                <NuxtLink :to="`/admin/courses/${course.id}/lessons`" class="text-sm font-medium text-primary-600 hover:underline dark:text-primary-400">
                  عکس، سرفصل‌ها، ویدیوها و جلسه‌ها
                </NuxtLink>
                <button
                  type="button"
                  :disabled="busyId === course.id"
                  class="glass rounded-md px-3 py-1 text-xs text-gray-700 disabled:opacity-50 dark:text-gray-200"
                  @click="setStatus(course.id, course.status === 'published' ? 'draft' : 'published')"
                >
                  {{ course.status === 'published' ? 'برگرداندن به پیش‌نویس' : 'انتشار' }}
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="courses && courses.length === 0" class="p-4 text-gray-600 dark:text-gray-400">هنوز دوره‌ای ثبت نشده است.</p>
    </div>

    <CourseCategoryPhotos class="mt-8" />
  </div>
</template>
