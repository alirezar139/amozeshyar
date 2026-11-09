<script setup lang="ts">
// Step 1 of a forgotten password: ask for a reset link. The answer is the same whether or not
// the email has an account, so this page never says which emails are registered.
const { request } = useApi()
const { siteName } = useSite()
useSeoMeta({ title: () => `فراموشی رمز عبور | ${siteName.value}`, robots: 'noindex' })

const email = ref('')
const sending = ref(false)
const sent = ref('')
const error = ref('')

async function submit() {
  sending.value = true
  error.value = ''
  try {
    const res = await request<{ detail: string }>('/auth/password-reset/', { method: 'POST', body: { email: email.value.trim() } })
    sent.value = res.detail
  } catch (err: any) {
    error.value = err?.response?.status === 429
      ? 'چند بار پشت سر هم درخواست داده‌اید؛ کمی بعد دوباره امتحان کنید.'
      : getFirstErrorMessage(err, 'درخواست ارسال نشد. لطفاً دوباره تلاش کنید.')
  } finally {
    sending.value = false
  }
}
</script>

<template>
  <div class="mx-auto max-w-md px-4 py-16 sm:px-6">
    <div class="glass rounded-2xl px-6 py-8">
      <h1 class="text-xl font-bold text-gray-900 dark:text-white">فراموشی رمز عبور</h1>
      <template v-if="sent">
        <p class="mt-4 rounded-xl bg-emerald-500/10 px-4 py-3 text-sm leading-7 text-emerald-800 dark:text-emerald-200" role="status">{{ sent }}</p>
        <p class="mt-3 text-sm leading-7 text-gray-600 dark:text-gray-300">
          لینک تا مدت کوتاهی و فقط یک بار کار می‌کند. اگر پیامی نرسید، پوشه‌ی هرزنامه را ببینید یا به مدرس پیام دهید.
        </p>
        <NuxtLink to="/" class="mt-6 inline-block text-sm font-semibold text-primary-600 hover:underline dark:text-primary-400">بازگشت به سایت</NuxtLink>
      </template>
      <form v-else class="mt-4 space-y-4" @submit.prevent="submit">
        <p class="text-sm leading-7 text-gray-600 dark:text-gray-300">ایمیل حساب‌تان را وارد کنید تا لینک ساختن رمز تازه برایتان فرستاده شود.</p>
        <label class="block">
          <span class="block text-sm font-medium text-gray-700 dark:text-gray-200">ایمیل</span>
          <input v-model="email" type="email" required autofocus autocomplete="email" dir="ltr" class="glass mt-1 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white">
        </label>
        <p v-if="error" class="text-sm text-red-600" role="alert">{{ error }}</p>
        <button type="submit" :disabled="sending" class="w-full rounded-md bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-500 disabled:opacity-50">
          {{ sending ? 'در حال ارسال…' : 'فرستادن لینک بازیابی' }}
        </button>
      </form>
    </div>
  </div>
</template>
