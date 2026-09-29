<script setup lang="ts">
// The student's classroom for one purchased course: player, lesson list
// with progress, and each lesson's files. `?lesson=<id>` keeps the place.
definePageMeta({ layout: 'dashboard', ssr: false })

const route = useRoute()
const router = useRouter()
const { request } = useApi()
const { download, downloadingId, downloadError } = useLessonFiles()

const { data: course, pending, error } = await useAsyncData(`learn-${route.params.slug}`, () =>
  request<any>(`/courses/${route.params.slug}/`),
)

const lessons = computed<any[]>(() => course.value?.lessons ?? [])
const canAccess = (lesson: any) => !!(course.value?.is_enrolled || lesson.is_free_preview)

const activeId = computed<number | null>(() => {
  const fromQuery = Number(route.query.lesson)
  if (fromQuery && lessons.value.some((l) => l.id === fromQuery)) return fromQuery
  const next = lessons.value.find((l) => !l.completed && canAccess(l)) ?? lessons.value[0]
  return next?.id ?? null
})
const activeIndex = computed(() => lessons.value.findIndex((l) => l.id === activeId.value))
const active = computed(() => lessons.value[activeIndex.value])
const prev = computed(() => lessons.value[activeIndex.value - 1])
const next = computed(() => lessons.value[activeIndex.value + 1])

const completedCount = computed(() => lessons.value.filter((l) => l.completed).length)
const percent = computed(() => (lessons.value.length ? (completedCount.value * 100) / lessons.value.length : 0))

function select(lesson: any) {
  router.replace({ query: { ...route.query, lesson: lesson.id } })
  if (import.meta.client) window.scrollTo({ top: 0, behavior: 'smooth' })
}

const toggling = ref(false)
async function toggleComplete() {
  if (!active.value) return
  toggling.value = true
  try {
    const saved = await request<{ completed: boolean }>('/progress/', {
      method: 'POST',
      body: { lesson_id: active.value.id, completed: !active.value.completed },
    })
    active.value.completed = saved.completed
    if (saved.completed && next.value && canAccess(next.value)) select(next.value)
  } finally {
    toggling.value = false
  }
}

function onPlayerProgress(saved: { lesson_id: number; position_seconds: number; completed: boolean }) {
  const lesson = lessons.value.find((l) => l.id === saved.lesson_id)
  if (!lesson) return
  lesson.progress_seconds = saved.position_seconds
  lesson.completed = saved.completed
}

useSeoMeta({ title: () => course.value?.title ?? 'یادگیری' })
</script>

