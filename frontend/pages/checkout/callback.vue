<script setup lang="ts">
// Where a buyer lands after checkout: the API's payment callback redirects
// here with ?order_id=&status= once it has asked ZarinPal (free orders come
// straight here as paid). status is one of:
//   paid      verified, the buyer is enrolled
//   pending   ZarinPal gave no clear answer yet; the server keeps checking
//   canceled  paid for something already bought, so not verified: ZarinPal refunds it
//   failed    not paid
const route = useRoute()
const status = computed(() => String(route.query.status ?? 'failed'))
const paid = computed(() => status.value === 'paid')
const failedText = computed(() => ({
  pending: {
    title: 'پرداخت در حال بررسی است',
    body: 'پاسخ درگاه هنوز به دست ما نرسیده. اگر مبلغ از حساب شما کم شده، کاری لازم نیست: پرداخت خودکار بررسی می‌شود و تا چند دقیقه‌ی دیگر دوره به «دوره‌های من» اضافه می‌شود.',
  },
  canceled: {
    title: 'این پرداخت تکراری بود',
    body: 'شما این دوره را پیش‌تر خریده بودید، پس این پرداخت ثبت نشد و درگاه مبلغ آن را خودکار به حسابتان برمی‌گرداند (معمولاً تا ۷۲ ساعت).',
  },
}[status.value] ?? {
  title: 'پرداخت انجام نشد',
  body: 'اگر مبلغی از حساب شما کم شده، نگران نباشید: بانک آن را تا ۷۲ ساعت برمی‌گرداند.',
}))
const orderId = computed(() => String(route.query.order_id ?? ''))

const { siteName } = useSite()
useSeoMeta({ title: () => `نتیجه‌ی پرداخت | ${siteName.value}`, robots: 'noindex' })
</script>

<template>
  <div class="mx-auto max-w-md px-4 py-16 sm:px-6">
    <div class="glass rounded-2xl px-6 py-10 text-center">
      <template v-if="paid">
        <div class="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-emerald-500/15">
          <svg class="h-7 w-7 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" /></svg>
        </div>
        <h1 class="mt-4 text-xl font-bold text-gray-900 dark:text-white">ثبت‌نام شما انجام شد</h1>
        <p class="mt-2 text-sm text-gray-600 dark:text-gray-300">
          دوره به بخش «دوره‌های من» اضافه شد و از همین حالا می‌توانید یادگیری را شروع کنید.
        </p>
        <NuxtLink
          to="/dashboard/my-courses"
          class="mt-6 inline-block rounded-xl bg-primary-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-primary-500"
        >
          رفتن به دوره‌های من
        </NuxtLink>
      </template>
      <template v-else>
        <div :class="['mx-auto flex h-14 w-14 items-center justify-center rounded-full', status === 'pending' ? 'bg-amber-500/15' : 'bg-red-500/15']">
          <svg v-if="status === 'pending'" class="h-7 w-7 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
          <svg v-else class="h-7 w-7 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
        </div>
        <h1 class="mt-4 text-xl font-bold text-gray-900 dark:text-white">{{ failedText.title }}</h1>
        <p class="mt-2 text-sm text-gray-600 dark:text-gray-300">{{ failedText.body }}</p>
        <p v-if="orderId" class="mt-3 text-xs text-gray-500">شماره‌ی سفارش: {{ toPersianDigits(orderId) }}</p>
        <div class="mt-6 flex justify-center gap-3">
          <NuxtLink
            to="/dashboard/orders"
            class="rounded-xl bg-primary-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-primary-500"
          >
            سفارش‌های من
          </NuxtLink>
          <NuxtLink
            to="/courses"
            class="glass rounded-xl px-5 py-2.5 text-sm font-semibold text-gray-800 dark:text-gray-100"
          >
            بازگشت به دوره‌ها
          </NuxtLink>
        </div>
      </template>
    </div>
  </div>
</template>
