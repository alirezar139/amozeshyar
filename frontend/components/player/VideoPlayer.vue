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

function attachSource(url: string) {
  const video = videoEl.value
  if (!video) return

  if (url.endsWith('.m3u8') && video.canPlayType('application/vnd.apple.mpegurl') === '') {
    import('hls.js').then(({ default: Hls }) => {
      if (Hls.isSupported()) {
        const hls = new Hls()
        hls.loadSource(url)
        hls.attachMedia(video)
      }
    })
  } else {
    video.src = url
  }
}

function onEnded() {
  if (!props.hasFullAccess) {
    previewEnded.value = true
  }
}

onMounted(loadSource)
</script>

<template>
  <div class="relative aspect-video w-full overflow-hidden rounded-lg bg-black">
    <video
      v-show="!loading"
      ref="videoEl"
      controls
      class="h-full w-full"
      @ended="onEnded"
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
