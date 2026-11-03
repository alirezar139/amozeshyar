<script setup lang="ts">
/**
 * Thin hls.js wrapper. The actual paywall is enforced server-side (the
 * backend only ever hands a non-enrolled viewer a URL to the physically
 * truncated preview clip) — the overlay here is UX only, shown once that
 * clip naturally ends.
 */
const props = defineProps<{
  videoId: number
  hasFullAccess: boolean
  lessonId?: number
  initialPosition?: number
}>()

const emit = defineEmits<{ progress: [{ lesson_id: number; position_seconds: number; completed: boolean }] }>()

const { request } = useApi()
const auth = useAuthStore()
const frameEl = ref<HTMLDivElement | null>(null)
const videoEl = ref<HTMLVideoElement | null>(null)
const previewEnded = ref(false)
const loading = ref(true)
const errorMessage = ref('')

async function loadSource() {
  loading.value = true
  errorMessage.value = ''
  try {
    const endpoint = props.hasFullAccess
      ? `/videos/${props.videoId}/manifest/`
      : `/videos/${props.videoId}/preview/`
    const { url } = await request<{ url: string }>(endpoint)
    attachSource(url)
  } catch {
    errorMessage.value = 'در حال حاضر امکان پخش این ویدیو وجود ندارد.'
  } finally {
    loading.value = false
  }
}

let hlsInstance: import('hls.js').default | null = null

function attachSource(url: string) {
  const video = videoEl.value
  if (!video) return

  hlsInstance?.destroy()
  hlsInstance = null

  // Judge by the path: signed links end in a query string, not ".m3u8".
  const isHls = new URL(url, window.location.href).pathname.endsWith('.m3u8')
  if (isHls && video.canPlayType('application/vnd.apple.mpegurl') === '') {
    import('hls.js').then(({ default: Hls }) => {
      if (Hls.isSupported()) {
        hlsInstance = new Hls()
        hlsInstance.loadSource(url)
        hlsInstance.attachMedia(video)
      }
    })
  } else {
    video.src = url
  }

  if (props.hasFullAccess && props.initialPosition && props.initialPosition > 3) {
    video.addEventListener(
      'loadedmetadata',
      () => {
        video.currentTime = props.initialPosition!
      },
      { once: true }
    )
  }
}

function onEnded() {
  if (!props.hasFullAccess) {
    previewEnded.value = true
  }
  reportProgress()
}

// Resume tracking: only meaningful for the full video, so the preview
// clip (already capped at ~30s server-side) never bothers reporting.
// Sent at most once every 10s of playback, plus once on pause/unmount so
// a viewer who closes the tab mid-lesson doesn't lose their spot.
let lastReportedAt = 0

function reportProgress() {
  const video = videoEl.value
  if (!props.hasFullAccess || !props.lessonId || !video) return
  const position = Math.floor(video.currentTime)
  request<{ lesson_id: number; position_seconds: number; completed: boolean }>('/progress/', {
    method: 'POST',
    body: { lesson_id: props.lessonId, position_seconds: position },
  })
    .then((saved) => emit('progress', saved))
    .catch(() => {})
}

function onTimeUpdate() {
  const now = Date.now()
  if (now - lastReportedAt >= 10000) {
    lastReportedAt = now
    reportProgress()
  }
}

// Watermark: the viewer's email drifts across the full video so a screen
// recording that gets shared can be traced back to the account. It deters,
// it doesn't prevent: HLS has no DRM. Previews carry none (they're public).
const WATERMARK_SPOTS = [
  { top: '8%', left: '6%' }, { top: '8%', left: '58%' }, { top: '46%', left: '30%' },
  { top: '78%', left: '8%' }, { top: '70%', left: '55%' },
]
const watermarkSpot = ref(0)
const watermarkText = computed(() => (props.hasFullAccess ? auth.user?.email ?? '' : ''))
let watermarkTimer: ReturnType<typeof setInterval> | null = null

// The native fullscreen button fullscreens the <video> element alone, which
// would hide the watermark; swap it for the frame that holds both.
function onFullscreenChange() {
  const frame = frameEl.value
  if (frame && watermarkText.value && document.fullscreenElement === videoEl.value) {
    document.exitFullscreen().then(() => frame.requestFullscreen()).catch(() => {})
  }
}

