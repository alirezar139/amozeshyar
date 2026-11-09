<script setup lang="ts">
definePageMeta({ layout: 'dashboard' })
const { request } = useApi()
const { formatGregorianDate } = useJalali()

const { data: orders, pending, error, refresh } = await useAsyncData('my-orders', async () => {
  const page = await request<{ results: any[] }>('/payments/orders/')
  return page.results
})

// ---------- refund request ----------
const asking = ref<any>(null)
const reason = ref('')
const sending = ref(false)
const askError = ref('')
const notice = ref('')

function canAsk(order: any) {
  return order.status === 'paid' && Number(order.total_amount) > 0 && order.refund?.status !== 'pending'
}

function openAsk(order: any) {
  asking.value = order
  reason.value = ''
  askError.value = ''
}

async function sendRequest() {
  sending.value = true
  askError.value = ''
  try {
    await request(`/payments/orders/${asking.value.id}/refund-request/`, { method: 'POST', body: { reason: reason.value.trim() } })
    notice.value = 'درخواست شما برای مدرس فرستاده شد؛ نتیجه را در پیام‌ها و همین صفحه می‌بینید.'
    asking.value = null
    await refresh()
  } catch (err) {
    askError.value = getFirstErrorMessage(err, 'درخواست ثبت نشد. لطفاً دوباره تلاش کنید.')
  } finally {
    sending.value = false
  }
}
</script>

<template>
  <div>
    <h1 data-tour="orders-heading" class="text-xl font-bold text-gray-900 dark:text-white">سفارش‌های من</h1>
    <p class="mt-2 text-gray-600 dark:text-gray-400">سابقه‌ی خریدهای شما در این بخش نمایش داده می‌شود.</p>

    <p v-if="notice" class="glass mt-4 rounded-xl px-4 py-2 text-sm text-emerald-700 dark:text-emerald-300" role="status">{{ notice }}</p>

    <div v-if="pending" class="mt-6 text-gray-500">در حال بارگذاری...</div>

    <p v-else-if="error" class="glass mt-6 rounded-2xl px-5 py-4 text-sm text-red-600">سفارش‌ها بارگذاری نشد. صفحه را دوباره باز کنید.</p>

    <div v-else-if="!orders?.length" class="glass mt-6 rounded-2xl px-6 py-12 text-center">
      <p class="font-semibold text-gray-800 dark:text-gray-100">هنوز سفارشی ثبت نکرده‌اید</p>
      <NuxtLink to="/courses" class="mt-4 inline-block rounded-xl bg-primary-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-primary-500">
        مشاهده‌ی دوره‌ها
      </NuxtLink>
    </div>

    <ul v-else class="mt-6 space-y-3">
      <li v-for="order in orders" :key="order.id" class="glass rounded-2xl px-5 py-4">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div class="text-sm text-gray-500 dark:text-gray-400">
            سفارش {{ toPersianDigits(order.id) }} · {{ formatGregorianDate(new Date(order.created_at)) }}
          </div>
          <SalesStatusBadge :map="ORDER_STATUS" :status="order.status" />
        </div>
        <div v-for="item in order.items" :key="item.course_slug" class="mt-2">
          <NuxtLink :to="`/courses/${item.course_slug}`" class="font-semibold text-gray-900 hover:text-primary-600 dark:text-white">
            {{ item.course_title }}
          </NuxtLink>
        </div>
        <div class="mt-2 flex flex-wrap items-center gap-x-3 text-sm text-gray-700 dark:text-gray-200">
          <span class="font-bold">{{ formatToman(order.total_amount) }}</span>
          <span v-if="order.coupon_code" class="text-xs text-gray-500" dir="ltr">({{ order.coupon_code }})</span>
        </div>
        <div v-if="order.refund" class="mt-3 flex flex-wrap items-center gap-2 text-xs text-gray-600 dark:text-gray-300">
          <span>درخواست استرداد:</span>
          <SalesStatusBadge :map="REFUND_STATUS" :status="order.refund.status" />
          <span v-if="order.refund.admin_note">— {{ order.refund.admin_note }}</span>
        </div>
        <button v-if="canAsk(order)" type="button" class="mt-3 text-xs font-semibold text-gray-500 hover:text-red-600 hover:underline" @click="openAsk(order)">
          درخواست استرداد وجه
        </button>
      </li>
    </ul>

    <ChatModal v-if="asking" title="درخواست استرداد وجه" @close="asking = null">
      <form class="space-y-3 px-5 py-4 text-sm" @submit.prevent="sendRequest">
        <p class="leading-6 text-gray-600 dark:text-gray-300">
          سفارش {{ toPersianDigits(asking.id) }} ({{ formatToman(asking.total_amount) }}). مدرس درخواست را بررسی می‌کند؛
          اگر مبلغ برگردانده شود، دسترسی به دوره‌های این سفارش بسته می‌شود.
        </p>
        <textarea v-model="reason" required maxlength="1000" rows="4" placeholder="دلیل درخواست را بنویسید…" class="glass w-full rounded-md px-3 py-2" />
        <p v-if="askError" class="text-red-600" role="alert">{{ askError }}</p>
        <button type="submit" :disabled="sending || !reason.trim()" class="w-full rounded-xl bg-primary-600 px-4 py-2.5 font-semibold text-white hover:bg-primary-500 disabled:opacity-60">
          {{ sending ? 'در حال ارسال…' : 'ارسال درخواست' }}
        </button>
      </form>
    </ChatModal>
  </div>
</template>
