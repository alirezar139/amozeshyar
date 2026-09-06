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

  function isSameDay(a: Date, b: Date): boolean {
    return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate()
  }

  return { fromGregorian, toGregorianDate, weekdayIndex, monthLength, formatDate, isSameDay }
}
