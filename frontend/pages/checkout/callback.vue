<script setup lang="ts">
// Where a buyer lands after checkout: the API's payment callback redirects
// here with ?order_id=&status=paid|failed once it has verified with
// ZarinPal (free orders come straight here as paid).
const route = useRoute()
const paid = computed(() => route.query.status === 'paid')
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
        <div class="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-red-500/15">
          <svg class="h-7 w-7 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
        </div>
        <h1 class="mt-4 text-xl font-bold text-gray-900 dark:text-white">پرداخت انجام نشد</h1>
        <p class="mt-2 text-sm text-gray-600 dark:text-gray-300">
          اگر مبلغی از حساب شما کم شده، نگران نباشید: پرداخت تا چند دقیقه‌ی دیگر خودکار بررسی می‌شود و
          ثبت‌نام انجام می‌شود، وگرنه بانک مبلغ را تا ۷۲ ساعت برمی‌گرداند.
        </p>
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
