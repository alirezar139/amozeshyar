<script setup lang="ts">
definePageMeta({ layout: 'admin' })
const { request } = useApi()

const { data: courses, pending, refresh } = await useAsyncData('admin-pending-courses', async () => {
  const page = await request<{ results: any[] }>('/courses/moderation/')
  return page.results
})

const busyId = ref<number | null>(null)
const rejectingId = ref<number | null>(null)
const rejectionReason = ref('')

async function approve(id: number) {
  busyId.value = id
  try {
    await request(`/courses/moderation/${id}/`, { method: 'PATCH', body: { status: 'published' } })
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
    await request(`/courses/moderation/${id}/`, {
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
      <h1 class="text-xl font-bold text-gray-900 dark:text-white">دوره‌های در انتظار تایید</h1>
      <NuxtLink
        to="/admin/courses/create"
        class="rounded-md bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-500"
      >
        ثبت مستقیم دوره
      </NuxtLink>
    </div>
    <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
      این دوره‌ها تا تایید یا رد شدن، در سایت عمومی نمایش داده نمی‌شوند.
    </p>

    <div v-if="pending" class="mt-6 text-gray-500">در حال بارگذاری...</div>
    <p v-else-if="courses && courses.length === 0" class="mt-6 text-gray-500">
      دوره‌ای در انتظار تایید نیست.
    </p>
    <div v-else class="mt-6 space-y-4">
      <div
        v-for="course in courses"
        :key="course.id"
        class="glass rounded-lg p-4"
      >
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 class="font-semibold text-gray-900 dark:text-white">{{ course.title }}</h2>
            <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">{{ course.subtitle }}</p>
            <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
              مدرس: {{ course.instructor_name }} — قیمت: {{ course.price }} تومان
            </p>
          </div>
          <div class="flex shrink-0 gap-2">
            <button
              :disabled="busyId === course.id"
              class="rounded-md bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-500 disabled:opacity-50"
              @click="approve(course.id)"
            >
              تایید
            </button>
            <button
              :disabled="busyId === course.id"
              class="rounded-md border border-red-300 px-4 py-2 text-sm font-semibold text-red-600 hover:bg-red-50 disabled:opacity-50 dark:border-red-800 dark:hover:bg-red-950/40"
              @click="startReject(course.id)"
            >
              رد کردن
            </button>
          </div>
        </div>

        <div v-if="rejectingId === course.id" class="mt-4 border-t border-white/30 pt-4 dark:border-white/10">
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">دلیل رد شدن</label>
          <textarea
            v-model="rejectionReason"
            rows="2"
            class="glass mt-1 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white"
          />
          <div class="mt-2 flex gap-2">
            <button
              :disabled="!rejectionReason || busyId === course.id"
              class="rounded-md bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-500 disabled:opacity-50"
              @click="confirmReject(course.id)"
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
