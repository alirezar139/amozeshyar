<script setup lang="ts">
// The exam clock: time left as a big countdown plus the wall-clock time it
// ends at. Turns amber under 5 minutes and red (pulsing) under 1 minute.
const props = defineProps<{ ms: number | null; endsAt?: string | null; label?: string; size?: 'lg' | 'sm' }>()

const tone = computed(() => {
  if (props.ms === null) return 'calm'
  if (props.ms <= 60_000) return 'danger'
  if (props.ms <= 5 * 60_000) return 'warn'
  return 'calm'
})
</script>

<template>
  <div
    :class="[
      'flex items-center gap-2.5 rounded-xl font-bold tabular-nums ring-1 transition-colors',
      size === 'sm' ? 'px-2.5 py-1 text-sm' : 'px-4 py-2 text-lg',
      tone === 'danger' ? 'animate-pulse bg-red-500/15 text-red-700 ring-red-500/40 dark:text-red-300'
      : tone === 'warn' ? 'bg-amber-500/15 text-amber-700 ring-amber-500/40 dark:text-amber-300'
      : 'bg-primary-500/10 text-primary-700 ring-primary-500/20 dark:text-primary-300',
    ]"
    role="timer"
    :aria-label="label"
  >
    <svg :class="size === 'sm' ? 'h-4 w-4' : 'h-5 w-5'" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
    <span v-if="ms === null">بدون محدودیت زمان</span>
    <span v-else dir="ltr">{{ formatCountdown(ms) }}</span>
    <span v-if="endsAt && ms !== null && size !== 'sm'" class="border-s border-current/20 ps-2.5 text-xs font-medium opacity-80">
      {{ label ?? 'پایان' }} ساعت {{ clockTime(endsAt) }}
    </span>
  </div>
</template>