// iPhone has no fullscreen API for anything but the <video> itself, and its
// own video fullscreen covers the page, watermark included. So there the
// native fullscreen is closed as soon as it opens and the frame (video +
// watermark) covers the screen instead. Other devices never get here: they
// support frame.requestFullscreen and take the path above.
const pageFullscreen = ref(false)

function onNativeVideoFullscreen() {
  const video = videoEl.value as (HTMLVideoElement & { webkitExitFullscreen?: () => void }) | null
  const frame = frameEl.value as (HTMLDivElement & { webkitRequestFullscreen?: () => void }) | null
  if (!video || !frame || !watermarkText.value) return
  if (frame.requestFullscreen || frame.webkitRequestFullscreen) return
  const wasPlaying = !video.paused
  video.webkitExitFullscreen?.()
  pageFullscreen.value = true
  if (wasPlaying) video.play().catch(() => {})
}

watch(pageFullscreen, (on) => {
  // Keep the page behind from scrolling while the player covers it.
  document.documentElement.style.overflow = on ? 'hidden' : ''
})

onMounted(() => {
  loadSource()
  watermarkTimer = setInterval(() => {
    watermarkSpot.value = (watermarkSpot.value + 1 + Math.floor(Math.random() * (WATERMARK_SPOTS.length - 1))) % WATERMARK_SPOTS.length
  }, 15000)
  document.addEventListener('fullscreenchange', onFullscreenChange)
})
onUnmounted(() => {
  reportProgress()
  hlsInstance?.destroy()
  if (watermarkTimer) clearInterval(watermarkTimer)
  document.removeEventListener('fullscreenchange', onFullscreenChange)
  pageFullscreen.value = false
  document.documentElement.style.overflow = ''
})

watch(
  () => props.videoId,
  () => {
    previewEnded.value = false
    lastReportedAt = 0
    loadSource()
  }
)
</script>

<template>
  <div
    ref="frameEl"
    :class="[
      'overflow-hidden bg-black',
      pageFullscreen ? 'fixed inset-0 z-[200]' : 'relative aspect-video w-full rounded-lg',
    ]"
  >
    <!-- playsinline: without it an iPhone plays every video in its own
         fullscreen, where the watermark can't be shown. -->
    <video
      v-show="!loading"
      ref="videoEl"
      controls
      playsinline
      webkit-playsinline
      controlslist="nodownload"
      disablepictureinpicture
      class="h-full w-full"
      @webkitbeginfullscreen="onNativeVideoFullscreen"
      @ended="onEnded"
      @pause="reportProgress"
      @timeupdate="onTimeUpdate"
    />
    <span
      v-if="watermarkText && !loading"
      class="watermark pointer-events-none absolute select-none text-xs font-medium text-white/25 sm:text-sm"
      :style="WATERMARK_SPOTS[watermarkSpot]"
      dir="ltr"
      aria-hidden="true"
    >{{ watermarkText }}</span>
    <button
      v-if="pageFullscreen"
      type="button"
      aria-label="خروج از تمام‌صفحه"
      class="absolute end-3 top-3 z-10 rounded-full bg-black/50 p-2 text-white"
      @click="pageFullscreen = false"
    >
      <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
    </button>
    <div v-if="loading" class="absolute inset-0 flex items-center justify-center text-gray-300">
      در حال بارگذاری پخش‌کننده...
    </div>
    <div v-if="errorMessage" class="absolute inset-0 flex items-center justify-center bg-black/80 px-4 text-center text-white">
      {{ errorMessage }}
    </div>
    <div
      v-if="previewEnded"
      class="absolute inset-0 flex flex-col items-center justify-center gap-4 bg-black/85 px-4 text-center text-white"
    >
      <p class="text-lg font-semibold">پیش‌نمایش رایگان به پایان رسید</p>
      <p class="text-sm text-gray-300">برای ادامه‌ی تماشا، دوره را خریداری کنید</p>
      <slot name="cta" />
    </div>
  </div>
</template>

<style scoped>
.watermark {
  transition: top 2s ease, left 2s ease;
  text-shadow: 0 0 2px rgb(0 0 0 / 0.35);
}
@media (prefers-reduced-motion: reduce) {
  .watermark { transition: none; }
}
</style>
