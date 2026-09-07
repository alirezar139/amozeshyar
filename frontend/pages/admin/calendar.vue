<script setup lang="ts">
definePageMeta({ layout: 'admin' })
const { request } = useApi()
const { isSameDay, formatGregorianDate } = useJalali()

// The three fetches below are independent of each other, so they're
// kicked off together and awaited as a group instead of one `await`
// per useAsyncData — three sequential round-trips (each one only
// starting once the previous fully finishes) added up to three times
// the wait for no reason, which is exactly what made this page feel
// like it was hanging on a slow connection.
const sessionsAsync = useAsyncData('admin-schedule', async () => {
  const page = await request<{ results: any[] }>('/class-sessions/')
  return page.results
    .map((s: any) => ({ ...s, startsAt: new Date(s.starts_at) }))
    .sort((a: any, b: any) => a.startsAt.getTime() - b.startsAt.getTime())
})
const instructorReportAsync = useAsyncData('admin-instructor-class-report', () =>
  request<{ instructor_id: number; instructor_name: string; total_sessions: number; past_sessions: number; upcoming_sessions: number }[]>(
    '/reports/instructor-classes/'
  )
)
const coursesAsync = useAsyncData('admin-schedule-courses', async () => {
  const page = await request<{ results: any[] }>('/courses/admin-all/')
  return page.results
})

await Promise.all([sessionsAsync, instructorReportAsync, coursesAsync])

const { data: sessions, pending, error: sessionsError, refresh } = sessionsAsync
const { data: instructorReport } = instructorReportAsync
const { data: courses } = coursesAsync

const markedDates = computed(() => (sessions.value ?? []).map((s: any) => s.startsAt))
const selectedDay = ref<Date | null>(null)
const dateBounds = dateTimeLocalBounds()

// Creating a session needs a course (a session always belongs to one) —
// the calendar itself has no course context, so this is the one extra
// field a course's own lesson-management page doesn't need to ask for.
const showCreateForm = ref(false)
const form = reactive({ course: null as number | null, title: '', starts_at: '', is_online: true, location_note: '' })
const creating = ref(false)
const createError = ref('')

