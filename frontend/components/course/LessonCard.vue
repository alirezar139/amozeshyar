<script setup lang="ts">
import type { UploadProgress } from '~/composables/useUpload'

// One lesson in the admin's course editor: title, free-preview flag,
// ordering, its video (upload / replace / delete, with live progress and
// processing status) and its downloadable files (multi-upload queue).
const props = defineProps<{ lesson: any; isFirst: boolean; isLast: boolean }>()
const emit = defineEmits<{ changed: []; move: [direction: 'up' | 'down']; uploading: [delta: number] }>()

const { request } = useApi()
const { upload, uploadErrorMessage } = useUpload()

const MAX_VIDEO_BYTES = 5 * 1024 ** 3
const MAX_FILE_BYTES = 500 * 1024 ** 2
const FILE_EXTENSIONS = [
  'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'csv', 'txt', 'md', 'rtf', 'odt', 'ods', 'odp',
  'zip', 'rar', '7z', 'tar', 'gz', 'png', 'jpg', 'jpeg', 'webp', 'gif', 'mp3', 'm4a', 'wav', 'ogg',
  'py', 'ipynb', 'java', 'c', 'cpp', 'h', 'cs', 'go', 'rs', 'php', 'rb', 'sql', 'json', 'xml', 'yaml', 'yml',
  'psd', 'ai', 'fig', 'sketch', 'dwg',
]
const fileAccept = FILE_EXTENSIONS.map((e) => `.${e}`).join(',')

// ---------- title / flags ----------
const editingTitle = ref(false)
const titleDraft = ref('')
const busy = ref(false)
const actionError = ref('')

function startEditTitle() {
  titleDraft.value = props.lesson.title
  editingTitle.value = true
}

async function patchLesson(body: Record<string, unknown>) {
  busy.value = true
  actionError.value = ''
  try {
    await request(`/lessons/${props.lesson.id}/`, { method: 'PATCH', body })
    emit('changed')
  } catch (err) {
    actionError.value = getErrorMessage(err, 'ذخیره نشد.')
  } finally {
    busy.value = false
  }
}

async function saveTitle() {
  const title = titleDraft.value.trim()
  editingTitle.value = false
  if (title && title !== props.lesson.title) await patchLesson({ title })
}

async function deleteLesson() {
  const hasContent = props.lesson.has_video || props.lesson.files.length
  const message = hasContent
    ? `«${props.lesson.title}» همراه با ویدیو و فایل‌هایش حذف شود؟ این کار برگشت‌پذیر نیست.`
    : `«${props.lesson.title}» حذف شود؟`
  if (!confirm(message)) return
  busy.value = true
  try {
    await request(`/lessons/${props.lesson.id}/`, { method: 'DELETE' })
    emit('changed')
  } catch (err) {
    actionError.value = getErrorMessage(err, 'حذف نشد.')
    busy.value = false
  }
}

// ---------- video ----------
const videoInput = ref<HTMLInputElement | null>(null)
const videoDrag = ref(false)
const videoUpload = ref<{ name: string; progress: UploadProgress | null; abort: () => void } | null>(null)
const videoError = ref('')

function pickVideo(file: File | undefined | null) {
  videoError.value = ''
  if (!file) return
  if (!file.type.startsWith('video/')) {
    videoError.value = 'این فایل ویدیو نیست. فرمت‌های مجاز: MP4، MOV، MKV، WEBM.'
    return
  }
  if (file.size > MAX_VIDEO_BYTES) {
    videoError.value = 'حجم ویدیو بیشتر از ۵ گیگابایت است.'
    return
  }
  if (props.lesson.has_video && !confirm('ویدیوی فعلی این جلسه با ویدیوی جدید جایگزین شود؟')) return

  const handle = upload('/videos/upload/', { lesson: String(props.lesson.id), file }, (p) => {
    if (videoUpload.value) videoUpload.value.progress = p
  })
  videoUpload.value = { name: file.name, progress: null, abort: handle.abort }
  emit('uploading', 1)
  handle.promise
    .then(() => emit('changed'))
    .catch((err) => {
      videoError.value = uploadErrorMessage(err, 'آپلود ویدیو ناموفق بود.')
    })
    .finally(() => {
      videoUpload.value = null
      emit('uploading', -1)
    })
}

function onVideoInput(e: Event) {
  const input = e.target as HTMLInputElement
  pickVideo(input.files?.[0])
  input.value = ''
}

