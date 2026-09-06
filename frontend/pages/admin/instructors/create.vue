<script setup lang="ts">
definePageMeta({ layout: 'admin' })
const { request } = useApi()

const form = reactive({
  first_name: '',
  last_name: '',
  email: '',
  password: '',
})
const error = ref('')
const success = ref(false)
const loading = ref(false)

async function onSubmit() {
  error.value = ''
  loading.value = true
  try {
    await request('/auth/admin/create-user/', {
      method: 'POST',
      body: { ...form, role: 'instructor' },
    })
    success.value = true
    form.first_name = ''
    form.last_name = ''
    form.email = ''
    form.password = ''
  } catch (err) {
    error.value = getErrorMessage(err, 'ثبت مدرس ناموفق بود.')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="max-w-lg">
    <h1 class="text-xl font-bold text-gray-900 dark:text-white">افزودن مدرس جدید</h1>
    <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
      حساب مدرس مستقیماً ساخته می‌شود؛ مدرس می‌تواند بعداً با همین ایمیل و رمز عبور وارد شود و پروفایل خود را تکمیل کند.
    </p>

    <form class="glass mt-6 space-y-4 rounded-2xl p-6" @submit.prevent="onSubmit">
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">نام</label>
          <input v-model="form.first_name" required class="glass mt-1 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white">
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">نام خانوادگی</label>
          <input v-model="form.last_name" required class="glass mt-1 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white">
        </div>
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">ایمیل</label>
        <input v-model="form.email" type="email" required class="glass mt-1 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white">
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">رمز عبور اولیه</label>
        <input v-model="form.password" type="password" required minlength="10" class="glass mt-1 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white">
      </div>
      <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
      <p v-if="success" class="text-sm text-emerald-600">مدرس با موفقیت ساخته شد.</p>
      <div class="flex gap-3">
        <button
          type="submit"
          :disabled="loading"
          class="rounded-md bg-primary-600 px-5 py-2 text-sm font-semibold text-white hover:bg-primary-500 disabled:opacity-50"
        >
          {{ loading ? 'در حال ثبت...' : 'ساخت مدرس' }}
        </button>
        <NuxtLink to="/admin/instructors" class="glass rounded-md px-5 py-2 text-sm text-gray-700 dark:text-gray-200">
          بازگشت به لیست
        </NuxtLink>
      </div>
    </form>
  </div>
</template>
