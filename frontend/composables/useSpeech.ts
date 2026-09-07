// Tour narration is pre-rendered (see public/audio/tour/) rather than
// synthesized in the browser — the earlier in-browser WASM/ONNX voice
// needed a ~60MB one-time model download per visitor and, worse, its
// Windows-compatible phonemizer produced garbled/looping Persian audio.
// Since every tour step's text is fixed and known ahead of time, there's
// nothing to synthesize at runtime: this just plays a small static file,
// same as any other asset on the page.
export function useSpeech() {
  const enabled = useState('speech-enabled', () => true)
  const isLoading = useState('speech-loading', () => false)
  const supported = import.meta.client

  let currentAudio: HTMLAudioElement | null = null

  function stop() {
    if (currentAudio) {
      currentAudio.pause()
      currentAudio = null
    }
    isLoading.value = false
  }

  function play(url: string | null) {
    if (!supported || !enabled.value || !url) return
    stop()
    isLoading.value = true
    const audio = new Audio(url)
    currentAudio = audio
    const clearLoading = () => {
      if (currentAudio === audio) isLoading.value = false
    }
    audio.addEventListener('canplay', clearLoading, { once: true })
    audio.addEventListener('error', clearLoading, { once: true })
    audio.play().catch(clearLoading)
  }

  function toggle() {
    enabled.value = !enabled.value
    if (!enabled.value) stop()
  }

  return { enabled, supported, isLoading, play, stop, toggle }
}
