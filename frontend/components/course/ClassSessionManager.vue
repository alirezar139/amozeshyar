<script setup lang="ts">
const props = defineProps<{ courseId: number }>()
const { request } = useApi()

const { data: sessions, refresh } = await useAsyncData(`course-${props.courseId}-sessions`, async () => {
  const page = await request<{ results: any[] }>('/class-sessions/')
  return page.results
    .filter((s: any) => s.course === props.courseId)
    .sort((a: any, b: any) => new Date(a.starts_at).getTime() - new Date(b.starts_at).getTime())
})

const form = reactive({ title: '', starts_at: '', is_online: true, location_note: '' })
const creating = ref(false)
const error = ref('')

async function addSession() {
  error.value = ''
  creating.value = true
  try {
    await request('/class-sessions/', {
      method: 'POST',
      body: {
        course: props.courseId,
        title: form.title,
        starts_at: new Date(form.starts_at).toISOString(),
        is_online: form.is_online,
        location_note: form.location_note,
      },
    })
    Object.assign(form, { title: '', starts_at: '', is_online: true, location_note: '' })
    await refresh()
  } catch (err) {
    error.value = getErrorMessage(err, 'ثبت کلاس ناموفق بود.')
  } finally {
    creating.value = false
  }
}

const deletingId = ref<number | null>(null)
async function removeSession(id: number) {
  deletingId.value = id
  try {
    await request(`/class-sessions/${id}/`, { method: 'DELETE' })
    await refresh()
  } finally {
    deletingId.value = null
  }
}

function formatDateTime(iso: string) {
  return new Date(iso).toLocaleString('fa-IR', { dateStyle: 'medium', timeStyle: 'short' })
}
</script>

<template>
  <div>
    <div class="glass rounded-2xl p-6">
      <h2 class="font-semibold text-gray-900 dark:text-white">افزودن کلاس زمان‌بندی‌شده</h2>
      <form class="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2" @submit.prevent="addSession">
        <input
          v-model="form.title"
          required
          placeholder="عنوان کلاس، مثلاً «جلسه‌ی پرسش و پاسخ زنده»"
          class="glass rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white sm:col-span-2"
        >
        <input
          v-model="form.starts_at"
          type="datetime-local"
          required
          class="glass rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white"
        >
        <label class="glass flex items-center gap-2 rounded-md px-3 py-2 text-sm text-gray-700 dark:text-gray-200">
          <input v-model="form.is_online" type="checkbox" class="h-4 w-4">
          کلاس آنلاین است
        </label>
        <input
          v-model="form.location_note"
          :placeholder="form.is_online ? 'توضیح اضافه (اختیاری) — کلاس آنلاین از همین سامانه برگزار می‌شود' : 'آدرس محل برگزاری'"
          class="glass rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white sm:col-span-2"
        >
        <button
          type="submit"
          :disabled="creating"
          class="rounded-md bg-primary-600 px-5 py-2 text-sm font-semibold text-white hover:bg-primary-500 disabled:opacity-50 sm:col-span-2"
        >
          {{ creating ? 'در حال ثبت...' : 'افزودن به تقویم' }}
        </button>
      </form>
      <p v-if="error" class="mt-2 text-sm text-red-600">{{ error }}</p>
    </div>

    <div class="mt-6 space-y-3">
      <div v-for="session in sessions" :key="session.id" class="glass flex flex-wrap items-center justify-between gap-3 rounded-xl p-4">
        <div>
          <p class="font-medium text-gray-900 dark:text-white">{{ session.title }}</p>
          <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
            {{ formatDateTime(session.starts_at) }} — {{ session.is_online ? 'آنلاین' : 'حضوری' }}
          </p>
          <p v-if="session.location_note" class="mt-1 text-xs text-gray-500 dark:text-gray-400">{{ session.location_note }}</p>
        </div>
        <div class="flex shrink-0 items-center gap-2">
          <NuxtLink
            v-if="session.is_online"
            :to="`/classroom/${session.id}`"
            class="rounded-md bg-primary-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-primary-500"
          >
            پیوستن به کلاس
          </NuxtLink>
          <button
            type="button"
            :disabled="deletingId === session.id"
            class="rounded-md border border-red-300 px-3 py-1.5 text-xs font-semibold text-red-600 hover:bg-red-50 disabled:opacity-50 dark:border-red-800 dark:hover:bg-red-950/40"
            @click="removeSession(session.id)"
          >
            حذف
          </button>
        </div>
      </div>
      <p v-if="sessions && sessions.length === 0" class="text-gray-600 dark:text-gray-400">هنوز کلاسی زمان‌بندی نشده است.</p>
    </div>
  </div>
</template>
