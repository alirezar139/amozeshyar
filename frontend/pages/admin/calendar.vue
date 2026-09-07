<script setup lang="ts">
definePageMeta({ layout: 'admin' })
const { request } = useApi()
const { isSameDay } = useJalali()

const { data: sessions, pending } = await useAsyncData('admin-schedule', async () => {
  const page = await request<{ results: any[] }>('/class-sessions/')
  return page.results
    .map((s: any) => ({ ...s, startsAt: new Date(s.starts_at) }))
    .sort((a: any, b: any) => a.startsAt.getTime() - b.startsAt.getTime())
})

const markedDates = computed(() => (sessions.value ?? []).map((s: any) => s.startsAt))
const selectedDay = ref<Date | null>(null)

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
      <button v-if="selectedDay" type="button" class="glass rounded-md px-3 py-1.5 text-sm text-gray-700 dark:text-gray-200" @click="clearFilter">
        نمایش همه ✕
      </button>
    </div>
    <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">تمام کلاس‌های زمان‌بندی‌شده در همه‌ی دوره‌ها.</p>

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
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
