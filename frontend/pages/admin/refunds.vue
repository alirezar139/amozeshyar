<script setup lang="ts">
// Students' refund requests. "Refunded" is recorded after the money was actually returned in the
// ZarinPal panel (or by bank transfer); it closes the order's course access and tells the student.
definePageMeta({ layout: 'admin' })
const { request } = useApi()

const status = ref('pending')
const { data: refunds, pending, error, refresh } = await useAsyncData(
  'admin-refunds',
  async () => {
    const qs = status.value ? `?status=${status.value}` : ''
    return (await request<{ results: any[] }>(`/payments/admin/refunds/${qs}`)).results
  },
  { watch: [status] },
)

const deciding = ref<{ refund: any; action: 'complete' | 'reject' } | null>(null)
const reference = ref('')
const note = ref('')
const saving = ref(false)
const formError = ref('')
const notice = ref('')

function open(refund: any, action: 'complete' | 'reject') {
  deciding.value = { refund, action }
  reference.value = ''
  note.value = ''
  formError.value = ''
}

async function decide() {
  if (!deciding.value) return
  const { refund, action } = deciding.value
  saving.value = true
  formError.value = ''
  try {
    await request(`/payments/admin/refunds/${refund.id}/${action}/`, {
      method: 'POST',
      body: { reference: reference.value.trim(), note: note.value.trim() },
    })
    notice.value = action === 'complete'
      ? `استرداد سفارش ${toPersianDigits(refund.order)} ثبت شد و به دانشجو اطلاع داده شد.`
      : `درخواست سفارش ${toPersianDigits(refund.order)} رد شد و به دانشجو اطلاع داده شد.`
    deciding.value = null
    await refresh()
  } catch (err) {
    formError.value = getFirstErrorMessage(err, 'ثبت انجام نشد.')
  } finally {
    saving.value = false
  }
}

function buyerName(r: any) {
  return `${r.buyer.first_name ?? ''} ${r.buyer.last_name ?? ''}`.trim() || r.buyer.email
}
</script>

<template>
  <div>
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-xl font-bold text-gray-900 dark:text-white">درخواست‌های استرداد</h1>
        <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">اول مبلغ را از پنل زرین‌پال برگردانید، بعد اینجا «مسترد شد» را ثبت کنید.</p>
      </div>
      <select v-model="status" class="glass rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white" aria-label="وضعیت درخواست">
        <option value="">همه</option>
        <option v-for="(s, key) in REFUND_STATUS" :key="key" :value="key">{{ s.label }}</option>
      </select>
    </div>

    <p v-if="notice" class="glass mt-4 rounded-xl px-4 py-2 text-sm text-emerald-700 dark:text-emerald-300" role="status">{{ notice }}</p>

    <p v-if="error" class="glass mt-6 rounded-2xl px-5 py-4 text-sm text-red-600">درخواست‌ها بارگذاری نشد.</p>
    <div v-else-if="pending && !refunds" class="mt-6 space-y-2">
      <div v-for="i in 2" :key="i" class="glass h-24 animate-pulse rounded-2xl" />
    </div>
    <div v-else-if="!refunds?.length" class="glass mt-6 rounded-2xl px-6 py-12 text-center text-sm text-gray-600 dark:text-gray-300">
      {{ status === 'pending' ? 'درخواست بررسی‌نشده‌ای ندارید.' : 'درخواستی پیدا نشد.' }}
    </div>
    <ul v-else class="mt-6 space-y-3">
      <li v-for="r in refunds" :key="r.id" class="glass rounded-2xl px-5 py-4 text-sm">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div>
            <span class="font-semibold text-gray-900 dark:text-white">{{ buyerName(r) }}</span>
            <span class="ms-2 text-xs text-gray-500" dir="ltr">{{ r.buyer.email }}</span>
          </div>
          <SalesStatusBadge :map="REFUND_STATUS" :status="r.status" />
        </div>
        <p class="mt-1 text-gray-600 dark:text-gray-300">
          سفارش {{ toPersianDigits(r.order) }} · {{ r.courses.join('، ') }} · <span class="font-semibold">{{ formatToman(r.amount) }}</span>
        </p>
        <p v-if="r.reason" class="mt-2 rounded-xl bg-black/[0.03] px-3 py-2 text-gray-800 dark:bg-white/5 dark:text-gray-100">{{ r.reason }}</p>
        <p class="mt-2 text-xs text-gray-500">
          درخواست: {{ formatDateTime(r.created_at) }}
          <template v-if="r.decided_at"> · بررسی: {{ formatDateTime(r.decided_at) }}</template>
          <template v-if="r.reference"> · شناسه: <span dir="ltr">{{ r.reference }}</span></template>
        </p>
        <p v-if="r.admin_note" class="mt-1 text-xs text-gray-500">یادداشت: {{ r.admin_note }}</p>
        <div v-if="r.status === 'pending'" class="mt-3 flex flex-wrap gap-2">
          <button type="button" class="rounded-xl bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-500" @click="open(r, 'complete')">مبلغ را برگرداندم</button>
          <button type="button" class="rounded-xl px-4 py-2 text-sm font-semibold text-red-600 hover:bg-red-500/10" @click="open(r, 'reject')">رد درخواست</button>
        </div>
      </li>
    </ul>

    <ChatModal v-if="deciding" :title="deciding.action === 'complete' ? 'ثبت استرداد' : 'رد درخواست'" @close="deciding = null">
      <form class="space-y-3 px-5 py-4 text-sm" @submit.prevent="decide">
        <p v-if="deciding.action === 'complete'" class="leading-6 text-gray-600 dark:text-gray-300">
          با ثبت، سفارش «مسترد شده» می‌شود و دسترسی دانشجو به دوره‌های آن بسته می‌شود.
        </p>
        <input v-if="deciding.action === 'complete'" v-model="reference" placeholder="شناسه‌ی استرداد در زرین‌پال / بانک" class="glass w-full rounded-md px-3 py-2" dir="auto">
        <textarea v-model="note" rows="3" :placeholder="deciding.action === 'reject' ? 'دلیل رد (برای دانشجو فرستاده می‌شود)' : 'یادداشت (اختیاری)'" class="glass w-full rounded-md px-3 py-2" />
        <p v-if="formError" class="text-red-600" role="alert">{{ formError }}</p>
        <button
          type="submit"
          :disabled="saving"
          :class="['w-full rounded-xl px-4 py-2.5 font-semibold text-white disabled:opacity-60', deciding.action === 'complete' ? 'bg-primary-600 hover:bg-primary-500' : 'bg-red-600 hover:bg-red-500']"
        >
          {{ saving ? 'در حال ثبت…' : deciding.action === 'complete' ? 'ثبت استرداد' : 'رد درخواست' }}
        </button>
      </form>
    </ChatModal>
  </div>
</template>
