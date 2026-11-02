<script setup lang="ts">
definePageMeta({ layout: 'dashboard' })
const { request } = useApi()
const { formatGregorianDate } = useJalali()

const { data: orders, pending } = await useAsyncData('my-orders', async () => {
  const page = await request<{ results: any[] }>('/payments/orders/')
  return page.results
})

const STATUS: Record<string, { label: string; tone: string }> = {
  paid: { label: 'پرداخت‌شده', tone: 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300' },
  pending: { label: 'در انتظار پرداخت', tone: 'bg-amber-500/15 text-amber-700 dark:text-amber-300' },
  failed: { label: 'ناموفق', tone: 'bg-red-500/15 text-red-700 dark:text-red-300' },
  canceled: { label: 'لغوشده', tone: 'bg-gray-500/15 text-gray-700 dark:text-gray-300' },
  refunded: { label: 'بازگشت وجه', tone: 'bg-gray-500/15 text-gray-700 dark:text-gray-300' },
}

function price(amount: string | number) {
  return Number(amount) > 0 ? `${Number(amount).toLocaleString('fa-IR')} تومان` : 'رایگان'
}
</script>

<template>
  <div>
    <h1 data-tour="orders-heading" class="text-xl font-bold text-gray-900 dark:text-white">سفارش‌های من</h1>
    <p class="mt-2 text-gray-600 dark:text-gray-400">سابقه‌ی خریدهای شما در این بخش نمایش داده می‌شود.</p>

    <div v-if="pending" class="mt-6 text-gray-500">در حال بارگذاری...</div>

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
          <span class="rounded-full px-2.5 py-0.5 text-xs font-semibold" :class="STATUS[order.status]?.tone">
            {{ STATUS[order.status]?.label ?? order.status }}
          </span>
        </div>
        <div v-for="item in order.items" :key="item.course_slug" class="mt-2">
          <NuxtLink :to="`/courses/${item.course_slug}`" class="font-semibold text-gray-900 hover:text-primary-600 dark:text-white">
            {{ item.course_title }}
          </NuxtLink>
        </div>
        <div class="mt-2 flex flex-wrap items-center gap-x-3 text-sm text-gray-700 dark:text-gray-200">
          <span class="font-bold">{{ price(order.total_amount) }}</span>
          <span v-if="order.coupon_code" class="text-xs text-gray-500" dir="ltr">({{ order.coupon_code }})</span>
        </div>
      </li>
    </ul>
  </div>
</template>
