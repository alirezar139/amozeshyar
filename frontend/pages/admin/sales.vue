<script setup lang="ts">
// The instructor's sales: revenue for a period, then every order with its buyer and payments.
definePageMeta({ layout: 'admin' })
const { request } = useApi()

const PERIODS = [
  { days: 7, label: '۷ روز' },
  { days: 30, label: '۳۰ روز' },
  { days: 90, label: '۳ ماه' },
  { days: 365, label: 'یک سال' },
]
const days = ref(30)
const summaryAsync = useAsyncData('admin-sales-summary', () => request<any>(`/payments/admin/summary/?days=${days.value}`), { watch: [days] })
const { data: summary, pending: summaryPending, error: summaryError } = summaryAsync

const status = ref('')
const search = ref('')
const searchInput = ref('')
const page = ref(1)
let searchTimer: ReturnType<typeof setTimeout> | undefined
watch(searchInput, (value) => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    search.value = value.trim()
    page.value = 1
  }, 350)
})
watch(status, () => (page.value = 1))

const ordersAsync = useAsyncData(
  'admin-sales-orders',
  () => {
    const qs = new URLSearchParams({ page: String(page.value) })
    if (status.value) qs.set('status', status.value)
    if (search.value) qs.set('search', search.value)
    return request<{ count: number; next: string | null; previous: string | null; results: any[] }>(`/payments/admin/orders/?${qs}`)
  },
  { watch: [status, search, page] },
)
const { data: orders, pending: ordersPending, error: ordersError, refresh: refreshOrders } = ordersAsync
await Promise.all([summaryAsync, ordersAsync])

const selected = ref<any>(null)
async function onChanged() {
  await Promise.all([refreshOrders(), summaryAsync.refresh()])
  selected.value = orders.value?.results.find((o) => o.id === selected.value?.id) ?? selected.value
}

const maxDaily = computed(() => Math.max(1, ...(summary.value?.daily ?? []).map((d: any) => d.amount)))

const { formatGregorianDate } = useJalali()
function dayLabel(d: { date: string; amount: number; orders: number }) {
  return `${formatGregorianDate(new Date(d.date))}: ${formatToman(d.amount)} (${d.orders.toLocaleString('fa-IR')} سفارش)`
}

function buyerName(o: any) {
  return `${o.buyer.first_name ?? ''} ${o.buyer.last_name ?? ''}`.trim() || o.buyer.email
}
</script>