async function deleteVideo() {
  if (!confirm('ویدیوی این جلسه حذف شود؟')) return
  busy.value = true
  try {
    await request(`/videos/${props.lesson.video_id}/`, { method: 'DELETE' })
    emit('changed')
  } catch (err) {
    videoError.value = getErrorMessage(err, 'حذف ویدیو ناموفق بود.')
  } finally {
    busy.value = false
  }
}

const videoState = computed(() => {
  if (videoUpload.value) return 'uploading'
  if (!props.lesson.has_video) return 'empty'
  return props.lesson.video_status as 'uploading' | 'processing' | 'ready' | 'failed'
})

// ---------- files ----------
const filesInput = ref<HTMLInputElement | null>(null)
const filesDrag = ref(false)
let queueKey = 0
const queue = ref<{ key: number; name: string; progress: UploadProgress | null; error: string; abort: () => void }[]>([])
const deletingFileId = ref<number | null>(null)
const filesError = ref('')

function extensionOf(name: string) {
  return name.includes('.') ? name.split('.').pop()!.toLowerCase() : ''
}

function pickFiles(list: FileList | File[] | null | undefined) {
  filesError.value = ''
  for (const file of Array.from(list ?? [])) {
    const key = ++queueKey
    const ext = extensionOf(file.name)
    if (!FILE_EXTENSIONS.includes(ext)) {
      queue.value.push({ key, name: file.name, progress: null, error: `نوع فایل .${ext || '?'} مجاز نیست.`, abort: () => {} })
      continue
    }
    if (file.size > MAX_FILE_BYTES) {
      queue.value.push({ key, name: file.name, progress: null, error: 'حجم بیشتر از ۵۰۰ مگابایت است.', abort: () => {} })
      continue
    }
    const handle = upload('/lesson-files/', { lesson: String(props.lesson.id), file }, (p) => {
      const item = queue.value.find((q) => q.key === key)
      if (item) item.progress = p
    })
    queue.value.push({ key, name: file.name, progress: null, error: '', abort: handle.abort })
    emit('uploading', 1)
    handle.promise
      .then(() => {
        queue.value = queue.value.filter((q) => q.key !== key)
        emit('changed')
      })
      .catch((err) => {
        const item = queue.value.find((q) => q.key === key)
        if (item) item.error = uploadErrorMessage(err, 'آپلود ناموفق بود.')
      })
      .finally(() => emit('uploading', -1))
  }
}

function onFilesInput(e: Event) {
  const input = e.target as HTMLInputElement
  pickFiles(input.files)
  input.value = ''
}

function dismiss(key: number) {
  queue.value = queue.value.filter((q) => q.key !== key)
}

async function deleteFile(file: any) {
  if (!confirm(`فایل «${file.title || file.original_name}» حذف شود؟`)) return
  deletingFileId.value = file.id
  try {
    await request(`/lesson-files/${file.id}/`, { method: 'DELETE' })
    emit('changed')
  } catch (err) {
    filesError.value = getErrorMessage(err, 'حذف فایل ناموفق بود.')
  } finally {
    deletingFileId.value = null
  }
}

async function downloadFile(file: any) {
  try {
    const { url } = await request<{ url: string }>(`/lesson-files/${file.id}/download/`)
    window.open(url, '_blank', 'noopener')
  } catch (err) {
    filesError.value = getErrorMessage(err, 'دانلود ممکن نشد.')
  }
}
</script>

