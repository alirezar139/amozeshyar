<script setup lang="ts">
definePageMeta({ layout: 'dashboard' })
const { request } = useApi()
const { isSameDay, formatGregorianDate } = useJalali()

const { data: sessions, pending } = await useAsyncData('student-schedule', async () => {
  const page = await request<{ results: any[] }>('/schedule/upcoming/')
  return page.results.map((s: any) => ({ ...s, startsAt: new Date(s.starts_at) }))
})

const markedDates = computed(() => (sessions.value ?? []).map((s: any) => s.startsAt))
const selectedDay = ref<Date | null>(null)

const visibleSessions = computed(() => {
  const list = sessions.value ?? []
  if (!selectedDay.value) return list
  return list.filter((s: any) => isSameDay(s.startsAt, selectedDay.value!))
})

function hoursUntil(date: Date) {
  return (date.getTime() - Date.now()) / (1000 * 60 * 60)
}

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
      <h1 class="text-xl font-bold text-gray-900 dark:text-white">تقویم کلاس‌ها</h1>
      <button v-if="selectedDay" type="button" class="glass rounded-md px-3 py-1.5 text-sm text-gray-700 dark:text-gray-200" @click="clearFilter">
        نمایش همه ✕
      </button>
    </div>

    <div v-if="pending" class="mt-6 text-gray-500">در حال بارگذاری...</div>
    <div v-else class="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-[320px_1fr]">
      <div data-tour="student-calendar" class="glass rounded-2xl p-5">
        <ScheduleMonthCalendar :marked-dates="markedDates" @select-day="(d) => (selectedDay = d)" />
      </div>

      <div data-tour="upcoming-sessions">
        <h2 class="text-sm font-semibold text-gray-900 dark:text-white">
          {{ selectedDay ? 'جلسات این روز' : 'جلسات پیش رو' }}
        </h2>
        <p v-if="!sessions?.length" class="mt-4 text-sm text-gray-500 dark:text-gray-400">
          فعلاً هیچ کلاس زمان‌بندی‌شده‌ای برای دوره‌های شما ثبت نشده است.
        </p>
        <p v-else-if="!visibleSessions.length" class="mt-4 text-sm text-gray-500 dark:text-gray-400">
          برای این روز کلاسی زمان‌بندی نشده است.
        </p>
        <div v-else class="mt-4 space-y-3">
          <div v-for="session in visibleSessions" :key="session.id" class="glass rounded-xl p-4">
            <div class="flex flex-wrap items-start justify-between gap-2">
              <div>
                <p class="font-semibold text-gray-900 dark:text-white">{{ session.title }}</p>
                <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">{{ session.course_title }} — {{ session.instructor_name }}</p>
              </div>
              <span
                v-if="hoursUntil(session.startsAt) <= 24"
                class="glass rounded-full px-3 py-1 text-xs font-semibold text-accent-600 dark:text-accent-400"
              >
                به‌زودی
              </span>
            </div>
            <div class="mt-3 flex flex-wrap items-center gap-4 text-sm text-gray-600 dark:text-gray-300">
              <span class="flex items-center gap-1.5">
                <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
                {{ formatGregorianDate(session.startsAt) }}
              </span>
              <span class="flex items-center gap-1.5">
                <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                {{ formatTime(session.startsAt) }}
              </span>
              <span v-if="session.is_online" class="flex items-center gap-1.5 text-primary-600 dark:text-primary-400">
                آنلاین
              </span>
            </div>
            <p v-if="session.location_note" class="mt-2 text-sm text-gray-500 dark:text-gray-400">{{ session.location_note }}</p>
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
