import { jalaaliMonthLength, toGregorian, toJalaali } from 'jalaali-js'

export const JALALI_MONTH_NAMES = [
  'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
  'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند',
]

// Saturday-first week, matching the Iranian calendar convention.
export const JALALI_WEEKDAY_NAMES = ['ش', 'ی', 'د', 'س', 'چ', 'پ', 'ج']

const PERSIAN_DIGITS = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹']

export function toPersianDigits(value: number | string): string {
  return String(value).replace(/[0-9]/g, (d) => PERSIAN_DIGITS[Number(d)])
}

/**
 * Thin wrapper around jalaali-js for the one thing the site needs: laying
 * out a Jalali month grid and mapping grid cells back to real (Gregorian)
 * dates for querying the backend, which stores everything in standard
 * ISO datetimes. Display-only conversions could lean on `Intl` instead,
 * but building an actual calendar grid needs real date arithmetic.
 */
export function useJalali() {
  function fromGregorian(date: Date) {
    return toJalaali(date.getFullYear(), date.getMonth() + 1, date.getDate())
  }

  function toGregorianDate(jy: number, jm: number, jd: number): Date {
    const { gy, gm, gd } = toGregorian(jy, jm, jd)
    return new Date(gy, gm - 1, gd)
  }

  // Saturday-first weekday index (0=Saturday..6=Friday) for a Jalali date.
  function weekdayIndex(jy: number, jm: number, jd: number): number {
    const jsDay = toGregorianDate(jy, jm, jd).getDay() // 0=Sunday..6=Saturday
    return (jsDay + 1) % 7
  }

  function monthLength(jy: number, jm: number): number {
    return jalaaliMonthLength(jy, jm)
  }

  function formatDate(jy: number, jm: number, jd: number): string {
    return `${toPersianDigits(jy)} ${JALALI_MONTH_NAMES[jm - 1]} ${toPersianDigits(jd)}`
  }

  // Convenience for the common case (a JS Date from the backend, e.g. a
  // session's starts_at) — every date shown anywhere in the app should
  // go through this rather than `Date.toLocaleDateString('fa-IR')`, whose
  // calendar system isn't guaranteed the same across browsers/Node ICU
  // builds; this always renders Jalali, unambiguously.
  //
  // Wrapped in a try/catch on purpose: jalaali-js throws for a year
  // outside roughly [-61, 3177], which a bad or corrupted `starts_at`
  // can absolutely produce (seen in practice: a UTC offset with a
  // seconds component for a pre-standard-timezone date broke the
  // browser's own Date parser entirely, yielding a garbage year). A
  // display helper crashing the whole page over one bad record is a far
  // worse outcome than it just showing a fallback string for that one.
  function formatGregorianDate(date: Date): string {
    try {
      const { jy, jm, jd } = fromGregorian(date)
      return formatDate(jy, jm, jd)
    } catch {
      return 'تاریخ نامعتبر'
    }
  }

  function isSameDay(a: Date, b: Date): boolean {
    return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate()
  }

  return { fromGregorian, toGregorianDate, weekdayIndex, monthLength, formatDate, formatGregorianDate, isSameDay }
}
