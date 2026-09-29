/** 1536 → «۱٫۵ کیلوبایت» */
export function formatBytes(bytes: number | null | undefined): string {
  if (!bytes) return '۰ بایت'
  const units = ['بایت', 'کیلوبایت', 'مگابایت', 'گیگابایت']
  let value = bytes
  let unit = 0
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024
    unit++
  }
  return `${value.toLocaleString('fa-IR', { maximumFractionDigits: unit >= 2 ? 1 : 0 })} ${units[unit]}`
}

/** 3725 → «۱:۰۲:۰۵», 125 → «۲:۰۵» */
export function formatDuration(seconds: number | null | undefined): string {
  if (!seconds && seconds !== 0) return ''
  const s = Math.round(seconds)
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = s % 60
  const pad = (n: number) => String(n).padStart(2, '0')
  const text = h ? `${h}:${pad(m)}:${pad(sec)}` : `${m}:${pad(sec)}`
  return text.replace(/\d/g, (d) => '۰۱۲۳۴۵۶۷۸۹'[Number(d)])
}

/** Remaining upload time in words: «حدود ۳ دقیقه» */
export function formatRemaining(seconds: number | null | undefined): string {
  if (seconds == null || !Number.isFinite(seconds)) return ''
  if (seconds < 60) return 'کمتر از یک دقیقه'
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return `حدود ${minutes.toLocaleString('fa-IR')} دقیقه`
  return `حدود ${(minutes / 60).toLocaleString('fa-IR', { maximumFractionDigits: 1 })} ساعت`
}
