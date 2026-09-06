<script setup lang="ts">
const props = defineProps<{
  /** Dates (any Date instances) that should be marked as having a session. */
  markedDates: Date[]
}>()

const emit = defineEmits<{ selectDay: [date: Date] }>()

const { fromGregorian, toGregorianDate, weekdayIndex, monthLength, isSameDay } = useJalali()

const today = new Date()
const todayJalali = fromGregorian(today)
const viewYear = ref(todayJalali.jy)
const viewMonth = ref(todayJalali.jm)
const selected = ref<Date | null>(null)

function prevMonth() {
  if (viewMonth.value === 1) {
    viewMonth.value = 12
    viewYear.value -= 1
  } else {
    viewMonth.value -= 1
  }
}
function nextMonth() {
  if (viewMonth.value === 12) {
    viewMonth.value = 1
    viewYear.value += 1
  } else {
    viewMonth.value += 1
  }
}

const cells = computed(() => {
  const length = monthLength(viewYear.value, viewMonth.value)
  const leadingBlanks = weekdayIndex(viewYear.value, viewMonth.value, 1)
  const days = Array.from({ length }, (_, i) => {
    const jd = i + 1
    const date = toGregorianDate(viewYear.value, viewMonth.value, jd)
    const hasSession = props.markedDates.some((m) => isSameDay(m, date))
    return { jd, date, hasSession, isToday: isSameDay(date, today) }
  })
  return { leadingBlanks, days }
})

function selectDay(date: Date) {
  selected.value = date
  emit('selectDay', date)
}
</script>

<template>
  <div>
    <div class="flex items-center justify-between">
      <button type="button" class="glass flex h-8 w-8 items-center justify-center rounded-full text-gray-700 dark:text-gray-200" @click="nextMonth">›</button>
      <p class="text-sm font-semibold text-gray-900 dark:text-white">{{ JALALI_MONTH_NAMES[viewMonth - 1] }} {{ toPersianDigits(viewYear) }}</p>
      <button type="button" class="glass flex h-8 w-8 items-center justify-center rounded-full text-gray-700 dark:text-gray-200" @click="prevMonth">‹</button>
    </div>

    <div class="mt-4 grid grid-cols-7 gap-1 text-center text-xs text-gray-500 dark:text-gray-400">
      <span v-for="d in JALALI_WEEKDAY_NAMES" :key="d">{{ d }}</span>
    </div>
    <div class="mt-1 grid grid-cols-7 gap-1">
      <div v-for="n in cells.leadingBlanks" :key="`blank-${n}`" />
      <button
        v-for="cell in cells.days"
        :key="cell.jd"
        type="button"
        class="relative flex aspect-square items-center justify-center rounded-lg text-sm transition"
        :class="[
          selected && isSameDay(selected, cell.date) ? 'bg-primary-600 text-white' : cell.isToday ? 'glass font-bold text-primary-700 dark:text-primary-300' : 'text-gray-700 hover:bg-white/40 dark:text-gray-200 dark:hover:bg-white/10',
        ]"
        @click="selectDay(cell.date)"
      >
        {{ toPersianDigits(cell.jd) }}
        <span v-if="cell.hasSession" class="absolute bottom-1 h-1.5 w-1.5 rounded-full bg-accent-500" />
      </button>
    </div>
  </div>
</template>
