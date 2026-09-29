<script setup lang="ts">
definePageMeta({ layout: 'admin' })
const { request } = useApi()
const { refresh: refreshSite, teacherName } = useSite()
const SITE_NAME_MAX = 100

// social_links is stored as { label: url }; edited here as rows so links
// can be added and removed freely.
const SUGGESTED_LABELS = ['اینستاگرام', 'تلگرام', 'یوتیوب', 'آپارات', 'لینکدین', 'واتساپ', 'وب‌سایت']
const HEADLINE_MAX = 255
const BIO_SOFT_MAX = 400

const form = reactive({ site_name: '', headline: '', bio: '' })
const links = ref<{ label: string; url: string }[]>([])
const currentCover = ref<string | null>(null)
const removeCover = ref(false)
const coverFile = ref<File | null>(null)
const coverPreview = ref<string | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const currentLogo = ref<string | null>(null)
const removeLogo = ref(false)
const logoFile = ref<File | null>(null)
const logoPreview = ref<string | null>(null)
const logoInput = ref<HTMLInputElement | null>(null)
const dragging = ref(false)
const saving = ref(false)
const savedAt = ref(false)
const error = ref('')
const savedSnapshot = ref('')

function snapshot() {
  return JSON.stringify({ form, links: links.value.filter((l) => l.label.trim() && l.url.trim()) })
}

const { pending } = await useAsyncData('admin-site-settings', async () => {
  const data = await request<any>('/site/settings/')
  form.site_name = data.site_name
  form.headline = data.headline
  form.bio = data.bio
  links.value = Object.entries(data.social_links ?? {}).map(([key, url]) => ({ label: socialLinkLabel(key), url: String(url) }))
  currentCover.value = data.cover_image
  currentLogo.value = data.logo
  savedSnapshot.value = snapshot()
  return data
})

const isDirty = computed(
  () => snapshot() !== savedSnapshot.value || !!coverFile.value || removeCover.value || !!logoFile.value || removeLogo.value,
)
watch(isDirty, (dirty) => {
  if (dirty) savedAt.value = false
})

const shownLogo = computed(() => (removeLogo.value ? null : logoPreview.value || currentLogo.value))
const shownSiteName = computed(() => form.site_name.trim() || teacherName.value)
const shownCover = computed(() => (removeCover.value ? null : coverPreview.value || currentCover.value))
const previewLinks = computed(() => links.value.filter((l) => l.label.trim() && l.url.trim()))
const unusedSuggestions = computed(() => SUGGESTED_LABELS.filter((s) => !links.value.some((l) => l.label.trim() === s)))

function isValidUrl(url: string) {
  return !url.trim() || /^https?:\/\/\S+$/i.test(url.trim())
}

function pickFile(file: File | undefined | null) {
  if (!file || !file.type.startsWith('image/')) return
  coverFile.value = file
  coverPreview.value = URL.createObjectURL(file)
  removeCover.value = false
}

function onCoverChange(e: Event) {
  pickFile((e.target as HTMLInputElement).files?.[0])
  ;(e.target as HTMLInputElement).value = ''
}

function onDrop(e: DragEvent) {
  dragging.value = false
  pickFile(e.dataTransfer?.files?.[0])
}

function onRemoveCover() {
  coverFile.value = null
  coverPreview.value = null
  removeCover.value = !!currentCover.value
}

function onLogoChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  ;(e.target as HTMLInputElement).value = ''
  if (!file || !file.type.startsWith('image/')) return
  logoFile.value = file
  logoPreview.value = URL.createObjectURL(file)
  removeLogo.value = false
}

function onRemoveLogo() {
  logoFile.value = null
  logoPreview.value = null
  removeLogo.value = !!currentLogo.value
}

function addLink(label = '') {
  links.value.push({ label, url: '' })
}

