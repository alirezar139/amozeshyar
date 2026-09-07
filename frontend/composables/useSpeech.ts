/**
 * Thin wrapper around the browser's built-in speech synthesis — no
 * external TTS API/cost, works offline. Persian voice support varies by
 * OS/browser (Windows Edge/Chrome usually ship one; some don't), so this
 * degrades gracefully to whatever default voice exists rather than
 * failing silently when no fa-IR voice is found.
 */
export function useSpeech() {
  const enabled = useState('speech-enabled', () => true)
  const supported = import.meta.client && 'speechSynthesis' in window

  function pickVoice(): SpeechSynthesisVoice | undefined {
    if (!supported) return undefined
    const voices = window.speechSynthesis.getVoices()
    return voices.find((v) => v.lang?.toLowerCase().startsWith('fa'))
  }

  function speak(text: string) {
    if (!supported || !enabled.value || !text) return
    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = 'fa-IR'
    utterance.rate = 0.95
    const voice = pickVoice()
    if (voice) utterance.voice = voice
    window.speechSynthesis.speak(utterance)
  }

  function stop() {
    if (supported) window.speechSynthesis.cancel()
  }

  function toggle() {
    enabled.value = !enabled.value
    if (!enabled.value) stop()
  }

  return { enabled, supported, speak, stop, toggle }
}
