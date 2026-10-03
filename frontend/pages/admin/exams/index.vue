<script setup lang="ts">
// The teacher's exams across all courses: create one, then open it to add
// questions; publish/unpublish and jump to the results.
definePageMeta({ layout: 'admin' })
useSeoMeta({ title: 'آزمون‌ها' })

const { request } = useApi()
const { formatGregorianDate } = useJalali()

interface ExamRow {
  id: number
  course: number
  course_title: string
  title: string
  status: 'draft' | 'published'
  available_from: string | null
  available_until: string | null
  duration_minutes: number | null
  question_count: number
  total_points: number
  attempt_count: number
  pending_count: number
}

const examsAsync = useAsyncData('admin-exams', () => request<ExamRow[]>('/exams/manage/'))
const coursesAsync = useAsyncData('admin-exam-courses', async () => (await request<{ results: any[] }>('/courses/manage/')).results)
await Promise.all([examsAsync, coursesAsync])
const { data: exams, pending, refresh } = examsAsync
const { data: courses } = coursesAsync

// One course picker: it filters the list and is the course a new exam goes into.
const course = ref<number | ''>('')
const visible = computed(() => (exams.value ?? []).filter((e) => !course.value || e.course === course.value))

const creating = ref(false)
const title = ref('')
const error = ref('')

async function create() {
  if (!title.value.trim()) return
  error.value = ''
  if (!course.value) {
    error.value = 'برای ساخت آزمون، اول دوره‌ی آن را انتخاب کنید.'
    return
  }
  creating.value = true
  try {
    const exam = await request<ExamRow>('/exams/manage/', { method: 'POST', body: { course: course.value, title: title.value.trim() } })
    await navigateTo(`/admin/exams/${exam.id}`)
  } catch (err) {
    error.value = getFirstErrorMessage(err, 'ساخت آزمون ناموفق بود.')
  } finally {
    creating.value = false
  }
}

const busyId = ref<number | null>(null)
async function toggleStatus(exam: ExamRow) {
  busyId.value = exam.id
  error.value = ''
  try {
    await request(`/exams/manage/${exam.id}/`, { method: 'PATCH', body: { status: exam.status === 'published' ? 'draft' : 'published' } })
    await refresh()
  } catch (err) {
    error.value = getFirstErrorMessage(err, 'تغییر وضعیت ناموفق بود.')
  } finally {
    busyId.value = null
  }
}

async function remove(exam: ExamRow) {
  const warning = exam.attempt_count ? ` نتایج ${toPersianDigits(exam.attempt_count)} شرکت‌کننده هم پاک می‌شود.` : ''
  if (!confirm(`آزمون «${exam.title}» حذف شود؟${warning}`)) return
  await request(`/exams/manage/${exam.id}/`, { method: 'DELETE' })
  await refresh()
}

function windowLabel(exam: ExamRow) {
  const now = Date.now()
  if (exam.available_from && Date.parse(exam.available_from) > now) return `شروع: ${formatGregorianDate(new Date(exam.available_from))} ساعت ${clockTime(exam.available_from)}`
  if (exam.available_until) {
    return Date.parse(exam.available_until) > now
      ? `تا ${formatGregorianDate(new Date(exam.available_until))} ساعت ${clockTime(exam.available_until)}`
      : 'بسته شده'
  }
  return 'همیشه باز'
}
</script>

