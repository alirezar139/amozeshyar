<script setup lang="ts">
const { login } = useAuth()
const authStore = useAuthStore()
const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

useSeoMeta({ title: 'ورود | آموزش‌یار' })

// Already signed in (e.g. session restored from the refresh cookie on load)?
// Don't show a login form for that — just send them where they belong.
if (authStore.isAuthenticated) {
  await navigateTo(getRoleHome(authStore.user?.role), { replace: true })
}

async function onSubmit() {
  error.value = ''
  loading.value = true
  try {
    await login(email.value, password.value)
    await navigateTo(getRoleHome(authStore.user?.role))
  } catch (err) {
    error.value = getErrorMessage(err, 'ایمیل یا رمز عبور نادرست است.')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="mx-auto flex min-h-[70vh] max-w-md flex-col justify-center px-4 py-12 sm:px-6">
    <div class="glass rounded-2xl p-8 shadow-xl">
      <h1 class="text-2xl font-bold text-gray-900 dark:text-white">ورود به حساب کاربری</h1>
      <form class="mt-8 space-y-4" @submit.prevent="onSubmit">
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">ایمیل</label>
          <input
            v-model="email"
            type="email"
            required
            class="glass mt-1 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white"
          >
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">رمز عبور</label>
          <input
            v-model="password"
            type="password"
            required
            class="glass mt-1 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white"
          >
        </div>
        <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
        <button
          type="submit"
          :disabled="loading"
          class="w-full rounded-md bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-500 disabled:opacity-50"
        >
          {{ loading ? 'در حال ورود...' : 'ورود' }}
        </button>
      </form>
      <p class="mt-4 text-sm text-gray-600 dark:text-gray-400">
        حساب کاربری ندارید؟
        <NuxtLink to="/auth/register" class="text-primary-600 hover:underline dark:text-primary-400">ثبت‌نام کنید</NuxtLink>
      </p>
    </div>
  </div>
</template>
