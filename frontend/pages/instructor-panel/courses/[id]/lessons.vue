<script setup lang="ts">
definePageMeta({ layout: 'instructor' })
const route = useRoute()
const courseId = Number(route.params.id)
const { request } = useApi()
const config = useRuntimeConfig()
const authStore = useAuthStore()

const { data: lessons, refresh } = await useAsyncData(`course-${courseId}-lessons`, async () => {
  const page = await request<{ results: any[] }>('/lessons/')
  return page.results.filter((l) => l.course === courseId).sort((a, b) => a.order - b.order)
})

const statusLabels: Record<string, string> = {
  uploading: 'در حال آپلود',
  processing: 'در حال پردازش',
  ready: 'آماده‌ی پخش',
  failed: 'خطا در پردازش',
}

const newTitle = ref('')
const creatingLesson = ref(false)
const createError = ref('')

async function addLesson() {
  createError.value = ''
  creatingLesson.value = true
  try {
    const nextOrder = (lessons.value?.length ?? 0) + 1
    await request('/lessons/', {
      method: 'POST',
      body: { course: courseId, title: newTitle.value, order: nextOrder, is_free_preview: nextOrder === 1 },
    })
    newTitle.value = ''
    await refresh()
  } catch (err) {
    createError.value = getErrorMessage(err, 'ثبت سرفصل ناموفق بود.')
  } finally {
    creatingLesson.value = false
  }
}

const uploadingLessonId = ref<number | null>(null)
const uploadError = ref('')

async function onFileSelected(lessonId: number, event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return

  uploadError.value = ''
  uploadingLessonId.value = lessonId
  try {
    const formData = new FormData()
    formData.append('lesson', String(lessonId))
    formData.append('file', file)

    const headers = new Headers()
    if (authStore.accessToken) headers.set('Authorization', `Bearer ${authStore.accessToken}`)

    await $fetch(`${config.public.apiBase}/videos/upload/`, {
      method: 'POST',
      body: formData,
      headers,
      credentials: 'include',
    })
    await refresh()
    startPolling()
  } catch (err) {
    uploadError.value = getErrorMessage(err, 'آپلود ویدیو ناموفق بود.')
  } finally {
    uploadingLessonId.value = null
  }
}

let pollTimer: ReturnType<typeof setInterval> | null = null
function startPolling() {
  if (pollTimer) return
  pollTimer = setInterval(async () => {
    await refresh()
    const stillProcessing = lessons.value?.some((l) => ['uploading', 'processing'].includes(l.video_status))
    if (!stillProcessing && pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }, 4000)
}

onMounted(() => {
  if (lessons.value?.some((l) => ['uploading', 'processing'].includes(l.video_status))) {
    startPolling()
  }
})
onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <div>
    <h1 class="text-xl font-bold text-gray-900 dark:text-white">مدیریت سرفصل‌ها و ویدیو</h1>
    <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
      بعد از آپلود، ویدیو به‌صورت خودکار پردازش می‌شود و یک کلیپ پیش‌نمایش رایگان از آن ساخته می‌شود.
    </p>

    <div class="glass mt-6 rounded-2xl p-6">
      <h2 class="font-semibold text-gray-900 dark:text-white">افزودن سرفصل جدید</h2>
      <form class="mt-3 flex flex-col gap-3 sm:flex-row" @submit.prevent="addLesson">
        <input
          v-model="newTitle"
          required
          placeholder="عنوان سرفصل، مثلاً «جلسه‌ی اول: آشنایی با پایتون»"
          class="glass flex-1 rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white"
        >
        <button
          type="submit"
          :disabled="creatingLesson"
          class="rounded-md bg-primary-600 px-5 py-2 text-sm font-semibold text-white hover:bg-primary-500 disabled:opacity-50"
        >
          {{ creatingLesson ? 'در حال ثبت...' : 'افزودن' }}
        </button>
      </form>
      <p v-if="createError" class="mt-2 text-sm text-red-600">{{ createError }}</p>
    </div>

    <p v-if="uploadError" class="mt-4 text-sm text-red-600">{{ uploadError }}</p>

    <div class="mt-6 space-y-3">
      <div v-for="lesson in lessons" :key="lesson.id" class="glass flex flex-wrap items-center justify-between gap-3 rounded-xl p-4">
        <div>
          <p class="font-medium text-gray-900 dark:text-white">{{ lesson.order }}. {{ lesson.title }}</p>
          <span v-if="lesson.is_free_preview" class="text-xs font-medium text-emerald-700 dark:text-emerald-400">پیش‌نمایش رایگان کامل</span>
        </div>

        <div class="flex items-center gap-3">
          <span
            v-if="lesson.has_video"
            class="rounded-full px-3 py-1 text-xs font-medium"
            :class="{
              'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300': ['uploading', 'processing'].includes(lesson.video_status),
              'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300': lesson.video_status === 'ready',
              'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300': lesson.video_status === 'failed',
            }"
          >
            {{ statusLabels[lesson.video_status] }}
          </span>
          <label v-else class="cursor-pointer rounded-md bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-500">
            {{ uploadingLessonId === lesson.id ? 'در حال آپلود...' : 'آپلود ویدیو' }}
            <input
              type="file"
              accept="video/*"
              class="hidden"
              :disabled="uploadingLessonId === lesson.id"
              @change="onFileSelected(lesson.id, $event)"
            >
          </label>
        </div>
      </div>
      <p v-if="lessons && lessons.length === 0" class="text-gray-600 dark:text-gray-400">هنوز سرفصلی ثبت نشده است.</p>
    </div>
  </div>
</template>
