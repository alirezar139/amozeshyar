<script setup lang="ts">
definePageMeta({ layout: 'admin' })
const { request } = useApi()
const { isSameDay } = useJalali()

const { data: sessions, pending, refresh } = await useAsyncData('admin-schedule', async () => {
  const page = await request<{ results: any[] }>('/class-sessions/')
  return page.results
    .map((s: any) => ({ ...s, startsAt: new Date(s.starts_at) }))
    .sort((a: any, b: any) => a.startsAt.getTime() - b.startsAt.getTime())
})

const { data: courses } = await useAsyncData('admin-schedule-courses', async () => {
  const page = await request<{ results: any[] }>('/courses/admin-all/')
  return page.results
})

const markedDates = computed(() => (sessions.value ?? []).map((s: any) => s.startsAt))
const selectedDay = ref<Date | null>(null)

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
    Object.assign(form, { course: null, title: '', starts_at: '', is_online: true, location_note: '' })
    showCreateForm.value = false
    await refresh()
  } catch (err) {
    createError.value = getErrorMessage(err, 'ثبت کلاس ناموفق بود.')
  } finally {
    creating.value = false
  }
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
        <input v-model="form.starts_at" type="datetime-local" required class="glass rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white">
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

    <div v-if="pending" class="mt-6 text-gray-500">در حال بارگذاری...</div>
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
              <span>{{ session.startsAt.toLocaleDateString('fa-IR') }}</span>
              <span>{{ formatTime(session.startsAt) }}</span>
              <span v-if="session.is_online" class="text-primary-600 dark:text-primary-400">آنلاین</span>
            </div>
            <NuxtLink
              v-if="session.is_online"
              :to="`/classroom/${session.id}`"
              class="mt-3 inline-flex items-center gap-1.5 rounded-md bg-primary-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-primary-500"
            >
              پیوستن به کلاس آنلاین
            </NuxtLink>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