<template>
  <div class="mx-auto max-w-6xl">
    <NuxtLink to="/dashboard/my-courses" class="text-sm text-primary-600 hover:underline dark:text-primary-400">→ دوره‌های من</NuxtLink>

    <div v-if="pending" class="mt-6 text-gray-500">در حال بارگذاری...</div>
    <div v-else-if="error || !course" class="glass mt-6 rounded-2xl p-8 text-center text-gray-600 dark:text-gray-300">
      این دوره پیدا نشد.
    </div>

    <template v-else>
      <!-- Header + overall progress -->
      <div class="mt-3 flex flex-wrap items-center justify-between gap-4">
        <div class="min-w-0">
          <h1 class="text-2xl font-extrabold text-gray-900 dark:text-white">{{ course.title }}</h1>
          <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
            {{ completedCount.toLocaleString('fa-IR') }} از {{ lessons.length.toLocaleString('fa-IR') }} جلسه تکمیل شده است
          </p>
        </div>
        <CourseProgressRing data-tour="learn-progress" :percent="percent" :size="64" />
      </div>

      <div v-if="!course.is_enrolled" class="mt-5 flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-accent-500/10 px-5 py-4 ring-1 ring-accent-500/25">
        <p class="text-sm text-gray-800 dark:text-gray-100">هنوز در این دوره ثبت‌نام نکرده‌اید؛ در حال حاضر تنها جلسه‌های رایگان در دسترس است.</p>
        <NuxtLink :to="`/courses/${course.slug}`" class="rounded-lg bg-accent-500 px-4 py-2 text-sm font-semibold text-white hover:bg-accent-400">
          ثبت‌نام در دوره
        </NuxtLink>
      </div>

      <div class="mt-6 grid grid-cols-1 items-start gap-6 lg:grid-cols-12">
        <!-- Player + current lesson -->
        <section class="space-y-5 lg:col-span-8">
          <div v-if="active" data-tour="learn-player" class="glass overflow-hidden rounded-2xl">
            <ClientOnly v-if="active.has_video && active.video_status === 'ready' && canAccess(active)">
              <PlayerVideoPlayer
                :key="active.video_id"
                :video-id="active.video_id"
                :lesson-id="active.id"
                :has-full-access="true"
                :initial-position="active.progress_seconds"
                class="!rounded-none"
                @progress="onPlayerProgress"
              />
            </ClientOnly>
            <div v-else class="flex aspect-video flex-col items-center justify-center gap-3 bg-gradient-to-br from-primary-500/15 to-accent-500/15 px-6 text-center">
              <span class="flex h-14 w-14 items-center justify-center rounded-2xl bg-white/60 text-primary-700 dark:bg-white/10 dark:text-primary-300">
                <svg v-if="!canAccess(active)" class="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" /></svg>
                <svg v-else class="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
              </span>
              <p class="font-semibold text-gray-800 dark:text-gray-100">
                {{ !canAccess(active) ? 'این جلسه ویژه‌ی دانشجویان ثبت‌نام‌شده است'
                  : active.has_video ? 'ویدیوی این جلسه در حال آماده‌سازی است'
                  : 'این جلسه ویدیو ندارد؛ فایل‌های آن را از بخش پایین دریافت کنید' }}
              </p>
            </div>

            <div class="flex flex-wrap items-center justify-between gap-3 p-5">
              <div class="min-w-0">
                <p class="text-xs font-medium text-primary-600 dark:text-primary-400">جلسه‌ی {{ (activeIndex + 1).toLocaleString('fa-IR') }}</p>
                <h2 class="mt-0.5 text-lg font-bold text-gray-900 dark:text-white">{{ active.title }}</h2>
              </div>
              <button
                v-if="course.is_enrolled"
                data-tour="learn-complete"
                type="button"
                :disabled="toggling"
                :class="[
                  'flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold transition disabled:opacity-60',
                  active.completed
                    ? 'bg-emerald-500/15 text-emerald-700 hover:bg-emerald-500/25 dark:text-emerald-300'
                    : 'bg-primary-600 text-white shadow-lg shadow-primary-600/25 hover:bg-primary-500',
                ]"
                @click="toggleComplete"
              >
                <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" /></svg>
                {{ active.completed ? 'تکمیل شد' : 'علامت‌گذاری به‌عنوان تکمیل‌شده' }}
              </button>
            </div>

            <div class="flex justify-between border-t border-white/30 px-5 py-3 text-sm dark:border-white/10">
              <button v-if="prev" type="button" class="text-primary-600 hover:underline dark:text-primary-400" @click="select(prev)">→ جلسه‌ی قبل</button>
              <span v-else />
              <button v-if="next" type="button" class="text-primary-600 hover:underline dark:text-primary-400" @click="select(next)">جلسه‌ی بعد ←</button>
            </div>
          </div>

          <!-- Files of the current lesson -->
          <div v-if="active?.files?.length" data-tour="learn-files" class="glass rounded-2xl p-5">
            <h3 class="font-semibold text-gray-900 dark:text-white">فایل‌های این جلسه</h3>
            <ul class="mt-3 grid grid-cols-1 gap-2.5 sm:grid-cols-2">
              <li v-for="file in active.files" :key="file.id">
                <button
                  type="button"
                  :disabled="!canAccess(active) || downloadingId === file.id"
                  class="group flex w-full items-center gap-3 rounded-xl bg-black/[0.03] p-3 text-start transition hover:bg-primary-500/10 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-white/5"
                  @click="download(file.id)"
                >
                  <CourseFileIcon :extension="file.extension" />
                  <span class="min-w-0 flex-1">
                    <span class="block truncate text-sm font-medium text-gray-800 dark:text-gray-100" dir="auto">{{ file.title || file.original_name }}</span>
                    <span class="text-xs text-gray-500 dark:text-gray-400">{{ formatBytes(file.size_bytes) }}</span>
                  </span>
                  <span class="flex h-9 w-9 items-center justify-center rounded-full bg-primary-600 text-white transition group-hover:scale-110">
                    <span v-if="downloadingId === file.id" class="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                    <svg v-else class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
                  </span>
                </button>
              </li>
            </ul>
            <p v-if="downloadError" class="mt-2 text-sm text-red-600">{{ downloadError }}</p>
          </div>
        </section>

        <!-- Lesson list -->
        <aside data-tour="learn-lessons" class="glass overflow-hidden rounded-2xl lg:sticky lg:top-6 lg:col-span-4">
          <div class="border-b border-white/30 px-5 py-4 dark:border-white/10">
            <p class="font-semibold text-gray-900 dark:text-white">جلسه‌ها</p>
            <div class="mt-2 h-1.5 overflow-hidden rounded-full bg-black/5 dark:bg-white/10">
              <div class="h-full rounded-full bg-gradient-to-l from-primary-500 to-emerald-500 transition-[width] duration-700" :style="{ width: `${percent}%` }" />
            </div>
          </div>
          <ol class="max-h-[70vh] overflow-y-auto p-2">
            <li v-for="(lesson, i) in lessons" :key="lesson.id">
              <button
                type="button"
                :class="[
                  'flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-start transition',
                  lesson.id === activeId ? 'bg-primary-500/15' : 'hover:bg-black/[0.04] dark:hover:bg-white/5',
                ]"
                @click="select(lesson)"
              >
                <span
                  :class="[
                    'flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold',
                    lesson.completed ? 'bg-emerald-500 text-white'
                    : lesson.id === activeId ? 'bg-primary-600 text-white'
                    : 'bg-black/5 text-gray-600 dark:bg-white/10 dark:text-gray-300',
                  ]"
                >
                  <svg v-if="lesson.completed" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" /></svg>
                  <svg v-else-if="!canAccess(lesson)" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" /></svg>
                  <template v-else>{{ (i + 1).toLocaleString('fa-IR') }}</template>
                </span>
                <span class="min-w-0 flex-1">
                  <span :class="['block truncate text-sm', lesson.id === activeId ? 'font-bold text-gray-900 dark:text-white' : 'text-gray-700 dark:text-gray-200']">
                    {{ lesson.title }}
                  </span>
                  <span class="flex items-center gap-2 text-[11px] text-gray-500 dark:text-gray-400">
                    <span v-if="lesson.video_duration">{{ formatDuration(lesson.video_duration) }}</span>
                    <span v-if="lesson.files.length" class="flex items-center gap-0.5">
                      <svg class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" /></svg>
                      {{ lesson.files.length.toLocaleString('fa-IR') }}
                    </span>
                    <span v-if="lesson.is_free_preview && !course.is_enrolled" class="text-emerald-600">رایگان</span>
                  </span>
                </span>
              </button>
            </li>
          </ol>
        </aside>
      </div>
    </template>
  </div>
</template>
