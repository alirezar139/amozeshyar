<script setup lang="ts">
const { isOpen, close } = useLoginModal()
const { login } = useAuth()
const authStore = useAuthStore()

const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function onSubmit() {
  error.value = ''
  loading.value = true
  try {
    await login(email.value, password.value)
    close()
    email.value = ''
    password.value = ''
    await navigateTo(getRoleHome(authStore.user?.role))
  } catch (err) {
    error.value = getErrorMessage(err, 'ایمیل یا رمز عبور نادرست است.')
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
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm px-4"
        @click.self="onBackdropClick"
      >
        <div class="glass w-full max-w-sm rounded-2xl p-8 shadow-2xl">
          <div class="flex items-center justify-between">
            <h2 class="text-xl font-bold text-gray-900 dark:text-white">ورود به حساب کاربری</h2>
            <button aria-label="بستن" class="text-gray-500 hover:text-gray-800 dark:hover:text-white" @click="close">
              ✕
            </button>
          </div>

          <form class="mt-6 space-y-4" @submit.prevent="onSubmit">
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">ایمیل</label>
              <input
                v-model="email"
                type="email"
                required
                autofocus
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
            <NuxtLink to="/auth/register" class="text-primary-600 hover:underline dark:text-primary-400" @click="close">
              ثبت‌نام کنید
            </NuxtLink>
          </p>
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
