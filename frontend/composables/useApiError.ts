/**
 * DRF error bodies come in a few shapes: {"detail": "..."} for auth/permission
 * errors, {"field": ["msg", ...]} for validation errors, or a bare list.
 * This normalizes all of them into one string so forms can show the real
 * cause instead of a generic "something went wrong".
 */
// Persian names for the API's (English) field keys, so a validation error reads
// «دسته‌بندی: …» instead of «category: …».
const FIELD_LABELS: Record<string, string> = {
  category: 'دسته‌بندی',
  title: 'عنوان',
  subtitle: 'زیرعنوان',
  description: 'توضیحات',
  level: 'سطح',
  price: 'قیمت',
  name: 'نام',
  email: 'ایمیل',
  password: 'رمز عبور',
  first_name: 'نام',
  last_name: 'نام خانوادگی',
  phone: 'شماره موبایل',
  file: 'فایل',
  image: 'تصویر',
  start_at: 'زمان شروع',
  end_at: 'زمان پایان',
  duration_minutes: 'مدت',
  question: 'سؤال',
  text: 'متن',
}

export function getErrorMessage(error: any, fallback: string): string {
  const data = error?.data ?? error?.response?._data
  if (!data) {
    // No response body at all means the request never reached the server
    // (backend down, network drop) — don't blame the user's credentials for that.
    if (!error?.response) {
      return 'سرور در دسترس نیست. لطفاً اتصال خود را بررسی کنید و دوباره تلاش کنید.'
    }
    return fallback
  }

  if (typeof data === 'string') return data
  if (data.detail) return String(data.detail)

  const firstKey = Object.keys(data)[0]
  if (firstKey) {
    const value = data[firstKey]
    const message = Array.isArray(value) ? value[0] : value
    if (firstKey === 'non_field_errors') return String(message)
    return `${FIELD_LABELS[firstKey] ?? firstKey}: ${message}`
  }

  return fallback
}

/**
 * Like getErrorMessage, but for showing next to a form: just the first
 * message, without the "field: " prefix (field names are English).
 */
export function getFirstErrorMessage(error: any, fallback: string): string {
  const data = error?.data ?? error?.response?._data
  if (data && typeof data === 'object' && !data.detail) {
    const first = Object.values(data).flat()[0]
    if (typeof first === 'string') return first
  }
  return getErrorMessage(error, fallback)
}
