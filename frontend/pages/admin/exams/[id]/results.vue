<script setup lang="ts">
// Results of one exam as a ranked table (score, then time taken), with each
// attempt opening in a panel for grading essay answers. Deleting an attempt
// lets that student take the exam again.
definePageMeta({ layout: 'admin', ssr: false })

const route = useRoute()
const { request } = useApi()
const examId = Number(route.params.id)

const examAsync = useAsyncData(`admin-exam-${examId}-meta`, () => request<any>(`/exams/manage/${examId}/`))
const attemptsAsync = useAsyncData(`admin-exam-${examId}-attempts`, () => request<any[]>(`/exams/manage/${examId}/attempts/`))
await Promise.all([examAsync, attemptsAsync])
const { data: exam } = examAsync
const { data: attempts, pending, refresh } = attemptsAsync
useSeoMeta({ title: () => `نتایج ${exam.value?.title ?? 'آزمون'}` })

const spentMs = (a: any) => (a.submitted_at ? Date.parse(a.submitted_at) - Date.parse(a.started_at) : null)
const ranked = computed(() =>
  [...(attempts.value ?? [])].sort((a, b) =>
    Number(b.score) - Number(a.score) || (spentMs(a) ?? Infinity) - (spentMs(b) ?? Infinity),
  ),
)
const stats = computed(() => {
  const done = ranked.value.filter((a) => a.status !== 'in_progress')
  const avg = done.length ? done.reduce((s, a) => s + a.percent, 0) / done.length : 0
  return {
    count: ranked.value.length,
    avg: Math.round(avg),
    passed: done.filter((a) => a.percent >= (exam.value?.pass_percent ?? 0)).length,
    pending: ranked.value.filter((a) => a.status === 'submitted').length,
  }
})

