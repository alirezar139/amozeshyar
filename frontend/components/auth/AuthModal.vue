<script setup lang="ts">
const { isOpen, mode, close } = useAuthModal()
const { login, register } = useAuth()
const { request } = useApi()
const authStore = useAuthStore()

const loginForm = reactive({ email: '', password: '' })
const registerForm = reactive({
  first_name: '',
  last_name: '',
  email: '',
  password: '',
  role: 'student' as 'student' | 'instructor',
  interests: '',
})
const resumeFile = ref<File | null>(null)
const introVideoFile = ref<File | null>(null)
const error = ref('')
const loading = ref(false)
const captchaPassToken = ref('')
const captchaRef = ref<{ reload: () => void } | null>(null)

function onResumeChange(event: Event) {
  resumeFile.value = (event.target as HTMLInputElement).files?.[0] ?? null
}

function onIntroVideoChange(event: Event) {
  introVideoFile.value = (event.target as HTMLInputElement).files?.[0] ?? null
}

watch(isOpen, (open) => {
  if (open) error.value = ''
})

function onCaptchaPassed(token: string) {
  captchaPassToken.value = token
  // The puzzle is already a "confirm" gesture on its own (dragging into
  // place and releasing) — if email/password are already filled in,
  // there's nothing left for a separate "ورود" click to add, so just log
  // them in. The button stays as a fallback for whichever field wasn't
  // filled in yet when the puzzle finished.
  if (loginForm.email && loginForm.password) onLoginSubmit()
}

async function onLoginSubmit() {
  error.value = ''
  if (!captchaPassToken.value) {
    error.value = 'لطفاً اول پازل امنیتی را کامل کنید.'
    return
  }
  loading.value = true
  try {
    await login(loginForm.email, loginForm.password, captchaPassToken.value)
    close()
    loginForm.email = ''
    loginForm.password = ''
    captchaPassToken.value = ''
    await navigateTo(getRoleHome(authStore.user?.role))
  } catch (err) {
    error.value = getErrorMessage(err, 'ایمیل یا رمز عبور نادرست است.')
    // The pass token is one-time-use on the backend regardless of whether
    // the login itself succeeds, so a failed login (bad password) needs a
    // fresh puzzle, not just a fresh password field.
    captchaPassToken.value = ''
    captchaRef.value?.reload()
  } finally {
    loading.value = false
  }
}

async function onRegisterSubmit() {
  error.value = ''
  if (registerForm.role === 'instructor' && !resumeFile.value) {
    error.value = 'برای ثبت‌نام به‌عنوان مدرس، بارگذاری رزومه الزامی است.'
    return
  }
  if (registerForm.role === 'instructor' && !introVideoFile.value) {
    error.value = 'برای ثبت‌نام به‌عنوان مدرس، بارگذاری ویدیوی معرفی الزامی است.'
    return
  }
  loading.value = true
  try {
    await register({ ...registerForm })
    if (registerForm.role === 'instructor' && (resumeFile.value || introVideoFile.value)) {
      const formData = new FormData()
      if (resumeFile.value) formData.append('resume', resumeFile.value)
      if (introVideoFile.value) formData.append('intro_video', introVideoFile.value)
      // Best-effort: the account is already created at this point, so a
      // failed upload here shouldn't strand the user outside their new
      // account — they can still upload it later from the instructor panel.
      await request('/instructors/me/', { method: 'PATCH', body: formData }).catch(() => {})
    }
    close()
    const role = registerForm.role
    Object.assign(registerForm, { first_name: '', last_name: '', email: '', password: '', role: 'student', interests: '' })
    resumeFile.value = null
    introVideoFile.value = null
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
            <AuthCaptchaPuzzle ref="captchaRef" @passed="onCaptchaPassed" @reset="captchaPassToken = ''" />
            <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
            <!-- Completing the puzzle already logs you in automatically when
                 both fields are filled — this button only matters as a
                 fallback for whichever field wasn't ready yet at that point. -->
            <p v-if="loading" class="text-center text-sm text-gray-600 dark:text-gray-300">در حال ورود...</p>
            <button
              v-else
              type="submit"
              :disabled="!captchaPassToken"
              class="w-full rounded-md bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-500 disabled:opacity-50"
            >
              ورود
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
            <div v-if="registerForm.role === 'instructor'" class="space-y-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">رزومه (الزامی)</label>
                <input
                  type="file"
                  accept=".pdf,.doc,.docx"
                  required
                  class="glass mt-1 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white"
                  @change="onResumeChange"
                />
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">ویدیوی معرفی (الزامی)</label>
                <input
                  type="file"
                  accept="video/*"
                  required
                  class="glass mt-1 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white"
                  @change="onIntroVideoChange"
                />
                <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">یک ویدیوی کوتاه از خودتان یا نمونه‌ی تدریس، برای بررسی کیفیت توسط ادمین.</p>
              </div>
            </div>
            <div v-else>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">علایق و مهارت‌ها (اختیاری)</label>
              <input
                v-model="registerForm.interests"
                placeholder="مثلاً: برنامه‌نویسی، طراحی، بازاریابی"
                class="glass mt-1 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white"
              />
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