<template>
  <article class="glass overflow-hidden rounded-2xl" :class="{ 'opacity-60': busy }">
    <!-- Header -->
    <header class="flex flex-wrap items-center gap-3 border-b border-white/30 px-5 py-4 dark:border-white/10">
      <span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary-600 text-sm font-black text-white">
        {{ lesson.order.toLocaleString('fa-IR') }}
      </span>

      <div class="min-w-0 flex-1">
        <input
          v-if="editingTitle"
          v-model="titleDraft"
          class="glass w-full rounded-lg px-3 py-1.5 text-sm font-semibold text-gray-900 outline-none focus:ring-2 focus:ring-primary-500/50 dark:text-white"
          @keydown.enter.prevent="saveTitle"
          @keydown.esc="editingTitle = false"
          @blur="saveTitle"
        >
        <button
          v-else
          type="button"
          class="group flex max-w-full items-center gap-2 text-start"
          title="ویرایش عنوان"
          @click="startEditTitle"
        >
          <span class="truncate font-bold text-gray-900 dark:text-white">{{ lesson.title }}</span>
          <svg class="h-3.5 w-3.5 shrink-0 text-gray-400 opacity-0 transition group-hover:opacity-100" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" /></svg>
        </button>
      </div>

      <button
        type="button"
        :class="[
          'rounded-full px-3 py-1 text-xs font-medium transition',
          lesson.is_free_preview
            ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300'
            : 'bg-black/5 text-gray-500 hover:text-gray-700 dark:bg-white/5 dark:text-gray-400',
        ]"
        :title="lesson.is_free_preview ? 'همه می‌توانند این جلسه را کامل ببینند' : 'فقط دانشجوهای ثبت‌نام‌شده'"
        @click="patchLesson({ is_free_preview: !lesson.is_free_preview })"
      >
        {{ lesson.is_free_preview ? '✓ رایگان برای همه' : 'رایگان کردن' }}
      </button>

      <div class="flex items-center gap-0.5">
        <button type="button" :disabled="isFirst" class="rounded-lg p-1.5 text-gray-500 transition hover:bg-black/5 disabled:opacity-30 dark:hover:bg-white/10" aria-label="بالا" @click="emit('move', 'up')">
          <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M5 15l7-7 7 7" /></svg>
        </button>
        <button type="button" :disabled="isLast" class="rounded-lg p-1.5 text-gray-500 transition hover:bg-black/5 disabled:opacity-30 dark:hover:bg-white/10" aria-label="پایین" @click="emit('move', 'down')">
          <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" /></svg>
        </button>
        <button type="button" class="rounded-lg p-1.5 text-gray-400 transition hover:bg-red-500/10 hover:text-red-600" aria-label="حذف جلسه" @click="deleteLesson">
          <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
        </button>
      </div>
    </header>
    <p v-if="actionError" class="px-5 pt-3 text-sm text-red-600">{{ actionError }}</p>

    <div class="grid grid-cols-1 gap-5 p-5 lg:grid-cols-2">
      <!-- ============ Video ============ -->
      <section>
        <h3 class="mb-2.5 flex items-center gap-2 text-sm font-semibold text-gray-700 dark:text-gray-200">
          <svg class="h-4 w-4 text-primary-600 dark:text-primary-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
          ویدیوی جلسه
        </h3>
        <input ref="videoInput" type="file" accept="video/*" class="hidden" @change="onVideoInput">

        <!-- empty -->
        <button
          v-if="videoState === 'empty'"
          type="button"
          :class="[
            'flex h-40 w-full flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed text-center transition',
            videoDrag ? 'scale-[1.01] border-primary-500 bg-primary-500/10' : 'border-gray-300 hover:border-primary-400 hover:bg-primary-500/5 dark:border-white/15',
          ]"
          @click="videoInput?.click()"
          @dragover.prevent="videoDrag = true"
          @dragleave.prevent="videoDrag = false"
          @drop.prevent="videoDrag = false; pickVideo($event.dataTransfer?.files?.[0])"
        >
          <span class="flex h-12 w-12 items-center justify-center rounded-full bg-primary-500/10 text-primary-600 dark:text-primary-400">
            <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" /></svg>
          </span>
          <span class="text-sm font-medium text-gray-700 dark:text-gray-200">ویدیو را اینجا رها کنید یا کلیک کنید</span>
          <span class="text-xs text-gray-500 dark:text-gray-400">MP4، MOV، MKV یا WEBM — تا ۵ گیگابایت</span>
        </button>

        <!-- uploading -->
        <div v-else-if="videoState === 'uploading'" class="rounded-xl bg-primary-500/5 p-4 ring-1 ring-primary-500/20">
          <div class="flex items-center justify-between gap-3">
            <p class="min-w-0 truncate text-sm font-medium text-gray-800 dark:text-gray-100" dir="auto">{{ videoUpload?.name }}</p>
            <button type="button" class="shrink-0 text-xs font-medium text-red-600 hover:underline" @click="videoUpload?.abort()">لغو</button>
          </div>
          <div class="mt-3 h-2.5 overflow-hidden rounded-full bg-black/5 dark:bg-white/10">
            <div
              class="upload-bar h-full rounded-full bg-gradient-to-l from-primary-500 to-accent-500 transition-[width] duration-300"
              :style="{ width: `${videoUpload?.progress?.percent ?? 2}%` }"
            />
          </div>
          <div class="mt-2 flex flex-wrap justify-between gap-2 text-xs text-gray-600 dark:text-gray-400">
            <span v-if="videoUpload?.progress">
              {{ videoUpload.progress.percent.toLocaleString('fa-IR') }}٪ —
              {{ formatBytes(videoUpload.progress.loaded) }} از {{ formatBytes(videoUpload.progress.total) }}
            </span>
            <span v-else>در حال آماده‌سازی...</span>
            <span v-if="videoUpload?.progress?.remaining">{{ formatRemaining(videoUpload.progress.remaining) }} مانده</span>
          </div>
          <p class="mt-2 text-[11px] text-gray-500 dark:text-gray-400">تا پایان آپلود این صفحه را نبندید.</p>
        </div>

        <!-- processing -->
        <div v-else-if="videoState === 'processing'" class="rounded-xl bg-amber-500/10 p-4 ring-1 ring-amber-500/25">
          <div class="flex items-center gap-3">
            <span class="relative flex h-10 w-10 items-center justify-center">
              <span class="absolute inset-0 animate-spin rounded-full border-2 border-amber-500/30 border-t-amber-500" />
              <svg class="h-4 w-4 text-amber-600" fill="currentColor" viewBox="0 0 20 20"><path d="M6 4l10 6-10 6V4z" /></svg>
            </span>
            <div>
              <p class="text-sm font-semibold text-amber-800 dark:text-amber-300">در حال پردازش ویدیو</p>
              <p class="text-xs text-amber-700/80 dark:text-amber-300/70">ساخت کیفیت‌های پخش و کلیپ پیش‌نمایش؛ بسته به طول ویدیو چند دقیقه طول می‌کشد.</p>
            </div>
          </div>
        </div>

        <!-- ready -->
        <div v-else-if="videoState === 'ready'" class="flex items-center gap-3 rounded-xl bg-emerald-500/10 p-4 ring-1 ring-emerald-500/25">
          <span class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-emerald-500 text-white">
            <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" /></svg>
          </span>
          <div class="min-w-0 flex-1">
            <p class="text-sm font-semibold text-emerald-800 dark:text-emerald-300">آماده‌ی پخش</p>
            <p v-if="lesson.video_duration" class="text-xs text-emerald-700/80 dark:text-emerald-300/70">مدت: {{ formatDuration(lesson.video_duration) }}</p>
          </div>
          <button type="button" class="glass shrink-0 rounded-lg px-3 py-1.5 text-xs font-medium text-gray-800 dark:text-gray-100" @click="videoInput?.click()">جایگزینی</button>
          <button type="button" class="shrink-0 rounded-lg px-2 py-1.5 text-xs font-medium text-red-600 hover:bg-red-500/10" @click="deleteVideo">حذف</button>
        </div>

        <!-- failed -->
        <div v-else-if="videoState === 'failed'" class="rounded-xl bg-red-500/10 p-4 ring-1 ring-red-500/25">
          <p class="text-sm font-semibold text-red-700 dark:text-red-300">پردازش ویدیو ناموفق بود</p>
          <p v-if="lesson.video_error" class="mt-1 line-clamp-2 text-xs text-red-700/80 dark:text-red-300/70" dir="ltr">{{ lesson.video_error }}</p>
          <div class="mt-3 flex gap-2">
            <button type="button" class="rounded-lg bg-red-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-red-500" @click="videoInput?.click()">آپلود دوباره</button>
            <button type="button" class="rounded-lg px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-500/10" @click="deleteVideo">حذف</button>
          </div>
        </div>

        <p v-if="videoError" class="mt-2 text-xs text-red-600">{{ videoError }}</p>
      </section>

      <!-- ============ Files ============ -->
      <section>
        <h3 class="mb-2.5 flex items-center justify-between gap-2 text-sm font-semibold text-gray-700 dark:text-gray-200">
          <span class="flex items-center gap-2">
            <svg class="h-4 w-4 text-accent-600 dark:text-accent-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" /></svg>
            فایل‌ها و جزوه‌ها
          </span>
          <span v-if="lesson.files.length" class="text-xs font-normal text-gray-500">{{ lesson.files.length.toLocaleString('fa-IR') }} فایل</span>
        </h3>
        <input ref="filesInput" type="file" multiple :accept="fileAccept" class="hidden" @change="onFilesInput">

        <ul v-if="lesson.files.length || queue.length" class="mb-3 space-y-2">
          <li v-for="file in lesson.files" :key="file.id" class="flex items-center gap-3 rounded-xl bg-black/[0.03] p-2.5 dark:bg-white/5">
            <CourseFileIcon :extension="file.extension" size="sm" />
            <div class="min-w-0 flex-1">
              <p class="truncate text-sm font-medium text-gray-800 dark:text-gray-100" dir="auto">{{ file.title || file.original_name }}</p>
              <p class="text-[11px] text-gray-500 dark:text-gray-400">{{ formatBytes(file.size_bytes) }}</p>
            </div>
            <button type="button" class="rounded-lg p-1.5 text-gray-500 transition hover:bg-black/5 hover:text-primary-600 dark:hover:bg-white/10" aria-label="دانلود" @click="downloadFile(file)">
              <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
            </button>
            <button
              type="button"
              :disabled="deletingFileId === file.id"
              class="rounded-lg p-1.5 text-gray-400 transition hover:bg-red-500/10 hover:text-red-600 disabled:opacity-40"
              aria-label="حذف فایل"
              @click="deleteFile(file)"
            >
              <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </li>

          <!-- in-flight / failed uploads -->
          <li
            v-for="item in queue"
            :key="item.key"
            :class="['rounded-xl p-2.5', item.error ? 'bg-red-500/10 ring-1 ring-red-500/20' : 'bg-primary-500/5 ring-1 ring-primary-500/20']"
          >
            <div class="flex items-center gap-3">
              <CourseFileIcon :extension="extensionOf(item.name)" size="sm" />
              <div class="min-w-0 flex-1">
                <p class="truncate text-sm font-medium text-gray-800 dark:text-gray-100" dir="auto">{{ item.name }}</p>
                <p v-if="item.error" class="text-[11px] text-red-600">{{ item.error }}</p>
                <div v-else class="mt-1.5 h-1.5 overflow-hidden rounded-full bg-black/5 dark:bg-white/10">
                  <div
                    class="upload-bar h-full rounded-full bg-gradient-to-l from-primary-500 to-accent-500 transition-[width] duration-300"
                    :style="{ width: `${item.progress?.percent ?? 3}%` }"
                  />
                </div>
              </div>
              <span v-if="!item.error" class="w-9 shrink-0 text-center text-[11px] text-gray-500">
                {{ (item.progress?.percent ?? 0).toLocaleString('fa-IR') }}٪
              </span>
              <button
                type="button"
                class="rounded-lg p-1.5 text-gray-400 transition hover:text-red-600"
                :aria-label="item.error ? 'بستن' : 'لغو آپلود'"
                @click="item.error ? dismiss(item.key) : item.abort()"
              >
                <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
          </li>
        </ul>

        <button
          type="button"
          :class="[
            'flex w-full items-center justify-center gap-2 rounded-xl border-2 border-dashed px-4 text-sm transition',
            lesson.files.length || queue.length ? 'py-3' : 'h-40 flex-col',
            filesDrag ? 'scale-[1.01] border-accent-500 bg-accent-500/10' : 'border-gray-300 text-gray-600 hover:border-accent-400 hover:bg-accent-500/5 dark:border-white/15 dark:text-gray-300',
          ]"
          @click="filesInput?.click()"
          @dragover.prevent="filesDrag = true"
          @dragleave.prevent="filesDrag = false"
          @drop.prevent="filesDrag = false; pickFiles($event.dataTransfer?.files)"
        >
          <svg class="h-5 w-5 text-accent-600 dark:text-accent-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" /></svg>
          <span class="font-medium">{{ lesson.files.length || queue.length ? 'افزودن فایل دیگر' : 'فایل‌ها را اینجا رها کنید یا کلیک کنید' }}</span>
          <span v-if="!lesson.files.length && !queue.length" class="text-xs text-gray-500 dark:text-gray-400">PDF، ورد، پاورپوینت، زیپ، کد و... — چند فایل با هم، هرکدام تا ۵۰۰ مگابایت</span>
        </button>
        <p v-if="filesError" class="mt-2 text-xs text-red-600">{{ filesError }}</p>
      </section>
    </div>
  </article>
</template>

<style scoped>
/* Moving sheen on progress bars so a slow upload still looks alive */
.upload-bar {
  background-size: 200% 100%;
  animation: sheen 1.6s linear infinite;
  background-image: linear-gradient(
    110deg,
    rgb(var(--c-primary-500)) 0%,
    rgb(var(--c-accent-500)) 45%,
    rgb(255 255 255 / 0.55) 50%,
    rgb(var(--c-accent-500)) 55%,
    rgb(var(--c-primary-500)) 100%
  );
}
@keyframes sheen {
  from { background-position: 200% 0; }
  to { background-position: 0 0; }
}
</style>