const STATUS: Record<string, { label: string; class: string }> = {
  in_progress: { label: 'در حال آزمون', class: 'bg-sky-500/15 text-sky-700 dark:text-sky-300' },
  submitted: { label: 'منتظر تصحیح', class: 'bg-amber-500/15 text-amber-700 dark:text-amber-300' },
  graded: { label: 'تصحیح‌شده', class: 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300' },
}

// ---------- detail panel ----------
const open = ref<any>(null)
const loadingId = ref<number | null>(null)
async function openAttempt(id: number) {
  loadingId.value = id
  try {
    open.value = await request<any>(`/exam-attempts/manage/${id}/`)
  } finally {
    loadingId.value = null
  }
}
async function onGraded(updated: any) {
  open.value = updated
  await refresh()
}
async function allowRetake(a: any) {
  if (!confirm(`پاسخ‌های ${a.student_name} پاک شود تا بتواند دوباره در آزمون شرکت کند؟`)) return
  await request(`/exam-attempts/manage/${a.id}/`, { method: 'DELETE' })
  open.value = null
  await refresh()
}
</script>

<template>
  <div class="mx-auto max-w-6xl">
    <NuxtLink :to="`/admin/exams/${examId}`" class="text-sm text-primary-600 hover:underline dark:text-primary-400">→ ویرایش آزمون</NuxtLink>
    <h1 class="mt-3 text-2xl font-extrabold text-gray-900 dark:text-white">نتایج «{{ exam?.title }}»</h1>

    <dl class="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
      <div class="glass rounded-2xl p-4">
        <dt class="text-xs text-gray-500">شرکت‌کننده</dt>
        <dd class="mt-1 text-2xl font-extrabold text-gray-900 dark:text-white">{{ toPersianDigits(stats.count) }}</dd>
      </div>
      <div class="glass rounded-2xl p-4">
        <dt class="text-xs text-gray-500">میانگین</dt>
        <dd class="mt-1 text-2xl font-extrabold text-gray-900 dark:text-white">{{ toPersianDigits(stats.avg) }}٪</dd>
      </div>
      <div class="glass rounded-2xl p-4">
        <dt class="text-xs text-gray-500">قبول‌شده</dt>
        <dd class="mt-1 text-2xl font-extrabold text-emerald-600">{{ toPersianDigits(stats.passed) }}</dd>
      </div>
      <div class="glass rounded-2xl p-4">
        <dt class="text-xs text-gray-500">منتظر تصحیح</dt>
        <dd class="mt-1 text-2xl font-extrabold text-amber-600">{{ toPersianDigits(stats.pending) }}</dd>
      </div>
    </dl>

    <div v-if="pending && !attempts" class="mt-6 text-gray-500">در حال بارگذاری...</div>
    <div v-else-if="!ranked.length" class="glass mt-6 rounded-2xl p-8 text-center text-gray-600 dark:text-gray-300">هنوز کسی در این آزمون شرکت نکرده است.</div>
    <div v-else class="glass mt-6 overflow-x-auto rounded-2xl">
      <table class="w-full min-w-[40rem] text-sm">
        <thead class="border-b border-black/5 text-xs text-gray-500 dark:border-white/10">
          <tr>
            <th class="px-4 py-3 text-start">رتبه</th>
            <th class="px-4 py-3 text-start">دانشجو</th>
            <th class="px-4 py-3 text-start">نمره</th>
            <th class="px-4 py-3 text-start">مدت</th>
            <th class="px-4 py-3 text-start">وضعیت</th>
            <th class="px-4 py-3" />
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(a, i) in ranked"
            :key="a.id"
            :class="['cursor-pointer border-b border-black/5 transition last:border-0 hover:bg-primary-500/5 dark:border-white/5', open?.id === a.id ? 'bg-primary-500/10' : '']"
            @click="openAttempt(a.id)"
          >
            <td class="px-4 py-3 font-bold text-gray-700 dark:text-gray-200">{{ ['🥇', '🥈', '🥉'][i] ?? toPersianDigits(i + 1) }}</td>
            <td class="px-4 py-3">
              <p class="font-semibold text-gray-900 dark:text-white">{{ a.student_name }}</p>
              <p class="text-xs text-gray-500" dir="ltr">{{ a.student_email }}</p>
            </td>
            <td class="px-4 py-3">
              <div class="flex items-center gap-2">
                <span class="font-bold text-gray-900 dark:text-white">{{ toPersianDigits(Number(a.score)) }}/{{ toPersianDigits(Number(a.max_score)) }}</span>
                <div class="h-1.5 w-20 overflow-hidden rounded-full bg-black/10 dark:bg-white/10">
                  <div :class="['h-full rounded-full', a.percent >= (exam?.pass_percent ?? 0) ? 'bg-emerald-500' : 'bg-red-500']" :style="{ width: `${a.percent}%` }" />
                </div>
              </div>
            </td>
            <td class="px-4 py-3 text-gray-600 dark:text-gray-300" dir="ltr">
              {{ spentMs(a) === null ? '—' : formatCountdown(spentMs(a)!) }}
              <span v-if="a.submit_reason === 'timeout'" class="ms-1 text-[11px] text-amber-600" title="زمان تمام شد و خودکار ارسال شد">⏰</span>
            </td>
            <td class="px-4 py-3">
              <span :class="['rounded-full px-2.5 py-0.5 text-xs font-semibold', STATUS[a.status].class]">
                {{ STATUS[a.status].label }}<template v-if="a.pending_count"> ({{ toPersianDigits(a.pending_count) }})</template>
              </span>
            </td>
            <td class="px-4 py-3 text-end">
              <span v-if="loadingId === a.id" class="text-xs text-gray-500">…</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- attempt panel -->
    <Teleport to="body">
      <div v-if="open" class="fixed inset-0 z-[70] flex justify-end bg-black/40 backdrop-blur-sm" @click.self="open = null">
        <aside class="h-full w-full max-w-3xl overflow-y-auto bg-white/90 p-5 shadow-2xl backdrop-blur-xl dark:bg-gray-900/95">
          <div class="flex flex-wrap items-center gap-3">
            <div>
              <h2 class="text-lg font-bold text-gray-900 dark:text-white">{{ open.student_name }}</h2>
              <p v-if="open.score !== undefined" class="text-sm text-gray-600 dark:text-gray-400">
                نمره: {{ toPersianDigits(Number(open.score)) }} از {{ toPersianDigits(Number(open.max_score)) }} ({{ toPersianDigits(open.percent) }}٪)
              </p>
              <p v-else class="text-sm text-sky-600">هنوز در حال پاسخ دادن است.</p>
            </div>
            <button type="button" class="ms-auto rounded-lg px-3 py-1.5 text-xs text-red-600 hover:bg-red-500/10" @click="allowRetake(open)">اجازه‌ی شرکت دوباره</button>
            <button type="button" class="rounded-lg p-2 text-gray-500 hover:bg-black/5 dark:hover:bg-white/10" aria-label="بستن" @click="open = null">✕</button>
          </div>
          <ExamAttemptReview v-if="open.score !== undefined" :attempt="open" grading class="mt-5" @graded="onGraded" />
        </aside>
      </div>
    </Teleport>
  </div>
</template>
