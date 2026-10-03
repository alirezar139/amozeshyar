import { toPersianDigits } from './useJalali'

/**
 * A ticking "now" in the server's time. Exam deadlines come from the server,
 * so the countdown is measured against the server clock (offset taken from
 * the `server_now` of each response) instead of trusting the device clock.
 */
export function useExamClock() {
  const offset = ref(0)
  const now = ref(Date.now())
  let timer: ReturnType<typeof setInterval> | null = null

  function sync(serverNow: string | undefined) {
    if (serverNow) offset.value = Date.parse(serverNow) - Date.now()
    now.value = Date.now() + offset.value
  }

  /** Milliseconds left until `iso` (null when there's no deadline). */
  function remaining(iso: string | null | undefined): number | null {
    return iso ? Math.max(0, Date.parse(iso) - now.value) : null
  }

  onMounted(() => {
    timer = setInterval(() => (now.value = Date.now() + offset.value), 250)
  })
  onBeforeUnmount(() => timer && clearInterval(timer))

  return { now, sync, remaining }
}

/** 3725000 -> "۱:۰۲:۰۵", 65000 -> "۰۱:۰۵". */
export function formatCountdown(ms: number): string {
  const total = Math.ceil(ms / 1000)
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = total % 60
  const pad = (n: number) => String(n).padStart(2, '0')
  return toPersianDigits(h ? `${h}:${pad(m)}:${pad(s)}` : `${pad(m)}:${pad(s)}`)
}

/** Wall-clock time of an ISO date, e.g. "۱۴:۳۰". */
export function clockTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit' })
}
