<script setup lang="ts">
// Full-screen, no site chrome — this is meant to feel like its own app
// (Google Meet, Zoom), not a page embedded in the rest of the site.
definePageMeta({ layout: false, ssr: false })

const route = useRoute()
const sessionId = route.params.id as string
const { request } = useApi()

const status = ref<'loading' | 'ready' | 'error'>('loading')
const errorMessage = ref('')
const info = ref<{ room_name: string; display_name: string; title: string; course_title: string } | null>(null)
const containerRef = ref<HTMLDivElement | null>(null)
let jitsiApi: any = null

function loadScript(src: string) {
  return new Promise<void>((resolve, reject) => {
    if (document.querySelector(`script[src="${src}"]`)) {
      resolve()
      return
    }
    const script = document.createElement('script')
    script.src = src
    script.async = true
    script.onload = () => resolve()
    script.onerror = () => reject(new Error('script load failed'))
    document.head.appendChild(script)
  })
}

onMounted(async () => {
  try {
    info.value = await request<typeof info.value>(`/class-sessions/${sessionId}/join/`)
  } catch (err) {
    status.value = 'error'
    errorMessage.value = getErrorMessage(err, 'شما به این کلاس دسترسی ندارید یا کلاسی با این شناسه پیدا نشد.')
    return
  }

  try {
    await loadScript('https://meet.jit.si/external_api.js')
  } catch {
    status.value = 'error'
    errorMessage.value = 'اتصال به سرویس کلاس آنلاین ناموفق بود. اتصال اینترنت خود را بررسی کنید.'
    return
  }

  // No configOverwrite/interfaceConfigOverwrite — the full default Jitsi
  // Meet toolbar (mic/camera, screen share, chat, raise hand, reactions,
  // tile view, etc.) is exactly the "like Google Meet, every feature"
  // experience asked for, so there's nothing to trim or hide here.
  jitsiApi = new (window as any).JitsiMeetExternalAPI('meet.jit.si', {
    roomName: info.value!.room_name,
    parentNode: containerRef.value,
    width: '100%',
    height: '100%',
    userInfo: { displayName: info.value!.display_name },
  })
  jitsiApi.on('readyToClose', () => {
    navigateTo('/dashboard/calendar')
  })
  status.value = 'ready'
})

onUnmounted(() => {
  jitsiApi?.dispose()
})
</script>

<template>
  <div class="fixed inset-0 flex flex-col bg-gray-950">
    <div v-if="status !== 'error'" class="flex items-center justify-between px-4 py-2 text-sm text-gray-300">
      <span>{{ info ? `${info.course_title} — ${info.title}` : 'در حال اتصال به کلاس...' }}</span>
      <NuxtLink to="/dashboard/calendar" class="text-gray-400 hover:text-white">بازگشت ✕</NuxtLink>
    </div>

    <div v-if="status === 'loading'" class="flex flex-1 items-center justify-center text-gray-400">
      در حال اتصال به کلاس آنلاین...
    </div>
    <div v-else-if="status === 'error'" class="flex flex-1 flex-col items-center justify-center gap-4 px-4 text-center text-gray-300">
      <p>{{ errorMessage }}</p>
      <NuxtLink to="/dashboard/calendar" class="rounded-md bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-500">
        بازگشت به تقویم
      </NuxtLink>
    </div>
    <div v-show="status === 'ready'" ref="containerRef" class="flex-1" />
  </div>
</template>