<template>
  <div>
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-xl font-bold text-gray-900 dark:text-white">آزمون‌ها</h1>
        <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">آزمون زمان‌دار بسازید؛ سوال‌های گزینه‌ای و پاسخ کوتاه خودکار تصحیح می‌شوند.</p>
      </div>
    </div>

    <form class="glass mt-6 flex flex-wrap items-end gap-3 rounded-2xl p-4" @submit.prevent="create">
      <label class="text-sm text-gray-700 dark:text-gray-200">
        دوره
        <select v-model="course" class="glass mt-1 block w-56 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white">
          <option value="">همه‌ی دوره‌ها</option>
          <option v-for="c in courses ?? []" :key="c.id" :value="c.id">{{ c.title }}</option>
        </select>
      </label>
      <label class="min-w-[14rem] flex-1 text-sm text-gray-700 dark:text-gray-200">
        عنوان آزمون
        <input v-model="title" required placeholder="مثلاً آزمون فصل ۱" class="glass mt-1 block w-full rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white">
      </label>
      <button type="submit" :disabled="creating" class="rounded-xl bg-primary-600 px-5 py-2 text-sm font-semibold text-white hover:bg-primary-700 disabled:opacity-50">
        {{ creating ? 'در حال ساخت…' : '+ آزمون جدید' }}
      </button>
    </form>
    <p v-if="error" class="mt-3 text-sm text-red-600">{{ error }}</p>

    <div v-if="pending && !exams" class="mt-6 text-gray-500">در حال بارگذاری...</div>
    <div v-else-if="!visible.length" class="glass mt-6 rounded-2xl p-8 text-center text-gray-600 dark:text-gray-300">هنوز آزمونی ساخته نشده است.</div>
    <div v-else class="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      <article v-for="exam in visible" :key="exam.id" class="glass flex flex-col rounded-2xl p-5">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <p class="text-xs text-primary-700 dark:text-primary-300">{{ exam.course_title }}</p>
            <h2 class="mt-1 truncate text-lg font-bold text-gray-900 dark:text-white">{{ exam.title }}</h2>
          </div>
          <span
            :class="[
              'shrink-0 rounded-full px-2.5 py-0.5 text-xs font-semibold',
              exam.status === 'published' ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300' : 'bg-gray-500/15 text-gray-600 dark:text-gray-300',
            ]"
          >
            {{ exam.status === 'published' ? 'منتشرشده' : 'پیش‌نویس' }}
          </span>
        </div>
        <dl class="mt-4 grid grid-cols-3 gap-2 text-center">
          <div class="rounded-xl bg-black/[0.03] py-2 dark:bg-white/5">
            <dt class="text-[11px] text-gray-500">سوال</dt>
            <dd class="font-bold text-gray-900 dark:text-white">{{ toPersianDigits(exam.question_count) }}</dd>
          </div>
          <div class="rounded-xl bg-black/[0.03] py-2 dark:bg-white/5">
            <dt class="text-[11px] text-gray-500">نمره</dt>
            <dd class="font-bold text-gray-900 dark:text-white">{{ toPersianDigits(exam.total_points) }}</dd>
          </div>
          <div class="rounded-xl bg-black/[0.03] py-2 dark:bg-white/5">
            <dt class="text-[11px] text-gray-500">زمان</dt>
            <dd class="font-bold text-gray-900 dark:text-white">{{ exam.duration_minutes ? `${toPersianDigits(exam.duration_minutes)}′` : '∞' }}</dd>
          </div>
        </dl>
        <p class="mt-3 text-xs text-gray-600 dark:text-gray-400">⏱ {{ windowLabel(exam) }}</p>
        <div class="mt-auto flex flex-wrap items-center gap-2 pt-4">
          <NuxtLink :to="`/admin/exams/${exam.id}`" class="rounded-lg bg-primary-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-primary-700">ویرایش سوال‌ها</NuxtLink>
          <NuxtLink :to="`/admin/exams/${exam.id}/results`" class="relative rounded-lg border border-black/10 px-3 py-1.5 text-xs font-semibold text-gray-700 hover:border-primary-400 dark:border-white/10 dark:text-gray-200">
            نتایج ({{ toPersianDigits(exam.attempt_count) }})
            <span v-if="exam.pending_count" class="absolute -end-2 -top-2 flex h-5 min-w-5 items-center justify-center rounded-full bg-amber-500 px-1 text-[10px] font-bold text-white" :title="`${exam.pending_count} نفر منتظر تصحیح`">{{ toPersianDigits(exam.pending_count) }}</span>
          </NuxtLink>
          <button type="button" :disabled="busyId === exam.id" class="rounded-lg px-3 py-1.5 text-xs text-gray-600 hover:bg-black/5 dark:text-gray-300 dark:hover:bg-white/10" @click="toggleStatus(exam)">
            {{ exam.status === 'published' ? 'لغو انتشار' : 'انتشار' }}
          </button>
          <button type="button" class="ms-auto rounded-lg px-2 py-1.5 text-xs text-red-600 hover:bg-red-500/10" @click="remove(exam)">حذف</button>
        </div>
      </article>
    </div>
  </div>
</template>
