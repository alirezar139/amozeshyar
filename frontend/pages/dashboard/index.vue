<script setup lang="ts">
definePageMeta({ layout: 'dashboard' })
const authStore = useAuthStore()
const { request } = useApi()
const { owner, teacherName } = useSite()
const { formatGregorianDate } = useJalali()
const { download, downloadingId, downloadError } = useLessonFiles()

const continueAsync = useAsyncData('dashboard-continue', () => request<any>('/enrollments/continue/').catch(() => null))
const summaryAsync = useAsyncData('dashboard-summary', () => request<any>('/enrollments/summary/').catch(() => null))
await Promise.all([continueAsync, summaryAsync])
const { data: continueLearning } = continueAsync
const { data: summary } = summaryAsync

const lessonPercent = computed(() =>
  summary.value?.total_lessons ? (summary.value.completed_lessons * 100) / summary.value.total_lessons : 0,
)

// ---- next class countdown ----
const now = ref(Date.now())
let ticker: ReturnType<typeof setInterval> | null = null
onMounted(() => {
  ticker = setInterval(() => (now.value = Date.now()), 1000)
})
onUnmounted(() => {
  if (ticker) clearInterval(ticker)
})

const nextStartsAt = computed(() => (summary.value?.next_session ? new Date(summary.value.next_session.starts_at) : null))
const countdown = computed(() => {
  if (!nextStartsAt.value) return null
  const diff = Math.max(0, nextStartsAt.value.getTime() - now.value)
  const d = Math.floor(diff / 86400000)
  const h = Math.floor((diff % 86400000) / 3600000)
  const m = Math.floor((diff % 3600000) / 60000)
  const s = Math.floor((diff % 60000) / 1000)
  return { d, h, m, s, soon: diff < 15 * 60000 }
})
const fa = (n: number) => n.toLocaleString('fa-IR', { minimumIntegerDigits: 2, useGrouping: false })

