<script setup lang="ts">
definePageMeta({ layout: 'admin' })
const { request } = useApi()

const { data: instructors, pending, refresh } = await useAsyncData('admin-instructors', async () => {
  const page = await request<{ results: any[] }>('/instructors/moderation/')
  return page.results
})

const statusLabels: Record<string, string> = {
  pending_review: 'در انتظار تایید',
  approved: 'تاییدشده',
  rejected: 'ردشده',
}

const busyId = ref<number | null>(null)
const rejectingId = ref<number | null>(null)
const rejectionReason = ref('')

async function approve(id: number) {
  busyId.value = id
  try {
    await request(`/instructors/moderation/${id}/`, { method: 'PATCH', body: { status: 'approved' } })
    await refresh()
  } finally {
    busyId.value = null
  }
}

function startReject(id: number) {
  rejectingId.value = id
  rejectionReason.value = ''
}

async function confirmReject(id: number) {
  busyId.value = id
  try {
    await request(`/instructors/moderation/${id}/`, {
      method: 'PATCH',
      body: { status: 'rejected', rejection_reason: rejectionReason.value },
    })
    rejectingId.value = null
    await refresh()
  } finally {
    busyId.value = null
  }
}
</script>

<template>
  <div>
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-bold text-gray-900 dark:text-white">مدرس‌ها</h1>
      <NuxtLink
        to="/admin/instructors/create"
        class="rounded-md bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-500"
      >
        افزودن مدرس جدید
      </NuxtLink>
    </div>

    <div v-if="pending" class="mt-6 text-gray-500">در حال بارگذاری...</div>
    <p v-else-if="instructors && instructors.length === 0" class="mt-6 text-gray-500">
      مدرسی برای بررسی نیست.
    </p>
    <div v-else data-tour="instructor-approval-list" class="mt-6 space-y-4">
      <div
        v-for="instructor in instructors"
        :key="instructor.id"
        class="glass rounded-lg p-4"
      >
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div class="flex items-center gap-2">
              <h2 class="font-semibold text-gray-900 dark:text-white">{{ instructor.display_name }}</h2>
              <span
                class="rounded-full px-2 py-0.5 text-xs font-medium"
                :class="{
                  'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300': instructor.status === 'pending_review',
                  'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300': instructor.status === 'approved',
                  'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300': instructor.status === 'rejected',
                }"
              >
                {{ statusLabels[instructor.status] }}
              </span>
            </div>
            <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">{{ instructor.headline }}</p>
            <a
              v-if="instructor.resume"
              :href="instructor.resume"
              target="_blank"
              rel="noopener"
              class="mt-1 inline-flex items-center gap-1 text-sm text-primary-600 hover:underline dark:text-primary-400"
            >
              مشاهده رزومه
            </a>
            <p v-else class="mt-1 text-sm text-red-600">رزومه‌ای بارگذاری نشده است</p>
          </div>
          <div v-if="instructor.status === 'pending_review'" class="flex shrink-0 gap-2">
            <button
              :disabled="busyId === instructor.id"
              class="rounded-md bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-500 disabled:opacity-50"
              @click="approve(instructor.id)"
            >
              تایید
            </button>
            <button
              :disabled="busyId === instructor.id"
              class="rounded-md border border-red-300 px-4 py-2 text-sm font-semibold text-red-600 hover:bg-red-50 disabled:opacity-50 dark:border-red-800 dark:hover:bg-red-950/40"
              @click="startReject(instructor.id)"
            >
              رد کردن
            </button>
          </div>
        </div>

        <div v-if="rejectingId === instructor.id" class="mt-4 border-t border-white/30 pt-4 dark:border-white/10">
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">دلیل رد شدن</label>
          <textarea
            v-model="rejectionReason"
            rows="2"
            class="glass mt-1 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white"
          />
          <div class="mt-2 flex gap-2">
            <button
              :disabled="!rejectionReason || busyId === instructor.id"
              class="rounded-md bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-500 disabled:opacity-50"
              @click="confirmReject(instructor.id)"
            >
              ثبت رد شدن
            </button>
            <button
              class="glass rounded-md px-4 py-2 text-sm text-gray-700 dark:text-gray-200"
              @click="rejectingId = null"
            >
              انصراف
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
