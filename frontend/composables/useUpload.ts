export interface UploadProgress {
  loaded: number
  total: number
  percent: number
  /** bytes per second, smoothed */
  speed: number
  /** seconds left at the current speed; null until measurable */
  remaining: number | null
}

export interface UploadHandle<T> {
  promise: Promise<T>
  abort: () => void
}

export class UploadAbortedError extends Error {
  constructor() {
    super('aborted')
  }
}

/**
 * Multipart uploads with real progress. $fetch can't report upload
 * progress, so this uses XMLHttpRequest. Starts from a freshly refreshed
 * access token; the backend's upload endpoints also accept it for a while
 * after expiry (UploadJWTAuthentication), so hour-long uploads still land.
 */
export function useUpload() {
  const config = useRuntimeConfig()
  const authStore = useAuthStore()
  const { refreshSession } = useApi()

  function upload<T>(path: string, fields: Record<string, string | Blob>, onProgress?: (p: UploadProgress) => void): UploadHandle<T> {
    const xhr = new XMLHttpRequest()
    let aborted = false

    const promise = (async () => {
      await refreshSession()
      if (aborted) throw new UploadAbortedError()

      const body = new FormData()
      for (const [key, value] of Object.entries(fields)) body.append(key, value)

      return await new Promise<T>((resolve, reject) => {
        const startedAt = performance.now()
        let speed = 0

        xhr.open('POST', `${config.public.apiBase}${path}`)
        xhr.withCredentials = true
        if (authStore.accessToken) xhr.setRequestHeader('Authorization', `Bearer ${authStore.accessToken}`)
        xhr.responseType = 'json'

        xhr.upload.onprogress = (e) => {
          if (!e.lengthComputable) return
          const elapsed = (performance.now() - startedAt) / 1000
          const instant = elapsed > 0 ? e.loaded / elapsed : 0
          speed = speed ? speed * 0.8 + instant * 0.2 : instant
          onProgress?.({
            loaded: e.loaded,
            total: e.total,
            percent: Math.min(100, Math.round((e.loaded / e.total) * 100)),
            speed,
            remaining: speed > 0 && elapsed > 1 ? (e.total - e.loaded) / speed : null,
          })
        }
        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) resolve(xhr.response as T)
          else reject(Object.assign(new Error('upload failed'), { status: xhr.status, data: xhr.response }))
        }
        xhr.onerror = () => reject(Object.assign(new Error('network'), { status: 0 }))
        xhr.onabort = () => reject(new UploadAbortedError())
        xhr.send(body)
      })
    })()

    return {
      promise,
      abort: () => {
        aborted = true
        xhr.abort()
      },
    }
  }

  /** A readable Persian message for a failed upload. */
  function uploadErrorMessage(err: any, fallback: string): string {
    if (err instanceof UploadAbortedError) return 'آپلود لغو شد.'
    if (err?.status === 0) return 'اتصال اینترنت قطع شد. دوباره تلاش کنید.'
    if (err?.status === 413) return 'حجم فایل بیشتر از حد مجاز سرور است.'
    const data = err?.data
    if (data && typeof data === 'object') {
      const first = Object.values(data).flat()[0]
      if (typeof first === 'string') return first
    }
    return fallback
  }

  return { upload, uploadErrorMessage }
}
