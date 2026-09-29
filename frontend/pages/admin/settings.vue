<script setup lang="ts">
definePageMeta({ layout: 'admin' })
const { request } = useApi()
const { refresh: refreshSite } = useSite()

// Keys shown as fields; anything else already stored in social_links is kept as-is.
const socialFields = [
  { key: 'instagram', label: 'اینستاگرام' },
  { key: 'telegram', label: 'تلگرام' },
  { key: 'youtube', label: 'یوتیوب' },
  { key: 'website', label: 'وب‌سایت' },
] as const

const form = reactive({ headline: '', bio: '', social_links: {} as Record<string, string> })
const currentCover = ref<string | null>(null)
const coverFile = ref<File | null>(null)
const coverPreview = ref<string | null>(null)
const saving = ref(false)
const message = ref('')
const error = ref('')

const { pending } = await useAsyncData('admin-site-settings', async () => {
  const data = await request<any>('/site/settings/')
  form.headline = data.headline
  form.bio = data.bio
  form.social_links = { ...data.social_links }
  currentCover.value = data.cover_image
  return data
})

function onCoverChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  coverFile.value = file
  coverPreview.value = URL.createObjectURL(file)
}

async function save() {
  saving.value = true
  message.value = ''
  error.value = ''
  try {
    // JSON for the text fields (social_links is a JSON object, which a
    // multipart body can't carry), then multipart only if a new photo was picked.
    await request('/site/settings/', { method: 'PATCH', body: form })
    if (coverFile.value) {
      const formData = new FormData()
      formData.append('cover_image', coverFile.value)
      const updated = await request<any>('/site/settings/', { method: 'PATCH', body: formData })
      currentCover.value = updated.cover_image
      coverFile.value = null
    }
    await refreshSite()
    message.value = 'ذخیره شد.'
  } catch (err) {
    error.value = getErrorMessage(err, 'ذخیره نشد. لطفاً دوباره تلاش کنید.')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="max-w-2xl">
    <h1 class="text-xl font-bold text-gray-900 dark:text-white">تنظیمات سایت</h1>
    <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
      این اطلاعات در صفحه‌ی اول سایت نمایش داده می‌شود. نام شما از «پروفایل من» تغییر می‌کند.
    </p>

    <div v-if="pending" class="mt-6 text-gray-500">در حال بارگذاری...</div>
    <form v-else data-tour="site-settings-form" class="glass mt-6 space-y-4 rounded-2xl p-6" @submit.prevent="save">
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">عنوان تخصص</label>
        <input
          v-model="form.headline"
          placeholder="مثلاً: مدرس برنامه‌نویسی پایتون"
          class="glass mt-1 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white"
        >
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">معرفی</label>
        <textarea
          v-model="form.bio"
          rows="5"
          placeholder="چند خط درباره‌ی خودتان و روش تدریستان"
          class="glass mt-1 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white"
        />
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">عکس صفحه‌ی اول</label>
        <img
          v-if="coverPreview || currentCover"
          :src="coverPreview || currentCover || ''"
          alt=""
          class="mt-2 aspect-[4/3] w-48 rounded-xl object-cover"
        >
        <input
          type="file"
          accept="image/*"
          class="glass mt-2 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white"
          @change="onCoverChange"
        >
      </div>
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div v-for="field in socialFields" :key="field.key">
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">{{ field.label }}</label>
          <input
            v-model="form.social_links[field.key]"
            dir="ltr"
            placeholder="https://..."
            class="glass mt-1 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white"
          >
        </div>
      </div>
      <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
      <p v-if="message" class="text-sm text-emerald-600">{{ message }}</p>
      <button
        type="submit"
        :disabled="saving"
        class="rounded-md bg-primary-600 px-5 py-2 text-sm font-semibold text-white hover:bg-primary-500 disabled:opacity-50"
      >
        {{ saving ? 'در حال ذخیره...' : 'ذخیره' }}
      </button>
    </form>
  </div>
</template>
