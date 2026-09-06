<script setup lang="ts">
definePageMeta({ layout: 'admin' })
const { request } = useApi()

const { data: courses, refresh } = await useAsyncData('admin-board-courses', async () => {
  const page = await request<{ results: any[] }>('/courses/moderation/')
  return page.results
})

const columns = [
  { status: 'pending_review', label: 'در انتظار بررسی' },
  { status: 'published', label: 'منتشرشده' },
  { status: 'rejected', label: 'رد‌شده' },
] as const

function columnCourses(status: string) {
  return (courses.value ?? []).filter((c: any) => c.status === status)
}

const draggedId = ref<number | null>(null)
function onDragStart(id: number) {
  draggedId.value = id
}

// Rejecting requires a reason (enforced by the backend too) — asked via a
// small inline panel instead of a native prompt() to match the rest of
// the UI, and to let the user cancel without silently losing the drag.
const rejectTarget = ref<any | null>(null)
const rejectReason = ref('')
const moving = ref(false)
const error = ref('')

async function applyMove(course: any, status: string, rejection_reason?: string) {
  error.value = ''
  moving.value = true
  try {
    const body: Record<string, any> = { status }
    if (rejection_reason !== undefined) body.rejection_reason = rejection_reason
    await request(`/courses/moderation/${course.id}/`, { method: 'PATCH', body })
    await refresh()
  } catch (err) {
    error.value = getErrorMessage(err, 'جابه‌جایی ناموفق بود.')
  } finally {
    moving.value = false
  }
}

function onDrop(targetStatus: string) {
  const course = courses.value?.find((c: any) => c.id === draggedId.value)
  draggedId.value = null
  if (!course || course.status === targetStatus) return

  if (targetStatus === 'rejected') {
    rejectTarget.value = course
    rejectReason.value = ''
    return
  }
  applyMove(course, targetStatus)
}

async function confirmReject() {
  if (!rejectTarget.value || !rejectReason.value.trim()) return
  await applyMove(rejectTarget.value, 'rejected', rejectReason.value.trim())
  rejectTarget.value = null
}

const columnStyles: Record<string, string> = {
  pending_review: 'border-t-4 border-amber-400',
  published: 'border-t-4 border-emerald-500',
  rejected: 'border-t-4 border-red-400',
}
</script>

<template>
  <div>
    <h1 class="text-xl font-bold text-gray-900 dark:text-white">تخته‌ی دوره‌ها</h1>
    <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
      کارت هر دوره را بین ستون‌ها بکشید تا وضعیتش تغییر کند.
    </p>
    <p v-if="error" class="mt-2 text-sm text-red-600">{{ error }}</p>

    <div class="mt-6 grid grid-cols-1 gap-4 md:grid-cols-3">
      <div
        v-for="col in columns"
        :key="col.status"
        :data-tour="`board-column-${col.status}`"
        class="glass rounded-2xl p-4"
        :class="columnStyles[col.status]"
        @dragover.prevent
        @drop="onDrop(col.status)"
      >
        <div class="flex items-center justify-between">
          <h2 class="text-sm font-semibold text-gray-900 dark:text-white">{{ col.label }}</h2>
          <span class="glass rounded-full px-2 py-0.5 text-xs text-gray-600 dark:text-gray-300">{{ columnCourses(col.status).length }}</span>
        </div>

        <div class="mt-3 min-h-[120px] space-y-2">
          <div
            v-for="course in columnCourses(col.status)"
            :key="course.id"
            draggable="true"
            data-tour="board-card"
            class="glass cursor-move rounded-lg p-3 transition"
            :class="draggedId === course.id ? 'opacity-40' : ''"
            @dragstart="onDragStart(course.id)"
          >
            <p class="text-sm font-medium text-gray-900 dark:text-white">{{ course.title }}</p>
            <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">{{ course.instructor_name }} — {{ Number(course.price).toLocaleString('fa-IR') }} تومان</p>
            <a
              v-if="course.instructor_resume"
              :href="course.instructor_resume"
              target="_blank"
              rel="noopener"
              class="mt-1 inline-block text-xs text-primary-600 hover:underline dark:text-primary-400"
              @click.stop
            >
              مشاهده رزومه مدرس
            </a>
            <p v-if="course.status === 'rejected' && course.rejection_reason" class="mt-1 text-xs text-red-600">{{ course.rejection_reason }}</p>
          </div>
          <p v-if="columnCourses(col.status).length === 0" class="text-xs text-gray-400 dark:text-gray-500">خالی</p>
        </div>
      </div>
    </div>

    <!-- Reject-reason panel -->
    <div v-if="rejectTarget" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4" @click.self="rejectTarget = null">
      <div class="glass w-full max-w-sm rounded-2xl p-6">
        <h3 class="font-semibold text-gray-900 dark:text-white">دلیل رد شدن «{{ rejectTarget.title }}»</h3>
        <textarea
          v-model="rejectReason"
          rows="3"
          required
          class="glass mt-3 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white"
        />
        <div class="mt-3 flex gap-2">
          <button
            :disabled="!rejectReason.trim() || moving"
            class="rounded-md bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-500 disabled:opacity-50"
            @click="confirmReject"
          >
            ثبت رد شدن
          </button>
          <button class="glass rounded-md px-4 py-2 text-sm text-gray-700 dark:text-gray-200" @click="rejectTarget = null">
            انصراف
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