function timeOf(date: Date) {
  return date.toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <div class="space-y-6">
    <div>
      <h1 class="text-2xl font-extrabold text-gray-900 dark:text-white">
        سلام{{ authStore.user?.first_name ? '، ' + authStore.user.first_name : '' }} 👋
      </h1>
      <p class="mt-1 text-gray-600 dark:text-gray-400">امروز هم یک قدم جلوتر برو.</p>
    </div>

    <!-- Stats -->
    <section v-if="summary" data-tour="dashboard-stats" class="grid grid-cols-1 gap-4 sm:grid-cols-3">
      <div class="glass flex items-center gap-4 rounded-2xl p-5">
        <CourseProgressRing :percent="lessonPercent" :size="60" />
        <div>
          <p class="text-sm text-gray-600 dark:text-gray-400">جلسه‌های تکمیل‌شده</p>
          <p class="mt-0.5 text-xl font-black text-gray-900 dark:text-white">
            {{ summary.completed_lessons.toLocaleString('fa-IR') }}
            <span class="text-sm font-medium text-gray-500">از {{ summary.total_lessons.toLocaleString('fa-IR') }}</span>
          </p>
        </div>
      </div>
      <NuxtLink to="/dashboard/my-courses" class="glass flex items-center gap-4 rounded-2xl p-5 transition hover:-translate-y-0.5">
        <span class="flex h-[60px] w-[60px] items-center justify-center rounded-2xl bg-primary-500/15 text-primary-700 dark:text-primary-300">
          <svg class="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" /></svg>
        </span>
        <div>
          <p class="text-sm text-gray-600 dark:text-gray-400">دوره‌های من</p>
          <p class="mt-0.5 text-xl font-black text-gray-900 dark:text-white">{{ summary.courses.toLocaleString('fa-IR') }}</p>
        </div>
      </NuxtLink>
      <div class="glass flex items-center gap-4 rounded-2xl p-5">
        <span class="flex h-[60px] w-[60px] items-center justify-center rounded-2xl bg-accent-500/15 text-accent-600 dark:text-accent-400">
          <svg class="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
        </span>
        <div>
          <p class="text-sm text-gray-600 dark:text-gray-400">زمان یادگیری</p>
          <p class="mt-0.5 text-xl font-black text-gray-900 dark:text-white">
            {{ summary.watched_minutes.toLocaleString('fa-IR') }} <span class="text-sm font-medium text-gray-500">دقیقه</span>
          </p>
        </div>
      </div>
    </section>

    <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <!-- Continue learning -->
      <NuxtLink
        v-if="continueLearning"
        :to="`/dashboard/courses/${continueLearning.course_slug}?lesson=${continueLearning.lesson_id}`"
        data-tour="continue-learning"
        class="group relative overflow-hidden rounded-2xl bg-gradient-to-br from-primary-600 to-primary-800 p-6 text-white shadow-xl transition hover:-translate-y-0.5"
      >
        <div class="absolute -end-10 -top-10 h-40 w-40 rounded-full bg-accent-400/30 blur-2xl" />
        <p class="relative text-xs font-medium text-primary-100">ادامه‌ی یادگیری</p>
        <p class="relative mt-2 text-lg font-bold">{{ continueLearning.course_title }}</p>
        <p class="relative mt-1 text-sm text-primary-100/90">{{ continueLearning.lesson_title }}</p>
        <span class="relative mt-5 inline-flex items-center gap-2 rounded-xl bg-white px-4 py-2 text-sm font-bold text-primary-700 transition group-hover:gap-3">
          <svg class="h-4 w-4" fill="currentColor" viewBox="0 0 20 20"><path d="M6 4l10 6-10 6V4z" /></svg>
          ادامه بده
        </span>
      </NuxtLink>

      <!-- Next class -->
      <section v-if="summary?.next_session && countdown" data-tour="next-session" class="glass rounded-2xl p-6">
        <div class="flex items-center gap-2 text-xs font-medium text-emerald-600 dark:text-emerald-400">
          <span class="relative flex h-2 w-2">
            <span class="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
            <span class="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
          </span>
          دوره‌ی آنلاین بعدی
        </div>
        <p class="mt-2 text-lg font-bold text-gray-900 dark:text-white">{{ summary.next_session.title }}</p>
        <p class="text-sm text-gray-600 dark:text-gray-400">
          {{ summary.next_session.course_title }} — {{ formatGregorianDate(nextStartsAt!) }}، ساعت {{ timeOf(nextStartsAt!) }}
        </p>
        <div class="mt-4 flex items-center gap-2" dir="ltr">
          <template v-for="(part, i) in [
            { v: countdown.d, l: 'روز' }, { v: countdown.h, l: 'ساعت' }, { v: countdown.m, l: 'دقیقه' }, { v: countdown.s, l: 'ثانیه' },
          ]" :key="i">
            <div class="flex min-w-[3.5rem] flex-col items-center rounded-xl bg-black/[0.04] px-2 py-2 dark:bg-white/5">
              <span class="text-xl font-black tabular-nums text-gray-900 dark:text-white">{{ fa(part.v) }}</span>
              <span class="text-[10px] text-gray-500">{{ part.l }}</span>
            </div>
          </template>
        </div>
        <NuxtLink
          v-if="summary.next_session.is_online"
          :to="`/classroom/${summary.next_session.id}`"
          :class="[
            'mt-4 inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold transition',
            countdown.soon ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-600/30 hover:bg-emerald-500' : 'glass text-gray-800 dark:text-gray-100',
          ]"
        >
          {{ countdown.soon ? 'ورود به دوره‌ی آنلاین' : 'جزئیات' }}
        </NuxtLink>
      </section>
      <section v-else-if="summary" data-tour="next-session" class="glass flex flex-col justify-center rounded-2xl p-6">
        <p class="font-semibold text-gray-800 dark:text-gray-100">فعلاً دوره‌ی آنلاینی در پیش ندارید</p>
        <NuxtLink to="/dashboard/calendar" class="mt-2 text-sm text-primary-600 hover:underline dark:text-primary-400">تقویم دوره‌های آنلاین ←</NuxtLink>
      </section>
    </div>

    <!-- Latest files -->
    <section v-if="summary?.recent_files?.length" data-tour="recent-files" class="glass rounded-2xl p-6">
      <h2 class="font-semibold text-gray-900 dark:text-white">تازه‌ترین فایل‌ها</h2>
      <ul class="mt-3 divide-y divide-black/5 dark:divide-white/5">
        <li v-for="file in summary.recent_files" :key="file.id" class="flex items-center gap-3 py-3">
          <CourseFileIcon :extension="file.extension" size="sm" />
          <div class="min-w-0 flex-1">
            <p class="truncate text-sm font-medium text-gray-800 dark:text-gray-100" dir="auto">{{ file.title }}</p>
            <p class="truncate text-xs text-gray-500 dark:text-gray-400">{{ file.course_title }} — {{ file.lesson_title }} · {{ formatBytes(file.size_bytes) }}</p>
          </div>
          <button
            type="button"
            :disabled="downloadingId === file.id"
            class="flex h-9 w-9 items-center justify-center rounded-full bg-primary-600 text-white transition hover:scale-110 disabled:opacity-60"
            aria-label="دانلود"
            @click="download(file.id)"
          >
            <span v-if="downloadingId === file.id" class="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
            <svg v-else class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
          </button>
        </li>
      </ul>
      <p v-if="downloadError" class="mt-2 text-sm text-red-600">{{ downloadError }}</p>
    </section>

    <!-- Teacher -->
    <section data-tour="teacher-card" class="glass flex flex-col gap-5 rounded-2xl p-6 sm:flex-row sm:items-center">
      <img
        v-if="owner?.cover_image"
        :src="owner.cover_image"
        :alt="teacherName"
        class="h-16 w-16 shrink-0 rounded-2xl object-cover object-top shadow-lg"
      >
      <span v-else class="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-primary-500 to-accent-500 text-2xl font-black text-white shadow-lg">
        {{ teacherName[0] }}
      </span>
      <div class="min-w-0 flex-1">
        <p class="text-xs font-medium text-primary-600 dark:text-primary-400">استاد شما</p>
        <p class="mt-1 text-lg font-extrabold text-gray-900 dark:text-white">{{ teacherName }}</p>
        <p v-if="owner?.headline" class="mt-0.5 text-sm text-gray-600 dark:text-gray-400">{{ owner.headline }}</p>
      </div>
      <NuxtLink
        to="/courses"
        class="shrink-0 rounded-xl bg-primary-600 px-5 py-2.5 text-center text-sm font-semibold text-white shadow-lg shadow-primary-600/30 transition hover:bg-primary-500"
      >
        دوره‌های استاد
      </NuxtLink>
    </section>
  </div>
</template>
