<script setup lang="ts">
const { isOpen, mode, close } = useAuthModal()
const { login, register } = useAuth()
const authStore = useAuthStore()

const loginForm = reactive({ email: '', password: '' })
const registerForm = reactive({
  first_name: '',
  last_name: '',
  email: '',
  password: '',
  role: 'student' as 'student' | 'instructor',
})
const error = ref('')
const loading = ref(false)

watch(isOpen, (open) => {
  if (open) error.value = ''
})

async function onLoginSubmit() {
  error.value = ''
  loading.value = true
  try {
    await login(loginForm.email, loginForm.password)
    close()
    loginForm.email = ''
    loginForm.password = ''
    await navigateTo(getRoleHome(authStore.user?.role))
  } catch (err) {
    error.value = getErrorMessage(err, 'ایمیل یا رمز عبور نادرست است.')
  } finally {
    loading.value = false
  }
}

async function onRegisterSubmit() {
  error.value = ''
  loading.value = true
  try {
    await register({ ...registerForm })
    close()
    const role = registerForm.role
    Object.assign(registerForm, { first_name: '', last_name: '', email: '', password: '', role: 'student' })
    await navigateTo(getRoleHome(role))
  } catch (err) {
    error.value = getErrorMessage(err, 'ثبت‌نام ناموفق بود. لطفاً اطلاعات را بررسی کنید.')
  } finally {
    loading.value = false
  }
}

function onBackdropClick() {
  close()
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="isOpen"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm px-4 py-8"
        @click.self="onBackdropClick"
      >
        <div class="glass w-full max-w-sm rounded-2xl p-8 shadow-2xl">
          <div class="flex items-center justify-between">
            <h2 class="text-xl font-bold text-gray-900 dark:text-white">
              {{ mode === 'login' ? 'ورود به حساب کاربری' : 'ساخت حساب کاربری' }}
            </h2>
            <button aria-label="بستن" class="text-gray-500 hover:text-gray-800 dark:hover:text-white" @click="close">
              ✕
            </button>
          </div>

          <form v-if="mode === 'login'" class="mt-6 space-y-4" @submit.prevent="onLoginSubmit">
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">ایمیل</label>
              <input v-model="loginForm.email" type="email" required autofocus class="glass mt-1 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white">
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">رمز عبور</label>
              <input v-model="loginForm.password" type="password" required class="glass mt-1 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white">
            </div>
            <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
            <button
              type="submit"
              :disabled="loading"
              class="w-full rounded-md bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-500 disabled:opacity-50"
            >
              {{ loading ? 'در حال ورود...' : 'ورود' }}
            </button>
            <p class="text-sm text-gray-600 dark:text-gray-400">
              حساب کاربری ندارید؟
              <button type="button" class="text-primary-600 hover:underline dark:text-primary-400" @click="mode = 'register'">
                ثبت‌نام کنید
              </button>
            </p>
          </form>

          <form v-else class="mt-6 space-y-4" @submit.prevent="onRegisterSubmit">
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">نام</label>
                <input v-model="registerForm.first_name" required class="glass mt-1 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white">
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">نام خانوادگی</label>
                <input v-model="registerForm.last_name" required class="glass mt-1 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white">
              </div>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">ایمیل</label>
              <input v-model="registerForm.email" type="email" required class="glass mt-1 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white">
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">رمز عبور</label>
              <input v-model="registerForm.password" type="password" required minlength="10" class="glass mt-1 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white">
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">نوع حساب</label>
              <select v-model="registerForm.role" class="glass mt-1 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white">
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
            <p class="text-sm text-gray-600 dark:text-gray-400">
              قبلاً ثبت‌نام کرده‌اید؟
              <button type="button" class="text-primary-600 hover:underline dark:text-primary-400" @click="mode = 'login'">
                وارد شوید
              </button>
            </p>
          </form>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
