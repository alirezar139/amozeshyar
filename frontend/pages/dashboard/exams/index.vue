<script setup lang="ts">
// The student's exams across their courses: what's open now (with a live
// countdown to closing), what's coming, and past results.
definePageMeta({ layout: 'dashboard', ssr: false })
useSeoMeta({ title: 'آزمون‌ها' })

const { request } = useApi()
const { formatGregorianDate } = useJalali()
const { remaining } = useExamClock()

const { data: exams, pending } = await useAsyncData('my-exams', () => request<any[]>('/exams/'))

function state(exam: any) {
  const attempt = exam.my_attempt
  if (attempt?.status === 'in_progress') return 'running'
  if (attempt) return 'done'
  if (exam.is_open) return 'open'
  if (exam.available_from && Date.parse(exam.available_from) > Date.now()) return 'upcoming'
  return 'closed'
}
const ORDER = { running: 0, open: 1, upcoming: 2, done: 3, closed: 4 } as const
const sorted = computed(() => [...(exams.value ?? [])].sort((a, b) => ORDER[state(a)] - ORDER[state(b)]))

const when = (iso: string) => `${formatGregorianDate(new Date(iso))} ساعت ${clockTime(iso)}`
</script>

<template>
  <div class="mx-auto max-w-5xl">
    <h1 class="text-2xl font-extrabold text-gray-900 dark:text-white">آزمون‌ها</h1>
    <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">آزمون‌های دوره‌هایی که در آن‌ها ثبت‌نام کرده‌اید.</p>

    <div v-if="pending && !exams" class="mt-6 text-gray-500">در حال بارگذاری...</div>
    <div v-else-if="!sorted.length" class="glass mt-6 rounded-2xl p-8 text-center text-gray-600 dark:text-gray-300">فعلاً آزمونی برای شما وجود ندارد.</div>
    <div v-else class="mt-6 grid gap-4 md:grid-cols-2">
      <NuxtLink
        v-for="exam in sorted"
        :key="exam.id"
        :to="`/dashboard/exams/${exam.id}`"
        :class="['glass group flex flex-col rounded-2xl p-5 transition hover:-translate-y-0.5 hover:shadow-lg', state(exam) === 'closed' ? 'opacity-70' : '']"
      >
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <p class="text-xs text-primary-700 dark:text-primary-300">{{ exam.course_title }}</p>
            <h2 class="mt-1 text-lg font-bold text-gray-900 dark:text-white">{{ exam.title }}</h2>
          </div>
          <span v-if="state(exam) === 'done' && exam.my_attempt.status === 'graded'" :class="['shrink-0 rounded-xl px-3 py-1 text-sm font-extrabold', exam.my_attempt.percent >= exam.pass_percent ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300' : 'bg-red-500/15 text-red-700 dark:text-red-300']">
            {{ toPersianDigits(exam.my_attempt.percent) }}٪
          </span>
        </div>
        <p class="mt-3 text-sm text-gray-600 dark:text-gray-400">
          {{ toPersianDigits(exam.question_count) }} سوال · {{ toPersianDigits(exam.total_points) }} نمره ·
          {{ exam.duration_minutes ? `${toPersianDigits(exam.duration_minutes)} دقیقه` : 'بدون محدودیت زمان' }}
        </p>

        <div class="mt-auto flex flex-wrap items-center gap-2 pt-4">
          <template v-if="state(exam) === 'running'">
            <span class="rounded-full bg-sky-500/15 px-2.5 py-1 text-xs font-semibold text-sky-700 dark:text-sky-300">در حال برگزاری</span>
            <span class="ms-auto text-sm font-semibold text-primary-600 group-hover:underline">ادامه‌ی آزمون ←</span>
          </template>
          <template v-else-if="state(exam) === 'open'">
            <ExamCountdown v-if="exam.available_until" :ms="remaining(exam.available_until)" size="sm" label="مهلت شرکت" />
            <span v-else class="rounded-full bg-emerald-500/15 px-2.5 py-1 text-xs font-semibold text-emerald-700 dark:text-emerald-300">باز است</span>
            <span class="ms-auto text-sm font-semibold text-primary-600 group-hover:underline">شروع آزمون ←</span>
          </template>
          <template v-else-if="state(exam) === 'upcoming'">
            <span class="rounded-full bg-violet-500/15 px-2.5 py-1 text-xs font-semibold text-violet-700 dark:text-violet-300">شروع: {{ when(exam.available_from) }}</span>
          </template>
          <template v-else-if="state(exam) === 'done'">
            <span v-if="exam.my_attempt.status === 'submitted'" class="rounded-full bg-amber-500/15 px-2.5 py-1 text-xs font-semibold text-amber-700 dark:text-amber-300">منتظر تصحیح استاد</span>
            <span class="ms-auto text-sm font-semibold text-primary-600 group-hover:underline">مشاهده‌ی کارنامه ←</span>
          </template>
          <span v-else class="rounded-full bg-gray-500/15 px-2.5 py-1 text-xs font-semibold text-gray-600 dark:text-gray-300">مهلت شرکت تمام شده</span>
        </div>
      </NuxtLink>
    </div>
  </div>
</template>
