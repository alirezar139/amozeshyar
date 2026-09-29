/** Download a lesson file through its short-lived signed link (the file URL itself is never public). */
export function useLessonFiles() {
  const { request } = useApi()
  const downloadingId = ref<number | null>(null)
  const downloadError = ref('')

  async function download(fileId: number) {
    downloadingId.value = fileId
    downloadError.value = ''
    try {
      const { url } = await request<{ url: string }>(`/lesson-files/${fileId}/download/`)
      // A same-tab navigation to a Content-Disposition: attachment URL just
      // downloads, without leaving the page or tripping popup blockers.
      window.location.href = url
    } catch (err) {
      downloadError.value = getErrorMessage(err, 'دانلود فایل ممکن نشد.')
    } finally {
      downloadingId.value = null
    }
  }

  return { download, downloadingId, downloadError }
}
