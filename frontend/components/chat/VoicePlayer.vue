<script setup lang="ts">
// Compact voice-note player for a chat bubble: play/pause, a seekable
// progress bar and the time. Colors adapt to the bubble it sits in.
const props = defineProps<{ src: string; duration?: number | null; mine?: boolean }>()

const audio = ref<HTMLAudioElement | null>(null)
const playing = ref(false)
const current = ref(0)
const total = ref(props.duration || 0)

function toggle() {
  if (!audio.value) return
  if (audio.value.paused) {
    // Only one voice note plays at a time across the page.
    document.querySelectorAll('audio').forEach((a) => a !== audio.value && a.pause())
    audio.value.play().catch(() => (playing.value = false))
  } else {
    audio.value.pause()
  }
}

function onLoaded() {
  // MediaRecorder webm files often report Infinity until fully read; keep
  // the recorder's own measurement in that case.
  const d = audio.value?.duration
  if (d && Number.isFinite(d)) total.value = d
}

function seek(e: MouseEvent) {
  if (!audio.value || !total.value) return
  const bar = e.currentTarget as HTMLElement
  const rect = bar.getBoundingClientRect()
  // RTL page, but a timeline reads left-to-right like a clock.
  const ratio = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width))
  audio.value.currentTime = ratio * total.value
}

const percent = computed(() => (total.value ? (current.value / total.value) * 100 : 0))
</script>

<template>
  <div class="flex min-w-[13rem] items-center gap-3" dir="ltr">
    <audio
      ref="audio"
      :src="src"
      preload="metadata"
      class="hidden"
      @loadedmetadata="onLoaded"
      @timeupdate="current = audio?.currentTime ?? 0"
      @play="playing = true"
      @pause="playing = false"
      @ended="playing = false; current = 0"
    />
    <button
      type="button"
      :class="[
        'flex h-10 w-10 shrink-0 items-center justify-center rounded-full transition hover:scale-105',
        mine ? 'bg-white text-primary-700' : 'bg-primary-600 text-white',
      ]"
      :aria-label="playing ? 'توقف' : 'پخش'"
      @click="toggle"
    >
      <svg v-if="playing" class="h-4 w-4" fill="currentColor" viewBox="0 0 20 20"><path d="M6 4h3v12H6zM11 4h3v12h-3z" /></svg>
      <svg v-else class="ms-0.5 h-4 w-4" fill="currentColor" viewBox="0 0 20 20"><path d="M6 4l10 6-10 6V4z" /></svg>
    </button>
    <div class="flex-1">
      <div :class="['h-1.5 cursor-pointer overflow-hidden rounded-full', mine ? 'bg-white/30' : 'bg-black/10 dark:bg-white/15']" @click="seek">
        <div :class="['h-full rounded-full', mine ? 'bg-white' : 'bg-primary-500']" :style="{ width: `${percent}%` }" />
      </div>
      <p :class="['mt-1 text-[11px] tabular-nums', mine ? 'text-white/80' : 'text-gray-500 dark:text-gray-400']">
        {{ formatDuration(playing || current ? current : total) }}
      </p>
    </div>
  </div>
</template>
