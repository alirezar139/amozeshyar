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

const { request } = useApi()
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

  if (url.endsWith('.m3u8') && video.canPlayType('application/vnd.apple.mpegurl') === '') {
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
  request('/progress/', {
    method: 'POST',
    body: { lesson_id: props.lessonId, position_seconds: position },
  }).catch(() => {})
}

function onTimeUpdate() {
  const now = Date.now()
  if (now - lastReportedAt >= 10000) {
    lastReportedAt = now
    reportProgress()
  }
}

onMounted(loadSource)
onUnmounted(() => {
  reportProgress()
  hlsInstance?.destroy()
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
  <div class="relative aspect-video w-full overflow-hidden rounded-lg bg-black">
    <video
      v-show="!loading"
      ref="videoEl"
      controls
      class="h-full w-full"
      @ended="onEnded"
      @pause="reportProgress"
      @timeupdate="onTimeUpdate"
    />
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
