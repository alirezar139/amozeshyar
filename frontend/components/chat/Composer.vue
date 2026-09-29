<script setup lang="ts">
// Message box: text (Enter sends, Shift+Enter new line), one attached
// file/photo with an optional caption, or a recorded voice note.
const emit = defineEmits<{
  send: [payload: { text: string; file?: File; voice?: boolean; duration?: number }]
}>()
defineProps<{ disabled?: boolean }>()

const text = ref('')
const file = ref<File | null>(null)
const filePreview = ref<string | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const textarea = ref<HTMLTextAreaElement | null>(null)
const error = ref('')

function autoGrow() {
  const el = textarea.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = `${Math.min(el.scrollHeight, 160)}px`
}

function pickFile(e: Event) {
  const input = e.target as HTMLInputElement
  const picked = input.files?.[0]
  input.value = ''
  if (!picked) return
  file.value = picked
  filePreview.value = picked.type.startsWith('image/') ? URL.createObjectURL(picked) : null
  textarea.value?.focus()
}

function clearFile() {
  file.value = null
  filePreview.value = null
}

function submit() {
  const body = text.value.trim()
  if (!body && !file.value) return
  emit('send', { text: body, file: file.value ?? undefined })
  text.value = ''
  clearFile()
  nextTick(autoGrow)
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
    e.preventDefault()
    submit()
  }
}

// ---------- voice recording ----------
const recording = ref(false)
const seconds = ref(0)
let recorder: MediaRecorder | null = null
let chunks: Blob[] = []
let timer: ReturnType<typeof setInterval> | null = null
let stream: MediaStream | null = null
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
    const voice = new File(chunks, `voice-${Date.now()}.${ext}`, { type })
    emit('send', { text: '', file: voice, voice: true, duration: seconds.value })
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

onBeforeUnmount(() => stopRecording(true))
</script>

<template>
  <div class="border-t border-white/40 bg-white/60 p-3 backdrop-blur-xl dark:border-white/10 dark:bg-gray-900/60">
    <!-- pending attachment -->
    <div v-if="file" class="mb-2 flex items-center gap-3 rounded-xl bg-black/[0.04] p-2 dark:bg-white/5">
      <img v-if="filePreview" :src="filePreview" alt="" class="h-12 w-12 rounded-lg object-cover">
      <CourseFileIcon v-else :extension="file.name.split('.').pop()" size="sm" />
      <div class="min-w-0 flex-1">
        <p class="truncate text-sm font-medium text-gray-800 dark:text-gray-100" dir="auto">{{ file.name }}</p>
        <p class="text-[11px] text-gray-500">{{ formatBytes(file.size) }} — در صورت تمایل، توضیحی هم بنویسید</p>
      </div>
      <button type="button" class="rounded-lg p-1.5 text-gray-400 hover:text-red-600" aria-label="حذف پیوست" @click="clearFile">
        <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
      </button>
    </div>

    <!-- recording bar -->
    <div v-if="recording" class="flex items-center gap-3 rounded-2xl bg-red-500/10 px-4 py-2.5">
      <span class="relative flex h-3 w-3">
        <span class="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-500 opacity-75" />
        <span class="relative inline-flex h-3 w-3 rounded-full bg-red-600" />
      </span>
      <span class="flex-1 text-sm font-medium tabular-nums text-red-700 dark:text-red-300">در حال ضبط… {{ formatDuration(seconds) }}</span>
      <button type="button" class="rounded-lg px-3 py-1.5 text-sm text-gray-600 hover:bg-black/5 dark:text-gray-300" @click="stopRecording(true)">لغو</button>
      <button type="button" class="flex items-center gap-1.5 rounded-xl bg-primary-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-primary-500" @click="stopRecording()">
        ارسال
        <svg class="h-4 w-4 -scale-x-100" fill="currentColor" viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" /></svg>
      </button>
    </div>

    <div v-else class="flex items-end gap-2">
      <input ref="fileInput" type="file" class="hidden" @change="pickFile">
      <button
        type="button"
        :disabled="disabled"
        class="flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-gray-500 transition hover:bg-black/5 hover:text-primary-600 disabled:opacity-40 dark:hover:bg-white/10"
        aria-label="پیوست فایل یا عکس"
        title="پیوست فایل یا عکس"
        @click="fileInput?.click()"
      >
        <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" /></svg>
      </button>
      <textarea
        ref="textarea"
        v-model="text"
        rows="1"
        :disabled="disabled"
        placeholder="پیام خود را بنویسید…"
        class="max-h-40 min-h-[2.75rem] flex-1 resize-none rounded-3xl bg-black/[0.05] px-4 py-2.5 text-sm leading-6 text-gray-900 outline-none transition focus:bg-white focus:ring-2 focus:ring-primary-500/40 dark:bg-white/[0.07] dark:text-white dark:focus:bg-white/10"
        @input="autoGrow"
        @keydown="onKeydown"
      />
      <button
        v-if="text.trim() || file"
        type="button"
        :disabled="disabled"
        class="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-primary-500 to-primary-700 text-white shadow-lg shadow-primary-600/30 transition hover:scale-105 disabled:opacity-40"
        aria-label="ارسال"
        @click="submit"
      >
        <svg class="h-5 w-5 -scale-x-100" fill="currentColor" viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" /></svg>
      </button>
      <button
        v-else
        type="button"
        :disabled="disabled"
        class="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-primary-500 to-primary-700 text-white shadow-lg shadow-primary-600/30 transition hover:scale-105 disabled:opacity-40"
        aria-label="ضبط پیام صوتی"
        title="ضبط پیام صوتی"
        @click="startRecording"
      >
        <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" /></svg>
      </button>
    </div>
    <p v-if="error" class="mt-2 text-xs text-red-600">{{ error }}</p>
  </div>
</template>
