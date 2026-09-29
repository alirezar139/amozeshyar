<script setup lang="ts">
definePageMeta({ layout: 'admin' })
const { request } = useApi()
const { refresh: refreshSite } = useSite()

// social_links is stored as { label: url }; edited here as rows so links
// can be added and removed freely. Older English keys show in Persian.
const LEGACY_LABELS: Record<string, string> = {
  instagram: 'اینستاگرام', telegram: 'تلگرام', youtube: 'یوتیوب', website: 'وب‌سایت', linkedin: 'لینکدین',
}
const SUGGESTED_LABELS = ['اینستاگرام', 'تلگرام', 'یوتیوب', 'وب‌سایت', 'لینکدین', 'واتساپ', 'آپارات']

const form = reactive({ headline: '', bio: '' })
const links = ref<{ label: string; url: string }[]>([])
const currentCover = ref<string | null>(null)
const removeCover = ref(false)
const coverFile = ref<File | null>(null)
const coverPreview = ref<string | null>(null)
const saving = ref(false)
const message = ref('')
const error = ref('')

const { pending } = await useAsyncData('admin-site-settings', async () => {
  const data = await request<any>('/site/settings/')
  form.headline = data.headline
  form.bio = data.bio
  links.value = Object.entries(data.social_links ?? {}).map(([key, url]) => ({ label: LEGACY_LABELS[key] ?? key, url: String(url) }))
  currentCover.value = data.cover_image
  return data
})

function onCoverChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  coverFile.value = file
  coverPreview.value = URL.createObjectURL(file)
  removeCover.value = false
}

function onRemoveCover() {
  coverFile.value = null
  coverPreview.value = null
  removeCover.value = true
}

function addLink() {
  links.value.push({ label: '', url: '' })
}

async function save() {
  saving.value = true
  message.value = ''
  error.value = ''
  try {
    // JSON for the text fields (social_links is a JSON object, which a
    // multipart body can't carry), then multipart only if a new photo was picked.
    const social_links = Object.fromEntries(
      links.value.filter((l) => l.label.trim() && l.url.trim()).map((l) => [l.label.trim(), l.url.trim()]),
    )
    const body: Record<string, unknown> = { ...form, social_links }
    if (removeCover.value) body.cover_image = null
    await request('/site/settings/', { method: 'PATCH', body })
    if (removeCover.value) {
      currentCover.value = null
      removeCover.value = false
    }
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
        <div v-if="!removeCover && (coverPreview || currentCover)" class="mt-2 flex items-end gap-3">
          <img :src="coverPreview || currentCover || ''" alt="" class="aspect-[4/3] w-48 rounded-xl object-cover">
          <button type="button" class="text-sm text-red-600 hover:underline" @click="onRemoveCover">حذف عکس</button>
        </div>
        <p v-else-if="removeCover" class="mt-2 text-sm text-gray-500 dark:text-gray-400">
          عکس بعد از ذخیره حذف می‌شود و تصویر پیش‌فرض نمایش داده می‌شود.
        </p>
        <input
          type="file"
          accept="image/*"
          class="glass mt-2 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white"
          @change="onCoverChange"
        >
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">لینک‌ها و شبکه‌های اجتماعی</label>
        <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">در فوتر سایت نمایش داده می‌شوند.</p>
        <datalist id="social-label-suggestions">
          <option v-for="label in SUGGESTED_LABELS" :key="label" :value="label" />
        </datalist>
        <div v-for="(link, i) in links" :key="i" class="mt-2 flex items-center gap-2">
          <input
            v-model="link.label"
            list="social-label-suggestions"
            placeholder="عنوان (مثلاً اینستاگرام)"
            class="glass w-36 shrink-0 rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white"
          >
          <input
            v-model="link.url"
            dir="ltr"
            placeholder="https://..."
            class="glass min-w-0 flex-1 rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white"
          >
          <button
            type="button"
            aria-label="حذف لینک"
            class="shrink-0 rounded-md px-2 py-2 text-red-600 hover:bg-red-50/50 dark:hover:bg-red-950/40"
            @click="links.splice(i, 1)"
          >
            <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>
        <button
          type="button"
          class="glass mt-2 rounded-md px-3 py-1.5 text-sm text-gray-700 dark:text-gray-200"
          @click="addLink"
        >
          + افزودن لینک
        </button>
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
