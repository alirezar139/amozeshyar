<script setup lang="ts">
// Admin course editor: the course's lessons, each with its video and files
// (see CourseLessonCard). Warns before leaving while anything is uploading.
const props = defineProps<{ courseId: number }>()
const { request } = useApi()

const { data: lessons, refresh, pending } = await useAsyncData(`course-${props.courseId}-lessons`, () =>
  request<any[]>(`/lessons/?course=${props.courseId}`),
)

const newTitle = ref('')
const creatingLesson = ref(false)
const createError = ref('')
const moveError = ref('')

async function addLesson() {
  const title = newTitle.value.trim()
  if (!title) return
  createError.value = ''
  creatingLesson.value = true
  try {
    await request('/lessons/', {
      method: 'POST',
      body: { course: props.courseId, title, is_free_preview: !lessons.value?.length },
    })
    newTitle.value = ''
    await refresh()
  } catch (err) {
    createError.value = getErrorMessage(err, 'ثبت جلسه ناموفق بود.')
  } finally {
    creatingLesson.value = false
  }
}

async function move(lessonId: number, direction: 'up' | 'down') {
  moveError.value = ''
  try {
    lessons.value = await request<any[]>(`/lessons/${lessonId}/move/`, { method: 'POST', body: { direction } })
  } catch (err) {
    moveError.value = getErrorMessage(err, 'جابه‌جایی ناموفق بود.')
  }
}

const stats = computed(() => {
  const list = lessons.value ?? []
  return {
    lessons: list.length,
    videos: list.filter((l) => l.video_status === 'ready').length,
    files: list.reduce((n, l) => n + l.files.length, 0),
    minutes: Math.round(list.reduce((n, l) => n + (l.video_duration || 0), 0) / 60),
  }
})

// ---- keep the page open while uploads are running ----
const activeUploads = ref(0)
function onUploading(delta: number) {
  activeUploads.value = Math.max(0, activeUploads.value + delta)
}
function beforeUnload(e: BeforeUnloadEvent) {
  if (activeUploads.value) e.preventDefault()
}
onMounted(() => window.addEventListener('beforeunload', beforeUnload))
onBeforeUnmount(() => window.removeEventListener('beforeunload', beforeUnload))
onBeforeRouteLeave(() => {
  if (activeUploads.value) return confirm('آپلود هنوز تمام نشده. با ترک صفحه لغو می‌شود. مطمئنید؟')
})

// ---- poll while a video is processing ----
let pollTimer: ReturnType<typeof setInterval> | null = null
const anyProcessing = computed(() => (lessons.value ?? []).some((l) => ['uploading', 'processing'].includes(l.video_status)))
watch(
  anyProcessing,
  (processing) => {
    if (processing && !pollTimer) {
      pollTimer = setInterval(() => refresh(), 4000)
    } else if (!processing && pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  },
  { immediate: true },
)
onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <div>
    <!-- Summary + add lesson -->
    <div class="glass rounded-2xl p-5">
      <div data-tour="lesson-stats" class="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div class="rounded-xl bg-black/[0.03] px-4 py-3 dark:bg-white/5">
          <p class="text-xs text-gray-500 dark:text-gray-400">جلسه</p>
          <p class="mt-0.5 text-xl font-black text-gray-900 dark:text-white">{{ stats.lessons.toLocaleString('fa-IR') }}</p>
        </div>
        <div class="rounded-xl bg-black/[0.03] px-4 py-3 dark:bg-white/5">
          <p class="text-xs text-gray-500 dark:text-gray-400">ویدیوی آماده</p>
          <p class="mt-0.5 text-xl font-black text-gray-900 dark:text-white">{{ stats.videos.toLocaleString('fa-IR') }}</p>
        </div>
        <div class="rounded-xl bg-black/[0.03] px-4 py-3 dark:bg-white/5">
          <p class="text-xs text-gray-500 dark:text-gray-400">فایل</p>
          <p class="mt-0.5 text-xl font-black text-gray-900 dark:text-white">{{ stats.files.toLocaleString('fa-IR') }}</p>
        </div>
        <div class="rounded-xl bg-black/[0.03] px-4 py-3 dark:bg-white/5">
          <p class="text-xs text-gray-500 dark:text-gray-400">مدت کل</p>
          <p class="mt-0.5 text-xl font-black text-gray-900 dark:text-white">{{ stats.minutes.toLocaleString('fa-IR') }} <span class="text-xs font-medium">دقیقه</span></p>
        </div>
      </div>

      <form data-tour="lesson-add" class="mt-5 flex flex-col gap-3 sm:flex-row" @submit.prevent="addLesson">
        <input
          v-model="newTitle"
          required
          placeholder="عنوان جلسه‌ی جدید، مثلاً «جلسه‌ی اول: آشنایی با پایتون»"
          class="glass flex-1 rounded-xl px-4 py-2.5 text-sm text-gray-900 outline-none focus:ring-2 focus:ring-primary-500/50 dark:text-white"
        >
        <button
          type="submit"
          :disabled="creatingLesson || !newTitle.trim()"
          class="rounded-xl bg-primary-600 px-6 py-2.5 text-sm font-semibold text-white shadow-lg shadow-primary-600/25 transition hover:bg-primary-500 disabled:opacity-50 disabled:shadow-none"
        >
          {{ creatingLesson ? 'در حال ثبت...' : '+ افزودن جلسه' }}
        </button>
      </form>
      <p v-if="createError" class="mt-2 text-sm text-red-600">{{ createError }}</p>
    </div>

    <div
      v-if="activeUploads"
      class="sticky top-3 z-20 mt-4 flex items-center gap-3 rounded-xl bg-primary-600 px-4 py-2.5 text-sm text-white shadow-lg"
    >
      <span class="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
      {{ activeUploads.toLocaleString('fa-IR') }} آپلود در جریان است — تا پایان، این صفحه را نبندید.
    </div>
    <p v-if="moveError" class="mt-3 text-sm text-red-600">{{ moveError }}</p>

    <div v-if="pending && !lessons" class="mt-6 text-gray-500">در حال بارگذاری...</div>
    <TransitionGroup v-else tag="div" name="lesson" class="mt-5 space-y-4">
      <CourseLessonCard
        v-for="(lesson, i) in lessons"
        :key="lesson.id"
        :lesson="lesson"
        :is-first="i === 0"
        :is-last="i === (lessons?.length ?? 0) - 1"
        @changed="refresh"
        @move="move(lesson.id, $event)"
        @uploading="onUploading"
      />
    </TransitionGroup>

    <div v-if="lessons && !lessons.length" class="glass mt-5 rounded-2xl px-6 py-12 text-center">
      <p class="font-semibold text-gray-800 dark:text-gray-100">هنوز جلسه‌ای ندارید</p>
      <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
        از بالا اولین جلسه را اضافه کنید؛ بعد ویدیو و فایل‌هایش را همین‌جا آپلود کنید. جلسه‌ی اول به‌صورت پیش‌فرض برای همه رایگان است.
      </p>
    </div>
  </div>
</template>

<style scoped>
.lesson-move {
  transition: transform 0.35s cubic-bezier(0.22, 1, 0.36, 1);
}
.lesson-enter-active,
.lesson-leave-active {
  transition: all 0.25s ease;
}
.lesson-enter-from,
.lesson-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>