function openCreateForm() {
  showCreateForm.value = true
  createError.value = ''
  if (selectedDay.value) {
    const d = selectedDay.value
    const pad = (n: number) => String(n).padStart(2, '0')
    form.starts_at = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T09:00`
  }
}

async function createSession() {
  createError.value = ''
  creating.value = true
  try {
    await request('/class-sessions/', {
      method: 'POST',
      body: {
        course: form.course,
        title: form.title,
        starts_at: new Date(form.starts_at).toISOString(),
        is_online: form.is_online,
        location_note: form.location_note,
      },
    })
  } catch (err) {
    createError.value = getErrorMessage(err, 'ثبت کلاس ناموفق بود.')
    creating.value = false
    return
  }
  // The class is already created at this point — closing the form and
  // resetting it shouldn't depend on the refresh below succeeding, and a
  // refresh failure shouldn't be reported as "creating failed" (it
  // didn't) nor go unnoticed just because the form that used to show
  // errors is now closed.
  Object.assign(form, { course: null, title: '', starts_at: '', is_online: true, location_note: '' })
  showCreateForm.value = false
  creating.value = false
  refresh().catch(() => {})
}

const visibleSessions = computed(() => {
  const list = sessions.value ?? []
  if (!selectedDay.value) return list
  return list.filter((s: any) => isSameDay(s.startsAt, selectedDay.value!))
})

function formatTime(date: Date) {
  return date.toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit' })
}
function clearFilter() {
  selectedDay.value = null
}

const copiedId = ref<number | null>(null)
async function copyLink(id: number) {
  await navigator.clipboard.writeText(`${window.location.origin}/classroom/${id}`)
  copiedId.value = id
  setTimeout(() => {
    if (copiedId.value === id) copiedId.value = null
  }, 2000)
}
</script>

<template>
  <div>
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-xl font-bold text-gray-900 dark:text-white">تقویم کلاس‌های سامانه</h1>
      <div class="flex gap-2">
        <button v-if="selectedDay" type="button" class="glass rounded-md px-3 py-1.5 text-sm text-gray-700 dark:text-gray-200" @click="clearFilter">
          نمایش همه ✕
        </button>
        <button type="button" class="rounded-md bg-primary-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-primary-500" @click="openCreateForm">
          + افزودن کلاس
        </button>
      </div>
    </div>
    <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">تمام کلاس‌های زمان‌بندی‌شده در همه‌ی دوره‌ها.</p>

    <div v-if="showCreateForm" class="glass mt-4 rounded-2xl p-5">
      <h2 class="text-sm font-semibold text-gray-900 dark:text-white">کلاس جدید</h2>
      <form class="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2" @submit.prevent="createSession">
        <select v-model.number="form.course" required class="glass rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white sm:col-span-2">
          <option :value="null" disabled>انتخاب دوره</option>
          <option v-for="c in courses" :key="c.id" :value="c.id">{{ c.title }}</option>
        </select>
        <input
          v-model="form.title"
          required
          placeholder="عنوان کلاس، مثلاً «جلسه‌ی پرسش و پاسخ زنده»"
          class="glass rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white sm:col-span-2"
        >
        <input v-model="form.starts_at" type="datetime-local" required :min="dateBounds.min" :max="dateBounds.max" class="glass rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white">
        <label class="glass flex items-center gap-2 rounded-md px-3 py-2 text-sm text-gray-700 dark:text-gray-200">
          <input v-model="form.is_online" type="checkbox" class="h-4 w-4">
          کلاس آنلاین است
        </label>
        <input
          v-model="form.location_note"
          :placeholder="form.is_online ? 'توضیح اضافه (اختیاری)' : 'آدرس محل برگزاری'"
          class="glass rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white sm:col-span-2"
        >
        <p v-if="createError" class="text-sm text-red-600 sm:col-span-2">{{ createError }}</p>
        <div class="flex gap-2 sm:col-span-2">
          <button type="submit" :disabled="creating" class="rounded-md bg-primary-600 px-5 py-2 text-sm font-semibold text-white hover:bg-primary-500 disabled:opacity-50">
            {{ creating ? 'در حال ثبت...' : 'ثبت کلاس' }}
          </button>
          <button type="button" class="glass rounded-md px-5 py-2 text-sm text-gray-700 dark:text-gray-200" @click="showCreateForm = false">
            انصراف
          </button>
        </div>
      </form>
    </div>

    <!-- Only the very first load ever blocks on `pending` — once we have
         a list at all, a later refresh() (e.g. after creating a class)
         updates it in place instead of hiding everything behind a
         spinner again, so a slow or failed background refresh can never
         strand the page on "در حال بارگذاری..." forever. -->
    <div v-if="pending && !sessions" class="mt-6 text-gray-500">در حال بارگذاری...</div>
    <div v-else-if="sessionsError" class="mt-6">
      <p class="text-sm text-red-600">بارگذاری تقویم ناموفق بود.</p>
      <button type="button" class="glass mt-2 rounded-md px-3 py-1.5 text-sm text-gray-700 dark:text-gray-200" @click="refresh()">
        تلاش دوباره
      </button>
    </div>
    <div v-else class="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-[320px_1fr]">
      <div data-tour="admin-calendar-grid" class="glass rounded-2xl p-5">
        <ScheduleMonthCalendar :marked-dates="markedDates" @select-day="(d) => (selectedDay = d)" />
      </div>

      <div data-tour="admin-calendar-sessions">
        <h2 class="text-sm font-semibold text-gray-900 dark:text-white">
          {{ selectedDay ? 'کلاس‌های این روز' : 'همه‌ی کلاس‌های زمان‌بندی‌شده' }}
        </h2>
        <p v-if="!sessions?.length" class="mt-4 text-sm text-gray-500 dark:text-gray-400">
          هنوز هیچ کلاسی در سامانه زمان‌بندی نشده است.
        </p>
        <p v-else-if="!visibleSessions.length" class="mt-4 text-sm text-gray-500 dark:text-gray-400">
          برای این روز کلاسی زمان‌بندی نشده است.
        </p>
        <div v-else class="mt-4 space-y-3">
          <div v-for="session in visibleSessions" :key="session.id" class="glass rounded-xl p-4">
            <p class="font-semibold text-gray-900 dark:text-white">{{ session.title }}</p>
            <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">{{ session.course_title }} — {{ session.instructor_name }}</p>
            <div class="mt-3 flex flex-wrap items-center gap-4 text-sm text-gray-600 dark:text-gray-300">
              <span>{{ formatGregorianDate(session.startsAt) }}</span>
              <span>{{ formatTime(session.startsAt) }}</span>
              <span v-if="session.is_online" class="text-primary-600 dark:text-primary-400">آنلاین</span>
            </div>
            <div v-if="session.is_online" class="mt-3 flex flex-wrap gap-2">
              <NuxtLink
                :to="`/classroom/${session.id}`"
                class="inline-flex items-center gap-1.5 rounded-md bg-primary-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-primary-500"
              >
                پیوستن به کلاس آنلاین
              </NuxtLink>
              <button
                type="button"
                class="glass rounded-md px-4 py-1.5 text-sm text-gray-700 dark:text-gray-200"
                @click="copyLink(session.id)"
              >
                {{ copiedId === session.id ? 'کپی شد ✓' : 'کپی لینک' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="instructorReport?.length" class="mt-8">
      <h2 class="text-sm font-semibold text-gray-900 dark:text-white">گزارش کلاس‌های هر مدرس</h2>
      <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">فقط مدرس‌هایی که حداقل یک کلاس زمان‌بندی کرده‌اند.</p>
      <div class="glass mt-3 overflow-x-auto rounded-xl p-2">
        <table class="w-full min-w-[420px] text-sm">
          <thead>
            <tr class="text-start text-gray-600 dark:text-gray-400">
              <th class="px-3 py-2">مدرس</th>
              <th class="px-3 py-2">کل کلاس‌ها</th>
              <th class="px-3 py-2">برگزارشده</th>
              <th class="px-3 py-2">پیش رو</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in instructorReport" :key="row.instructor_id" class="border-t border-white/30 dark:border-white/10">
              <td class="px-3 py-2 text-gray-900 dark:text-white">{{ row.instructor_name }}</td>
              <td class="px-3 py-2 text-gray-600 dark:text-gray-400">{{ row.total_sessions }}</td>
              <td class="px-3 py-2 text-gray-600 dark:text-gray-400">{{ row.past_sessions }}</td>
              <td class="px-3 py-2 text-gray-600 dark:text-gray-400">{{ row.upcoming_sessions }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
