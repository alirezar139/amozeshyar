<script setup lang="ts">
definePageMeta({ layout: false, ssr: false })

const authStore = useAuthStore()
const { request } = useApi()
const { theme, toggle: toggleTheme, palette, setPalette } = useTheme()

const layoutName = computed(() =>
  authStore.isAdmin ? 'admin' : authStore.isInstructor ? 'instructor' : 'dashboard'
)

const form = reactive({ first_name: '', last_name: '' })
const avatarFile = ref<File | null>(null)
const avatarPreview = ref<string | null>(null)
const saving = ref(false)
const message = ref('')
const error = ref('')

watchEffect(() => {
  if (authStore.user) {
    form.first_name = authStore.user.first_name
    form.last_name = authStore.user.last_name
  }
})

function onAvatarChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  avatarFile.value = file
  avatarPreview.value = URL.createObjectURL(file)
}

async function saveProfile() {
  saving.value = true
  message.value = ''
  error.value = ''
  try {
    const formData = new FormData()
    formData.append('first_name', form.first_name)
    formData.append('last_name', form.last_name)
    if (avatarFile.value) formData.append('avatar', avatarFile.value)
    const updated = await request<any>('/auth/me/', { method: 'PATCH', body: formData })
    authStore.setSession(authStore.accessToken!, updated)
    avatarFile.value = null
    message.value = 'ذخیره شد.'
  } catch (err) {
    error.value = getErrorMessage(err, 'ذخیره نشد. لطفاً دوباره تلاش کنید.')
  } finally {
    saving.value = false
  }
}

const palettes: Palette[] = ['teal', 'blue', 'purple', 'mono', 'green', 'red', 'orange']
const paletteSwatches: Record<Palette, [string, string]> = {
  teal: ['#157e6c', '#f98307'],
  blue: ['#2563eb', '#db2777'],
  purple: ['#7c3aed', '#ca8a04'],
  mono: ['#475569', '#f98307'],
  green: ['#16a34a', '#f98307'],
  red: ['#dc2626', '#ca8a04'],
  orange: ['#ea580c', '#2563eb'],
}
</script>

<template>
  <NuxtLayout :name="layoutName">
    <div class="mx-auto max-w-2xl">
      <h1 class="text-xl font-bold text-gray-900 dark:text-white">پروفایل من</h1>

      <section class="glass mt-6 rounded-2xl p-6">
        <h2 class="text-sm font-semibold text-gray-900 dark:text-white">اطلاعات حساب</h2>
        <div data-tour="avatar-upload" class="mt-4 flex items-center gap-4">
          <div class="relative h-20 w-20 shrink-0">
            <img
              v-if="avatarPreview || authStore.user?.avatar"
              :src="avatarPreview || (authStore.user as any)?.avatar"
              class="h-20 w-20 rounded-full object-cover"
              alt=""
            />
            <div v-else class="flex h-20 w-20 items-center justify-center rounded-full bg-primary-100 text-2xl font-bold text-primary-700 dark:bg-primary-900/40 dark:text-primary-300">
              {{ authStore.user?.first_name?.[0] }}
            </div>
            <label class="absolute -bottom-1 -left-1 flex h-7 w-7 cursor-pointer items-center justify-center rounded-full bg-primary-600 text-white shadow">
              <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" /><path stroke-linecap="round" stroke-linejoin="round" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
              <input type="file" accept="image/*" class="hidden" @change="onAvatarChange" />
            </label>
          </div>
          <div class="grid flex-1 grid-cols-2 gap-3">
            <div>
              <label class="block text-xs font-medium text-gray-600 dark:text-gray-300">نام</label>
              <input v-model="form.first_name" class="glass mt-1 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white" />
            </div>
            <div>
              <label class="block text-xs font-medium text-gray-600 dark:text-gray-300">نام خانوادگی</label>
              <input v-model="form.last_name" class="glass mt-1 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white" />
            </div>
          </div>
        </div>

        <p v-if="message" class="mt-4 text-sm text-emerald-600">{{ message }}</p>
        <p v-if="error" class="mt-4 text-sm text-red-600">{{ error }}</p>
        <button
          :disabled="saving"
          class="mt-4 rounded-md bg-primary-600 px-5 py-2 text-sm font-semibold text-white hover:bg-primary-500 disabled:opacity-50"
          @click="saveProfile"
        >
          {{ saving ? 'در حال ذخیره...' : 'ذخیره تغییرات' }}
        </button>
      </section>

      <section class="glass mt-6 rounded-2xl p-6">
        <h2 class="text-sm font-semibold text-gray-900 dark:text-white">حالت نمایش</h2>
        <div class="mt-3 flex items-center gap-3">
          <button
            type="button"
            data-tour="theme-toggle"
            class="glass flex items-center gap-2 rounded-md px-4 py-2 text-sm text-gray-700 dark:text-gray-200"
            @click="toggleTheme"
          >
            {{ theme === 'dark' ? 'حالت تاریک (فعال) — تغییر به روشن' : 'حالت روشن (فعال) — تغییر به تاریک' }}
          </button>
        </div>
      </section>

      <section class="glass mt-6 rounded-2xl p-6">
        <h2 class="text-sm font-semibold text-gray-900 dark:text-white">پالت رنگی</h2>
        <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">این انتخاب برای حساب شما ذخیره می‌شود و در همه‌ی دستگاه‌ها اعمال می‌شود.</p>
        <div data-tour="palette-picker" class="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <button
            v-for="p in palettes"
            :key="p"
            type="button"
            class="glass flex flex-col items-center gap-2 rounded-xl p-4 transition"
            :class="palette === p ? 'ring-2 ring-primary-600' : ''"
            @click="setPalette(p)"
          >
            <span class="flex h-8 gap-1">
              <span class="h-8 w-4 rounded-full" :style="{ backgroundColor: paletteSwatches[p][0] }" />
              <span class="h-8 w-4 rounded-full" :style="{ backgroundColor: paletteSwatches[p][1] }" />
            </span>
            <span class="text-xs text-gray-700 dark:text-gray-200">{{ PALETTE_LABELS[p] }}</span>
          </button>
        </div>
      </section>
    </div>
  </NuxtLayout>
</template>