async function save() {
  if (links.value.some((l) => !isValidUrl(l.url))) {
    error.value = 'آدرس لینک‌ها باید با https:// شروع شود.'
    return
  }
  saving.value = true
  error.value = ''
  try {
    // JSON for the text fields (social_links is a JSON object, which a
    // multipart body can't carry), then multipart only if a new image was picked.
    const social_links = Object.fromEntries(previewLinks.value.map((l) => [l.label.trim(), l.url.trim()]))
    const body: Record<string, unknown> = { ...form, social_links }
    if (removeCover.value) body.cover_image = null
    if (removeLogo.value) body.logo = null
    await request('/site/settings/', { method: 'PATCH', body })
    if (removeCover.value) {
      currentCover.value = null
      removeCover.value = false
    }
    if (removeLogo.value) {
      currentLogo.value = null
      removeLogo.value = false
    }
    if (coverFile.value || logoFile.value) {
      const formData = new FormData()
      if (coverFile.value) formData.append('cover_image', coverFile.value)
      if (logoFile.value) formData.append('logo', logoFile.value)
      const updated = await request<any>('/site/settings/', { method: 'PATCH', body: formData })
      currentCover.value = updated.cover_image
      currentLogo.value = updated.logo
      coverFile.value = null
      coverPreview.value = null
      logoFile.value = null
      logoPreview.value = null
    }
    links.value = [...previewLinks.value]
    savedSnapshot.value = snapshot()
    savedAt.value = true
    await refreshSite()
  } catch (err) {
    error.value = getErrorMessage(err, 'ذخیره نشد. لطفاً دوباره تلاش کنید.')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="max-w-6xl">
    <h1 class="text-xl font-bold text-gray-900 dark:text-white">تنظیمات سایت</h1>
    <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
      چیزی که بازدیدکننده‌ها در صفحه‌ی اول می‌بینند. نام شما از
      <NuxtLink to="/profile" class="text-primary-600 hover:underline dark:text-primary-400">پروفایل من</NuxtLink>
      تغییر می‌کند.
    </p>

    <div v-if="pending" class="mt-6 text-gray-500">در حال بارگذاری...</div>
    <div v-else class="mt-6 grid grid-cols-1 items-start gap-6 lg:grid-cols-5">
      <form data-tour="site-settings-form" class="space-y-5 lg:col-span-3" @submit.prevent="save">
        <!-- Brand -->
        <section class="glass rounded-2xl p-6">
          <div class="flex items-center gap-3">
            <span class="glass flex h-9 w-9 items-center justify-center rounded-lg text-header-700 dark:text-header-300">
              <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" /></svg>
            </span>
            <div>
              <h2 class="font-semibold text-gray-900 dark:text-white">نام و لوگوی سایت</h2>
              <p class="text-xs text-gray-500 dark:text-gray-400">بالای همه‌ی صفحه‌ها، در فوتر و عنوان تب مرورگر</p>
            </div>
          </div>
          <div class="mt-5 flex flex-col gap-5 sm:flex-row sm:items-start">
            <input ref="logoInput" type="file" accept="image/*" class="hidden" @change="onLogoChange">
            <div class="flex shrink-0 flex-col items-center gap-2">
              <button
                type="button"
                class="group relative flex h-24 w-24 items-center justify-center overflow-hidden rounded-2xl border-2 border-dashed border-gray-300 transition hover:border-primary-400 dark:border-white/15"
                aria-label="انتخاب لوگو"
                @click="logoInput?.click()"
              >
                <img v-if="shownLogo" :src="shownLogo" alt="" class="h-full w-full object-contain p-2">
                <span v-else class="flex flex-col items-center gap-1 text-gray-400">
                  <svg class="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" /></svg>
                  <span class="text-[11px]">لوگو</span>
                </span>
              </button>
              <button v-if="shownLogo" type="button" class="text-xs text-red-600 hover:underline" @click="onRemoveLogo">حذف لوگو</button>
              <span v-else class="text-[11px] text-gray-500 dark:text-gray-400">PNG شفاف، مربعی</span>
            </div>
            <div class="min-w-0 flex-1">
              <div class="flex items-baseline justify-between">
                <label for="site-name" class="text-sm font-medium text-gray-700 dark:text-gray-200">نام سایت</label>
                <span class="text-xs text-gray-400">{{ form.site_name.length.toLocaleString('fa-IR') }}/{{ SITE_NAME_MAX.toLocaleString('fa-IR') }}</span>
              </div>
              <input
                id="site-name"
                v-model="form.site_name"
                :maxlength="SITE_NAME_MAX"
                :placeholder="`مثلاً: آکادمی ${teacherName.split(' ').slice(-1)[0]}`"
                class="glass mt-1.5 block w-full rounded-lg px-3 py-2.5 text-sm text-gray-900 outline-none transition focus:ring-2 focus:ring-primary-500/50 dark:text-white"
              >
              <p class="mt-1.5 text-xs text-gray-500 dark:text-gray-400">اگر خالی بماند، نام خودتان نمایش داده می‌شود.</p>
              <!-- How the header will look -->
              <div class="glass mt-4 flex items-center gap-2.5 rounded-xl px-4 py-3">
                <img v-if="shownLogo" :src="shownLogo" alt="" class="h-9 w-9 shrink-0 object-contain">
                <span v-else class="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-header-600 text-sm font-extrabold text-white">
                  {{ shownSiteName[0] }}
                </span>
                <span class="truncate text-lg font-bold text-header-700 dark:text-header-400">{{ shownSiteName }}</span>
                <span class="ms-auto shrink-0 text-[11px] text-gray-400">پیش‌نمایش هدر</span>
              </div>
            </div>
          </div>
        </section>

        <!-- About -->
        <section class="glass rounded-2xl p-6">
          <div class="flex items-center gap-3">
            <span class="glass flex h-9 w-9 items-center justify-center rounded-lg text-primary-700 dark:text-primary-300">
              <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>
            </span>
            <div>
              <h2 class="font-semibold text-gray-900 dark:text-white">معرفی</h2>
              <p class="text-xs text-gray-500 dark:text-gray-400">بالای صفحه‌ی اول، کنار نام شما</p>
            </div>
          </div>
          <div class="mt-5 space-y-4">
            <div>
              <div class="flex items-baseline justify-between">
                <label for="headline" class="text-sm font-medium text-gray-700 dark:text-gray-200">عنوان تخصص</label>
                <span class="text-xs text-gray-400">{{ form.headline.length.toLocaleString('fa-IR') }}/{{ HEADLINE_MAX.toLocaleString('fa-IR') }}</span>
              </div>
              <input
                id="headline"
                v-model="form.headline"
                :maxlength="HEADLINE_MAX"
                placeholder="مثلاً: مدرس برنامه‌نویسی پایتون"
                class="glass mt-1.5 block w-full rounded-lg px-3 py-2.5 text-sm text-gray-900 outline-none transition focus:ring-2 focus:ring-primary-500/50 dark:text-white"
              >
            </div>
            <div>
              <div class="flex items-baseline justify-between">
                <label for="bio" class="text-sm font-medium text-gray-700 dark:text-gray-200">درباره‌ی شما</label>
                <span :class="['text-xs', form.bio.length > BIO_SOFT_MAX ? 'text-amber-600' : 'text-gray-400']">
                  {{ form.bio.length.toLocaleString('fa-IR') }}/{{ BIO_SOFT_MAX.toLocaleString('fa-IR') }}
                </span>
              </div>
              <textarea
                id="bio"
                v-model="form.bio"
                rows="5"
                placeholder="چند خط درباره‌ی خودتان، سابقه‌تان و روش تدریستان"
                class="glass mt-1.5 block w-full resize-y rounded-lg px-3 py-2.5 text-sm leading-7 text-gray-900 outline-none transition focus:ring-2 focus:ring-primary-500/50 dark:text-white"
              />
              <p v-if="form.bio.length > BIO_SOFT_MAX" class="mt-1 text-xs text-amber-600">
                متن طولانی است؛ در صفحه‌ی اول، متن کوتاه‌تر بهتر خوانده می‌شود.
              </p>
            </div>
          </div>
        </section>

        <!-- Photo -->
        <section class="glass rounded-2xl p-6">
          <div class="flex items-center gap-3">
            <span class="glass flex h-9 w-9 items-center justify-center rounded-lg text-accent-700 dark:text-accent-300">
              <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
            </span>
            <div>
              <h2 class="font-semibold text-gray-900 dark:text-white">عکس صفحه‌ی اول</h2>
              <p class="text-xs text-gray-500 dark:text-gray-400">عکس پرتره‌ی خودتان؛ قاب عمودی است (۴ به ۵) و از بالا برش می‌خورد</p>
            </div>
          </div>

          <input ref="fileInput" type="file" accept="image/*" class="hidden" @change="onCoverChange">

          <!-- Shown in the exact frame and crop the homepage uses (4:5, object-top), so what you see here is what visitors get -->
          <div v-if="shownCover" class="mt-5 flex flex-col gap-4 sm:flex-row sm:items-end">
            <div class="relative w-full max-w-[13rem] shrink-0 overflow-hidden rounded-[1.75rem] shadow-lg ring-1 ring-black/5 dark:ring-white/10">
              <img :src="shownCover" alt="" class="aspect-[4/5] w-full object-cover object-top">
              <span v-if="coverFile" class="absolute inset-x-2 top-2 rounded-full bg-primary-600/95 px-2 py-0.5 text-center text-[11px] font-medium text-white">
                جدید — هنوز ذخیره نشده
              </span>
            </div>
            <div class="flex flex-col gap-2">
              <p class="text-xs leading-6 text-gray-500 dark:text-gray-400">
                در صفحه‌ی اول دقیقاً همین قسمت از عکس دیده می‌شود. اگر بخش مهمی بریده شده، عکس دیگری انتخاب کنید.
                برای لوگو از بخش «نام و لوگوی سایت» استفاده کنید.
              </p>
              <div class="flex gap-2">
                <button
                  type="button"
                  class="glass rounded-lg px-3 py-1.5 text-sm font-medium text-gray-800 transition hover:-translate-y-0.5 dark:text-gray-100"
                  @click="fileInput?.click()"
                >
                  تغییر عکس
                </button>
                <button
                  type="button"
                  class="rounded-lg px-3 py-1.5 text-sm font-medium text-red-600 transition hover:bg-red-500/10"
                  @click="onRemoveCover"
                >
                  حذف
                </button>
              </div>
            </div>
          </div>
          <button
            v-else
            type="button"
            :class="[
              'mt-5 flex w-full flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed px-4 py-10 text-center transition',
              dragging
                ? 'border-primary-500 bg-primary-500/10'
                : 'border-gray-300 hover:border-primary-400 hover:bg-primary-500/5 dark:border-white/15',
            ]"
            @click="fileInput?.click()"
            @dragover.prevent="dragging = true"
            @dragleave.prevent="dragging = false"
            @drop.prevent="onDrop"
          >
            <svg class="h-10 w-10 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" /></svg>
            <span class="text-sm font-medium text-gray-700 dark:text-gray-200">عکس را اینجا بکشید یا کلیک کنید</span>
            <span class="text-xs text-gray-500 dark:text-gray-400">JPG یا PNG — بدون عکس، تصویر پیش‌فرض نمایش داده می‌شود</span>
            <span v-if="removeCover" class="mt-1 text-xs text-amber-600">عکس فعلی بعد از ذخیره حذف می‌شود</span>
          </button>
        </section>

        <!-- Links -->
        <section class="glass rounded-2xl p-6">
          <div class="flex items-center justify-between gap-3">
            <div class="flex items-center gap-3">
              <span class="glass flex h-9 w-9 items-center justify-center rounded-lg text-nav-700 dark:text-nav-300">
                <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" /></svg>
              </span>
              <div>
                <h2 class="font-semibold text-gray-900 dark:text-white">لینک‌ها و شبکه‌های اجتماعی</h2>
                <p class="text-xs text-gray-500 dark:text-gray-400">در فوتر همه‌ی صفحه‌ها نمایش داده می‌شوند</p>
              </div>
            </div>
            <button
              v-if="links.length"
              type="button"
              class="shrink-0 rounded-lg bg-primary-600/10 px-3 py-1.5 text-sm font-medium text-primary-700 transition hover:bg-primary-600/20 dark:text-primary-300"
              @click="addLink()"
            >
              + لینک جدید
            </button>
          </div>

          <TransitionGroup tag="div" name="row" class="mt-5 space-y-2.5">
            <div v-for="(link, i) in links" :key="i" class="flex items-center gap-2">
              <span :class="['flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-sm font-bold text-white', socialBadgeClass(link)]">
                <template v-if="link.label.trim()">{{ link.label.trim()[0] }}</template>
                <svg v-else class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" /></svg>
              </span>
              <input
                v-model="link.label"
                list="social-label-suggestions"
                placeholder="عنوان"
                aria-label="عنوان لینک"
                class="glass w-28 shrink-0 rounded-lg px-3 py-2 text-sm text-gray-900 outline-none transition focus:ring-2 focus:ring-primary-500/50 sm:w-36 dark:text-white"
              >
              <input
                v-model="link.url"
                dir="ltr"
                placeholder="https://..."
                aria-label="آدرس لینک"
                :class="[
                  'glass min-w-0 flex-1 rounded-lg px-3 py-2 text-sm text-gray-900 outline-none transition focus:ring-2 dark:text-white',
                  isValidUrl(link.url) ? 'focus:ring-primary-500/50' : 'ring-2 ring-red-500/60 focus:ring-red-500/60',
                ]"
              >
              <button
                type="button"
                aria-label="حذف لینک"
                class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-gray-400 transition hover:bg-red-500/10 hover:text-red-600"
                @click="links.splice(i, 1)"
              >
                <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
              </button>
            </div>
          </TransitionGroup>
          <datalist id="social-label-suggestions">
            <option v-for="label in SUGGESTED_LABELS" :key="label" :value="label" />
          </datalist>

          <div v-if="!links.length" class="rounded-xl border-2 border-dashed border-gray-300 px-4 py-6 text-center dark:border-white/15">
            <p class="text-sm text-gray-600 dark:text-gray-300">هنوز لینکی اضافه نکرده‌اید.</p>
            <button
              type="button"
              class="mt-3 rounded-lg bg-primary-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-primary-500"
              @click="addLink()"
            >
              + افزودن لینک
            </button>
          </div>

          <div v-if="unusedSuggestions.length" class="mt-4 flex flex-wrap items-center gap-2">
            <span class="text-xs text-gray-500 dark:text-gray-400">افزودن سریع:</span>
            <button
              v-for="label in unusedSuggestions"
              :key="label"
              type="button"
              class="glass rounded-full px-3 py-1 text-xs text-gray-700 transition hover:-translate-y-0.5 hover:text-primary-700 dark:text-gray-200 dark:hover:text-primary-300"
              @click="addLink(label)"
            >
              + {{ label }}
            </button>
          </div>
        </section>

        <!-- Save bar -->
        <div class="glass sticky bottom-4 z-10 flex items-center justify-between gap-3 rounded-2xl px-5 py-3 shadow-lg">
          <p class="text-sm">
            <span v-if="error" class="text-red-600">{{ error }}</span>
            <span v-else-if="isDirty" class="flex items-center gap-2 text-amber-600 dark:text-amber-400">
              <span class="h-2 w-2 rounded-full bg-amber-500" />
              تغییرات ذخیره نشده
            </span>
            <span v-else-if="savedAt" class="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400">
              <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" /></svg>
              ذخیره شد و روی سایت اعمال شد
            </span>
            <span v-else class="text-gray-500 dark:text-gray-400">همه‌چیز به‌روز است</span>
          </p>
          <button
            type="submit"
            :disabled="saving || !isDirty"
            class="shrink-0 rounded-lg bg-primary-600 px-6 py-2 text-sm font-semibold text-white shadow-lg shadow-primary-600/30 transition hover:bg-primary-500 disabled:cursor-not-allowed disabled:opacity-40 disabled:shadow-none"
          >
            {{ saving ? 'در حال ذخیره...' : 'ذخیره' }}
          </button>
        </div>
      </form>

      <!-- Live preview of the homepage hero -->
      <aside class="lg:sticky lg:top-6 lg:col-span-2">
        <div class="flex items-center justify-between">
          <p class="text-sm font-semibold text-gray-700 dark:text-gray-200">پیش‌نمایش صفحه‌ی اول</p>
          <NuxtLink to="/" target="_blank" class="text-xs text-primary-600 hover:underline dark:text-primary-400">دیدن سایت ↗</NuxtLink>
        </div>
        <div class="glass mt-3 overflow-hidden rounded-2xl">
          <div class="flex justify-center bg-gradient-to-br from-primary-500/15 to-accent-500/15 px-6 pb-6 pt-8">
            <IllustrationPortraitStack :src="shownCover" size="sm" class="w-40" />
          </div>
          <div class="p-5">
            <p class="text-2xl font-black text-gray-900 dark:text-white">{{ teacherName }}</p>
            <p v-if="form.headline" class="mt-1 bg-gradient-to-l from-primary-600 to-accent-500 bg-clip-text font-bold text-transparent dark:from-primary-300 dark:to-accent-300">
              {{ form.headline }}
            </p>
            <p class="mt-2 line-clamp-4 whitespace-pre-line text-sm leading-6 text-gray-600 dark:text-gray-300">
              {{ form.bio || 'متن معرفی شما اینجا نمایش داده می‌شود.' }}
            </p>
            <div v-if="previewLinks.length" class="mt-4 flex flex-wrap gap-1.5 border-t border-white/30 pt-4 dark:border-white/10">
              <span
                v-for="link in previewLinks"
                :key="link.label"
                class="inline-flex items-center gap-1.5 rounded-full bg-black/5 py-0.5 pe-2.5 ps-0.5 text-xs text-gray-700 dark:bg-white/10 dark:text-gray-200"
              >
                <span :class="['flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold text-white', socialBadgeClass(link)]">
                  {{ link.label.trim()[0] }}
                </span>
                {{ link.label }}
              </span>
            </div>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.row-enter-active,
.row-leave-active {
  transition: all 0.2s ease;
}
.row-enter-from,
.row-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
