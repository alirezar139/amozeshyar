// Sane min/max for a `datetime-local` input's `min`/`max` attributes —
// added after a real incident where a Jalali year got typed directly
// into the field (browser widgets on a Persian-locale Windows can show a
// Jalali-looking picker while still writing a literal Gregorian value),
// producing a class session dated 621 years in the past that later
// crashed the calendar page entirely when displayed. The browser will
// simply refuse to submit a value outside this range.
function toLocalInputValue(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

export function dateTimeLocalBounds(): { min: string; max: string } {
  const now = new Date()
  const max = new Date(now)
  max.setFullYear(max.getFullYear() + 5)
  return { min: toLocalInputValue(now), max: toLocalInputValue(max) }
}
