<script setup lang="ts">
// "Report a problem" for the instructor: their description plus the errors this page caught
// (useLiveLog). The backend attaches their recent server-side errors; the developer reads it
// in /admin/dev-log.
const emit = defineEmits<{ close: [] }>()
const { request } = useApi()
const { entries } = useLiveLog()
const route = useRoute()

const message = ref('')
const sending = ref(false)
const sent = ref(false)
const error = ref('')

async function send() {
  error.value = ''
  if (!message.value.trim()) {
    error.value = 'لطفاً بنویسید چه مشکلی پیش آمده است.'
    return
  }
  sending.value = true
  try {
    await request('/support/reports/', {
      method: 'POST',
      body: {
        message: message.value,
        page_url: route.fullPath,
        browser_events: entries.value.slice(0, 30).map(({ at, level, kind, message, detail }) => ({ at, level, kind, message, detail })),
      },
    })
    sent.value = true
  } catch (err) {
    error.value = getErrorMessage(err, 'ارسال گزارش انجام نشد. لطفاً دوباره تلاش کنید.')
  } finally {
    sending.value = false
  }
}
</script>

<template>
  <div class="fixed inset-0 z-[150] flex items-center justify-center bg-black/50 p-4" @click.self="emit('close')">
    <div class="glass w-full max-w-lg rounded-2xl p-6">
      <h2 class="text-lg font-bold text-gray-900 dark:text-white">گزارش مشکل به پشتیبانی</h2>
      <template v-if="!sent">
        <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
          بنویسید چه کاری می‌کردید و چه اتفاقی افتاد. خطاهای اخیر همین صفحه و حساب شما خودکار ضمیمه می‌شود.
        </p>
        <textarea
          v-model="message"
          rows="5"
          maxlength="4000"
          placeholder="مثلاً: روی «ثبت دوره» زدم ولی هیچ اتفاقی نیفتاد."
          class="glass mt-4 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white"
        />
        <p class="mt-2 text-xs text-gray-500 dark:text-gray-400">
          صفحه: <span dir="ltr">{{ route.fullPath }}</span> · {{ entries.length }} خطای ثبت‌شده در این صفحه
        </p>
        <p v-if="error" class="mt-2 text-sm text-red-600">{{ error }}</p>
        <div class="mt-4 flex gap-3">
          <button
            type="button"
            :disabled="sending"
            class="rounded-md bg-primary-600 px-5 py-2 text-sm font-semibold text-white hover:bg-primary-500 disabled:opacity-50"
            @click="send"
          >
            {{ sending ? 'در حال ارسال...' : 'ارسال گزارش' }}
          </button>
          <button type="button" class="glass rounded-md px-5 py-2 text-sm text-gray-700 dark:text-gray-200" @click="emit('close')">
            انصراف
          </button>
        </div>
      </template>
      <template v-else>
        <p class="mt-3 text-sm text-emerald-600">گزارش شما برای تیم پشتیبانی ارسال شد. ممنون!</p>
        <button type="button" class="glass mt-4 rounded-md px-5 py-2 text-sm text-gray-700 dark:text-gray-200" @click="emit('close')">
          بستن
        </button>
      </template>
    </div>
  </div>
</template>
