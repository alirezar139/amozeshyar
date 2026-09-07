import type { VoiceId } from '@diffusionstudio/vits-web'

// A fully offline, in-browser neural TTS voice (Piper, via WASM/ONNX) —
// chosen over the native Web Speech API because Windows ships no Persian
// SAPI voice at all, and Edge's "online" voices turned out not to be
// exposed to page JS either. The ~60MB model is fetched once and cached
// in the browser's Origin Private File System, so only the very first
// narration on a given browser is slow; everything after is local.
const VOICE_ID: VoiceId = 'fa_IR-amir-medium'

// The espeak-ng phonemizer underneath Piper stumbles on characters that
// carry no sound of their own — most importantly U+200C (ZWNJ), the
// invisible "نیم‌فاصله" Persian text uses constantly for compound words
// like "می‌شه" or "ثبت‌نام". Left in, it reads as a small glitch on
// nearly every other word, which is what made the narration sound
// pervasively "off" rather than wrong in any one obvious place. Dropping
// it merges the compound back into one plain word ("میشه") — no audible
// pause is lost, since the half-space was never a spoken pause to begin
// with. An em dash is replaced with a comma instead of dropped, so the
// pause it implies in writing survives as an actual pause in speech.
function sanitizeForSpeech(text: string) {
  return text.replace(/‌/g, '').replace(/[—–]/g, '،')
}

export function useSpeech() {
  const enabled = useState('speech-enabled', () => true)
  const isLoading = useState('speech-loading', () => false)
  // 0-100, only meaningful while isLoading is true and the model itself
  // (not the tiny config file) is being downloaded for the first time.
  const loadProgress = useState('speech-progress', () => 0)
  const supported = import.meta.client && typeof navigator !== 'undefined' && !!navigator.storage?.getDirectory

  let currentAudio: HTMLAudioElement | null = null
  // Bumped on every speak()/stop() call so a slow in-flight synthesis
  // from a step the user already clicked past can't finish late and
  // start playing over the current one.
  let requestId = 0

  function stop() {
    requestId++
    if (currentAudio) {
      currentAudio.pause()
      URL.revokeObjectURL(currentAudio.src)
      currentAudio = null
    }
    isLoading.value = false
  }

  async function speak(text: string) {
    if (!supported || !enabled.value || !text) return
    stop()
    const myRequest = requestId
    isLoading.value = true
    loadProgress.value = 0
    try {
      const { predict } = await import('@diffusionstudio/vits-web')
      const blob = await predict({ text: sanitizeForSpeech(text), voiceId: VOICE_ID }, (progress) => {
        if (myRequest !== requestId) return
        loadProgress.value = progress.total ? Math.round((progress.loaded / progress.total) * 100) : 0
      })
      if (myRequest !== requestId) return
      const audio = new Audio(URL.createObjectURL(blob))
      currentAudio = audio
      await audio.play()
    } catch (err) {
      console.error('speech synthesis failed', err)
    } finally {
      if (myRequest === requestId) isLoading.value = false
    }
  }

  function toggle() {
    enabled.value = !enabled.value
    if (!enabled.value) stop()
  }

  return { enabled, supported, isLoading, loadProgress, speak, stop, toggle }
}