<template>
  <div>
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-xl font-bold text-gray-900 dark:text-white">فروش و سفارش‌ها</h1>
        <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">درآمد، سفارش‌ها و تراکنش‌های درگاه سایت شما.</p>
      </div>
      <div class="glass flex rounded-xl p-1 text-sm" role="tablist" aria-label="بازه‌ی گزارش">
        <button
          v-for="p in PERIODS"
          :key="p.days"
          type="button"
          role="tab"
          :aria-selected="days === p.days"
          :class="['rounded-lg px-3 py-1.5 transition', days === p.days ? 'bg-primary-600 font-semibold text-white' : 'text-gray-700 hover:bg-black/5 dark:text-gray-200 dark:hover:bg-white/10']"
          @click="days = p.days"
        >
          {{ p.label }}
        </button>
      </div>
    </div>

    <!-- summary -->
    <p v-if="summaryError" class="glass mt-6 rounded-2xl px-5 py-4 text-sm text-red-600">گزارش فروش بارگذاری نشد. صفحه را دوباره باز کنید.</p>
    <div v-else-if="summaryPending && !summary" class="mt-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
      <div v-for="i in 4" :key="i" class="glass h-24 animate-pulse rounded-2xl" />
    </div>
    <template v-else-if="summary">
      <div class="mt-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <div class="glass rounded-2xl p-4">
          <p class="text-xs text-gray-500">فروش ناخالص</p>
          <p class="mt-1 text-lg font-bold text-gray-900 dark:text-white">{{ formatToman(summary.gross) }}</p>
        </div>
        <div class="glass rounded-2xl p-4">
          <p class="text-xs text-gray-500">مسترد شده</p>
          <p class="mt-1 text-lg font-bold text-gray-900 dark:text-white">{{ formatToman(summary.refunded) }}</p>
        </div>
        <div class="glass rounded-2xl p-4">
          <p class="text-xs text-gray-500">درآمد خالص</p>
          <p class="mt-1 text-lg font-bold text-emerald-700 dark:text-emerald-300">{{ formatToman(summary.net) }}</p>
        </div>
        <div class="glass rounded-2xl p-4">
          <p class="text-xs text-gray-500">سفارش پرداخت‌شده</p>
          <p class="mt-1 text-lg font-bold text-gray-900 dark:text-white">
            {{ summary.paid_orders.toLocaleString('fa-IR') }}
            <span class="text-xs font-normal text-gray-500">({{ summary.buyers.toLocaleString('fa-IR') }} خریدار)</span>
          </p>
        </div>
      </div>

      <div class="mt-3 flex flex-wrap gap-2 text-xs">
        <span class="glass rounded-full px-3 py-1 text-gray-700 dark:text-gray-200">در انتظار پرداخت: {{ summary.pending_orders.toLocaleString('fa-IR') }}</span>
        <span class="glass rounded-full px-3 py-1 text-gray-700 dark:text-gray-200">پرداخت ناموفق: {{ summary.failed_payments.toLocaleString('fa-IR') }}</span>
        <span class="glass rounded-full px-3 py-1 text-gray-700 dark:text-gray-200" title="پرداخت دوباره برای دوره‌ای که خریدار از قبل داشت؛ زرین‌پال خودکار برمی‌گرداند">
          پرداخت تکراری (برگشت خودکار): {{ summary.canceled_payments.toLocaleString('fa-IR') }}
        </span>
        <span v-if="summary.unsettled_payments" class="glass rounded-full px-3 py-1 text-amber-700 dark:text-amber-300">در حال بررسی با درگاه: {{ summary.unsettled_payments.toLocaleString('fa-IR') }}</span>
        <NuxtLink v-if="summary.open_refunds" to="/admin/refunds" class="rounded-full bg-amber-500/15 px-3 py-1 font-semibold text-amber-700 hover:underline dark:text-amber-300">
          {{ summary.open_refunds.toLocaleString('fa-IR') }} درخواست استرداد در انتظار شما
        </NuxtLink>
      </div>

      <div class="mt-4 grid gap-3 lg:grid-cols-3">
        <div class="glass rounded-2xl p-4 lg:col-span-2">
          <p class="text-sm font-semibold text-gray-800 dark:text-gray-100">فروش روزانه</p>
          <p v-if="!summary.daily.length" class="py-8 text-center text-sm text-gray-500">در این بازه فروشی ثبت نشده است.</p>
          <div v-else class="mt-4 flex h-32 items-end gap-1" dir="ltr">
            <div
              v-for="d in summary.daily"
              :key="d.date"
              class="min-w-[4px] flex-1 rounded-t bg-primary-500/70 transition hover:bg-primary-600"
              :style="{ height: `${Math.max(4, (d.amount / maxDaily) * 100)}%` }"
              :title="dayLabel(d)"
            />
          </div>
        </div>
        <div class="glass rounded-2xl p-4">
          <p class="text-sm font-semibold text-gray-800 dark:text-gray-100">پرفروش‌ترین دوره‌ها</p>
          <p v-if="!summary.top_courses.length" class="py-8 text-center text-sm text-gray-500">هنوز فروشی نیست.</p>
          <ol v-else class="mt-3 space-y-2 text-sm">
            <li v-for="c in summary.top_courses" :key="c.course_id" class="flex justify-between gap-3">
              <span class="truncate text-gray-800 dark:text-gray-100">{{ c.title }}</span>
              <span class="shrink-0 text-gray-500">{{ c.sales.toLocaleString('fa-IR') }} فروش</span>
            </li>
          </ol>
        </div>
      </div>
    </template>

    <!-- orders -->
    <div class="mt-8 flex flex-wrap items-center justify-between gap-3">
      <h2 class="text-lg font-bold text-gray-900 dark:text-white">سفارش‌ها</h2>
      <div class="flex flex-wrap gap-2">
        <select v-model="status" class="glass rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white" aria-label="وضعیت سفارش">
          <option value="">همه‌ی وضعیت‌ها</option>
          <option v-for="(s, key) in ORDER_STATUS" :key="key" :value="key">{{ s.label }}</option>
        </select>
        <input
          v-model="searchInput"
          type="search"
          placeholder="ایمیل، نام، موبایل یا شماره‌ی سفارش…"
          class="glass w-64 max-w-full rounded-md px-3 py-2 text-sm text-gray-900 placeholder:text-gray-500 dark:text-white"
        >
      </div>
    </div>

    <p v-if="ordersError" class="glass mt-4 rounded-2xl px-5 py-4 text-sm text-red-600">سفارش‌ها بارگذاری نشد.</p>
    <div v-else-if="ordersPending && !orders" class="mt-4 space-y-2">
      <div v-for="i in 3" :key="i" class="glass h-16 animate-pulse rounded-2xl" />
    </div>
    <div v-else-if="!orders?.results.length" class="glass mt-4 rounded-2xl px-6 py-10 text-center text-sm text-gray-600 dark:text-gray-300">
      {{ status || search ? 'سفارشی با این شرایط پیدا نشد.' : 'هنوز سفارشی ثبت نشده است.' }}
    </div>
    <ul v-else :class="['mt-4 space-y-2 transition', ordersPending ? 'opacity-60' : '']">
      <li v-for="o in orders.results" :key="o.id">
        <button
          type="button"
          class="glass grid w-full grid-cols-2 items-center gap-x-3 gap-y-1 rounded-2xl px-4 py-3 text-start text-sm transition hover:shadow-md sm:grid-cols-[5rem_1fr_1fr_auto_auto]"
          @click="selected = o"
        >
          <span class="text-xs text-gray-500">#{{ toPersianDigits(o.id) }}</span>
          <span class="truncate font-semibold text-gray-900 dark:text-white">{{ buyerName(o) }}</span>
          <span class="col-span-2 truncate text-gray-600 sm:col-span-1 dark:text-gray-300">{{ o.items.map((i: any) => i.course_title).join('، ') }}</span>
          <span class="font-bold text-gray-900 dark:text-white">{{ formatToman(o.total_amount) }}</span>
          <span class="flex flex-col items-end gap-1">
            <SalesStatusBadge :map="ORDER_STATUS" :status="o.status" />
            <span class="text-[11px] text-gray-500">{{ formatDateTime(o.created_at) }}</span>
          </span>
        </button>
      </li>
    </ul>
    <div v-if="orders && (orders.next || orders.previous)" class="mt-4 flex items-center justify-center gap-3 text-sm">
      <button type="button" :disabled="!orders.previous" class="glass rounded-lg px-3 py-1.5 disabled:opacity-40" @click="page--">قبلی</button>
      <span class="text-gray-600 dark:text-gray-300">صفحه‌ی {{ toPersianDigits(page) }}</span>
      <button type="button" :disabled="!orders.next" class="glass rounded-lg px-3 py-1.5 disabled:opacity-40" @click="page++">بعدی</button>
    </div>

    <SalesOrderDetail v-if="selected" :order="selected" @close="selected = null" @changed="onChanged" />
  </div>
</template>
