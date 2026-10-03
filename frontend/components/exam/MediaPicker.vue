<script setup lang="ts">
// Add an image, an audio file, or record a voice clip right in the browser.
// Emits each picked/recorded file; the parent uploads it.
const props = defineProps<{ disabled?: boolean; busy?: boolean }>()
const emit = defineEmits<{ pick: [file: File, durationSeconds: number | null] }>()

const BUTTON = 'rounded-lg border border-black/10 bg-white/50 px-3 py-1.5 text-xs font-medium text-gray-700 transition hover:border-primary-400 hover:text-primary-700 disabled:cursor-not-allowed disabled:opacity-50 dark:border-white/10 dark:bg-white/5 dark:text-gray-200'
const error = ref('')
const imageInput = ref<HTMLInputElement | null>(null)
const audioInput = ref<HTMLInputElement | null>(null)

function onFile(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) emit('pick', file, null)
  input.value = ''
}

// ---------- voice recording ----------
const recording = ref(false)
const seconds = ref(0)
let recorder: MediaRecorder | null = null
let chunks: Blob[] = []
let stream: MediaStream | null = null
let timer: ReturnType<typeof setInterval> | null = null
let cancelled = false

function pickMime() {
  const options = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4']
  return options.find((m) => typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported(m)) ?? ''
}

async function startRecording() {
  error.value = ''
  if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
    error.value = 'مرورگر شما از ضبط صدا پشتیبانی نمی‌کند.'
    return
  }
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true })
  } catch {
    error.value = 'اجازه‌ی دسترسی به میکروفون داده نشد؛ لطفاً آن را در تنظیمات مرورگر فعال کنید.'
    return
  }
  const mimeType = pickMime()
  recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
  chunks = []
  cancelled = false
  recorder.ondataavailable = (e) => e.data.size && chunks.push(e.data)
  recorder.onstop = () => {
    stream?.getTracks().forEach((t) => t.stop())
    stream = null
    if (cancelled || !chunks.length) return
    const type = recorder?.mimeType || mimeType || 'audio/webm'
    const ext = type.includes('mp4') ? 'm4a' : type.includes('ogg') ? 'ogg' : 'webm'
    emit('pick', new File(chunks, `voice-${Date.now()}.${ext}`, { type }), seconds.value)
  }
  recorder.start()
  recording.value = true
  seconds.value = 0
  timer = setInterval(() => {
    seconds.value++
    if (seconds.value >= 600) stopRecording() // 10-minute cap
  }, 1000)
}

function stopRecording(cancel = false) {
  cancelled = cancel
  if (timer) clearInterval(timer)
  timer = null
  recording.value = false
  if (recorder && recorder.state !== 'inactive') recorder.stop()
}

// Time ran out mid-recording: keep what was said.
watch(() => props.disabled, (disabled) => disabled && recording.value && stopRecording())
onBeforeUnmount(() => stopRecording(true))
</script>

<template>
  <div>
    <div v-if="recording" class="flex items-center gap-3 rounded-xl bg-red-500/10 px-3 py-2">
      <span class="h-2.5 w-2.5 animate-pulse rounded-full bg-red-600" />
      <span class="text-sm font-semibold tabular-nums text-red-700 dark:text-red-300" dir="ltr">{{ formatCountdown(seconds * 1000) }}</span>
      <span class="text-xs text-gray-600 dark:text-gray-400">در حال ضبط…</span>
      <button type="button" class="ms-auto rounded-lg px-2.5 py-1 text-xs text-gray-600 hover:bg-black/5 dark:text-gray-300 dark:hover:bg-white/10" @click="stopRecording(true)">لغو</button>
      <button type="button" class="rounded-lg bg-red-600 px-3 py-1 text-xs font-semibold text-white hover:bg-red-700" @click="stopRecording()">پایان و افزودن</button>
    </div>
    <div v-else class="flex flex-wrap gap-2">
      <button type="button" :class="BUTTON" :disabled="disabled || busy" @click="imageInput?.click()">📷 عکس</button>
      <button type="button" :class="BUTTON" :disabled="disabled || busy" @click="audioInput?.click()">🎵 فایل صوتی</button>
      <button type="button" :class="BUTTON" :disabled="disabled || busy" @click="startRecording">🎤 ضبط صدا</button>
      <span v-if="busy" class="self-center text-xs text-gray-500">در حال آپلود…</span>
    </div>
    <input ref="imageInput" type="file" accept="image/jpeg,image/png,image/webp,image/gif" class="hidden" @change="onFile">
    <input ref="audioInput" type="file" accept="audio/*" class="hidden" @change="onFile">
    <p v-if="error" class="mt-1 text-xs text-red-600">{{ error }}</p>
  </div>
</template>

