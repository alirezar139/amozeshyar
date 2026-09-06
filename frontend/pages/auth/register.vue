<script setup lang="ts">
const { register } = useAuth()
const authStore = useAuthStore()
const form = reactive({
  first_name: '',
  last_name: '',
  email: '',
  password: '',
  role: 'student' as 'student' | 'instructor',
})
const error = ref('')
const loading = ref(false)

useSeoMeta({ title: 'ثبت‌نام | آموزش‌یار' })

if (authStore.isAuthenticated) {
  await navigateTo(getRoleHome(authStore.user?.role), { replace: true })
}

async function onSubmit() {
  error.value = ''
  loading.value = true
  try {
    await register({ ...form })
    await navigateTo(getRoleHome(form.role))
  } catch (err) {
    error.value = getErrorMessage(err, 'ثبت‌نام ناموفق بود. لطفاً اطلاعات را بررسی کنید.')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="mx-auto flex min-h-[70vh] max-w-md flex-col justify-center px-4 py-12 sm:px-6">
    <div class="glass rounded-2xl p-8 shadow-xl">
    <h1 class="text-2xl font-bold text-gray-900 dark:text-white">ساخت حساب کاربری</h1>
    <form class="mt-8 space-y-4" @submit.prevent="onSubmit">
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">نام</label>
          <input
            v-model="form.first_name"
            required
            class="glass mt-1 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white"
          >
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">نام خانوادگی</label>
          <input
            v-model="form.last_name"
            required
            class="glass mt-1 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white"
          >
        </div>
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">ایمیل</label>
        <input
          v-model="form.email"
          type="email"
          required
          class="glass mt-1 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white"
        >
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">رمز عبور</label>
        <input
          v-model="form.password"
          type="password"
          required
          minlength="10"
          class="glass mt-1 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white"
        >
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">نوع حساب</label>
        <select
          v-model="form.role"
          class="glass mt-1 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white"
        >
          <option value="student">دانشجو</option>
          <option value="instructor">مدرس</option>
        </select>
      </div>
      <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
      <button
        type="submit"
        :disabled="loading"
        class="w-full rounded-md bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-500 disabled:opacity-50"
      >
        {{ loading ? 'در حال ثبت‌نام...' : 'ثبت‌نام' }}
      </button>
    </form>
    <p class="mt-4 text-sm text-gray-600 dark:text-gray-400">
      قبلاً ثبت‌نام کرده‌اید؟
      <NuxtLink to="/auth/login" class="text-primary-600 hover:underline dark:text-primary-400">وارد شوید</NuxtLink>
    </p>
    </div>
  </div>
</template>
