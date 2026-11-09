<script setup lang="ts">
// Step 2: the page the emailed link opens (#uid=&token=). The token is single-use and expires;
// on success every session of the account is signed out, so the user logs in again.
// It travels in the URL fragment, which browsers never send to a server: it can't end up in the
// nginx or SSR logs. It's read once on the client, then removed from the address bar.
const { request } = useApi()
const { openLogin } = useAuthModal()
const { siteName } = useSite()
useSeoMeta({ title: () => `رمز عبور تازه | ${siteName.value}`, robots: 'noindex' })
useHead({ meta: [{ name: 'referrer', content: 'no-referrer' }] })

const uid = ref('')
const token = ref('')
const ready = ref(false)
onMounted(() => {
  const params = new URLSearchParams(window.location.hash.slice(1))
  uid.value = params.get('uid') ?? ''
  token.value = params.get('token') ?? ''
  history.replaceState(null, '', window.location.pathname)
  ready.value = true
})
const password = ref('')
const repeat = ref('')
const saving = ref(false)
const error = ref('')
const done = ref('')

async function submit() {
  if (password.value !== repeat.value) {
    error.value = 'دو رمز با هم یکی نیستند.'
    return
  }
  saving.value = true
  error.value = ''
  try {
    const res = await request<{ detail: string }>('/auth/password-reset/confirm/', {
      method: 'POST',
      body: { uid: uid.value, token: token.value, password: password.value },
    })
    done.value = res.detail
  } catch (err) {
    error.value = getFirstErrorMessage(err, 'رمز ثبت نشد. لطفاً دوباره تلاش کنید.')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="mx-auto max-w-md px-4 py-16 sm:px-6">
    <div class="glass rounded-2xl px-6 py-8">
      <h1 class="text-xl font-bold text-gray-900 dark:text-white">ساختن رمز عبور تازه</h1>

      <template v-if="done">
        <p class="mt-4 rounded-xl bg-emerald-500/10 px-4 py-3 text-sm text-emerald-800 dark:text-emerald-200" role="status">{{ done }}</p>
        <button type="button" class="mt-6 w-full rounded-md bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-500" @click="openLogin">
          ورود با رمز تازه
        </button>
      </template>

      <p v-else-if="!ready" class="mt-4 text-sm text-gray-500">در حال بارگذاری…</p>

      <template v-else-if="!uid || !token">
        <p class="mt-4 text-sm leading-7 text-gray-600 dark:text-gray-300">این لینک کامل نیست. لینک را از ایمیل دوباره باز کنید یا درخواست تازه بدهید.</p>
        <NuxtLink to="/auth/forgot-password" class="mt-4 inline-block text-sm font-semibold text-primary-600 hover:underline dark:text-primary-400">درخواست لینک تازه</NuxtLink>
      </template>

      <form v-else class="mt-4 space-y-4" @submit.prevent="submit">
        <label class="block">
          <span class="block text-sm font-medium text-gray-700 dark:text-gray-200">رمز تازه (دست‌کم ۱۰ نویسه)</span>
          <FormPasswordInput v-model="password" required minlength="10" autocomplete="new-password" />
        </label>
        <label class="block">
          <span class="block text-sm font-medium text-gray-700 dark:text-gray-200">تکرار رمز تازه</span>
          <FormPasswordInput v-model="repeat" required minlength="10" autocomplete="new-password" />
        </label>
        <p v-if="error" class="text-sm text-red-600" role="alert">
          {{ error }}
          <NuxtLink v-if="error.includes('منقضی')" to="/auth/forgot-password" class="ms-1 font-semibold underline">درخواست تازه</NuxtLink>
        </p>
        <button type="submit" :disabled="saving" class="w-full rounded-md bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-500 disabled:opacity-50">
          {{ saving ? 'در حال ثبت…' : 'ثبت رمز تازه' }}
        </button>
      </form>
    </div>
  </div>
</template>
