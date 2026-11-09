// Shared wording for money and for the order / payment / refund states the API returns,
// so the instructor's sales pages and the student's orders page say the same thing.

/** 150000 → «۱۵۰٬۰۰۰ تومان», 0 → «رایگان» */
export function formatToman(amount: string | number | null | undefined): string {
  const value = Number(amount ?? 0)
  return value > 0 ? `${value.toLocaleString('fa-IR')} تومان` : 'رایگان'
}

export interface StatusStyle {
  label: string
  tone: string
}

const GREEN = 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300'
const AMBER = 'bg-amber-500/15 text-amber-700 dark:text-amber-300'
const RED = 'bg-red-500/15 text-red-700 dark:text-red-300'
const GRAY = 'bg-gray-500/15 text-gray-700 dark:text-gray-300'
const BLUE = 'bg-sky-500/15 text-sky-700 dark:text-sky-300'

export const ORDER_STATUS: Record<string, StatusStyle> = {
  paid: { label: 'پرداخت‌شده', tone: GREEN },
  pending: { label: 'در انتظار پرداخت', tone: AMBER },
  failed: { label: 'ناموفق', tone: RED },
  canceled: { label: 'لغوشده', tone: GRAY },
  refunded: { label: 'مسترد شده', tone: BLUE },
}

export const PAYMENT_STATUS: Record<string, StatusStyle> = {
  verified: { label: 'موفق', tone: GREEN },
  initiated: { label: 'در درگاه / در حال بررسی', tone: AMBER },
  failed: { label: 'ناموفق', tone: RED },
  // Paid at the gateway for something already bought: never verified, so ZarinPal returns it.
  canceled: { label: 'تکراری (برگشت خودکار)', tone: GRAY },
}

export const REFUND_STATUS: Record<string, StatusStyle> = {
  pending: { label: 'در انتظار بررسی', tone: AMBER },
  rejected: { label: 'رد شده', tone: RED },
  refunded: { label: 'مسترد شده', tone: BLUE },
}

export function statusOf(map: Record<string, StatusStyle>, key: string): StatusStyle {
  return map[key] ?? { label: key, tone: GRAY }
}

/** ISO date-time → «۱۴۰۵/۰۸/۱۸ · ۱۴:۰۵» */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  const date = new Date(iso)
  const time = date.toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit' })
  return `${useJalali().formatGregorianDate(date)} · ${time}`
}
