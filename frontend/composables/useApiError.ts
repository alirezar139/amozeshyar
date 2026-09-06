/**
 * DRF error bodies come in a few shapes: {"detail": "..."} for auth/permission
 * errors, {"field": ["msg", ...]} for validation errors, or a bare list.
 * This normalizes all of them into one string so forms can show the real
 * cause instead of a generic "something went wrong".
 */
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
    return firstKey === 'non_field_errors' ? String(message) : `${firstKey}: ${message}`
  }

  return fallback
}
