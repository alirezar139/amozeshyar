/**
 * Thin wrapper around the browser's built-in speech synthesis — no
 * external TTS API/cost, works offline. Persian voice support varies by
 * OS/browser (Windows Edge/Chrome usually ship one; some don't). Forcing
 * `lang = 'fa-IR'` when no matching voice is installed makes some
 * engines fail *silently* instead of falling back — so lang/voice are
 * only set together, from a voice that's actually confirmed to exist;
 * otherwise the utterance is left to the browser's own default so it at
 * least produces audible (if mispronounced) speech instead of nothing.
 */
export function useSpeech() {
  const enabled = useState('speech-enabled', () => true)
  const supported = import.meta.client && 'speechSynthesis' in window

  function pickVoice(): SpeechSynthesisVoice | undefined {
    if (!supported) return undefined
    const voices = window.speechSynthesis.getVoices()
    // Match by lang code first (fa, fa-IR); some engines mislabel the lang
    // but still name the voice "Persian"/"Farsi", so check that too.
    return voices.find(
      (v) =>
        v.lang?.toLowerCase().startsWith('fa') ||
        /persian|farsi/i.test(v.name)
    )
  }

  function hasPersianVoice(): boolean {
    if (!supported) return false
    return !!pickVoice()
  }

  function speak(text: string) {
    if (!supported || !enabled.value || !text) return
    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.rate = 0.95
    const voice = pickVoice()
    if (voice) {
      utterance.voice = voice
      utterance.lang = voice.lang
    }
    // Voices load asynchronously in some browsers and getVoices() can
    // return [] on the very first call of a page session — retry once
    // shortly after if that happens, instead of just speaking with
    // whatever (possibly wrong) default voice was available immediately.
    if (supported && window.speechSynthesis.getVoices().length === 0) {
      window.speechSynthesis.addEventListener(
        'voiceschanged',
        () => {
          const retryVoice = pickVoice()
          if (retryVoice) {
            utterance.voice = retryVoice
            utterance.lang = retryVoice.lang
          }
          window.speechSynthesis.speak(utterance)
        },
        { once: true }
      )
      return
    }
    window.speechSynthesis.speak(utterance)
  }

  function stop() {
    if (supported) window.speechSynthesis.cancel()
  }

  function toggle() {
    enabled.value = !enabled.value
    if (!enabled.value) stop()
  }

  return { enabled, supported, speak, stop, toggle, hasPersianVoice }
}
