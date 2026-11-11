<script setup lang="ts">
// One order in full for the instructor: buyer, courses, every gateway attempt and refund,
// plus recording a refund the instructor made without a request.
const props = defineProps<{ order: any }>()
const emit = defineEmits<{ close: []; changed: [] }>()
const { request } = useApi()

const refunding = ref(false)
const reference = ref('')
const note = ref('')
const saving = ref(false)
const error = ref('')
const done = ref(false)

async function recordRefund() {
  saving.value = true
  error.value = ''
  try {
    await request(`/payments/admin/orders/${props.order.id}/refund/`, {
      method: 'POST',
      body: { reference: reference.value.trim(), note: note.value.trim() },
    })
    done.value = true
    emit('changed')
  } catch (err) {
    error.value = getFirstErrorMessage(err, 'ثبت استرداد انجام نشد.')
  } finally {
    saving.value = false
  }
}

const buyerName = computed(() => {
  const b = props.order.buyer
  return `${b.first_name ?? ''} ${b.last_name ?? ''}`.trim() || b.email
})
</script>

<template>
  <ChatModal :title="`سفارش ${toPersianDigits(order.id)}`" wide @close="emit('close')">
    <div class="space-y-5 px-5 py-4 text-sm">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <SalesStatusBadge :map="ORDER_STATUS" :status="order.status" />
        <span class="text-base font-bold text-gray-900 dark:text-white">{{ formatToman(order.total_amount) }}</span>
      </div>

      <section>
        <h4 class="mb-1.5 text-xs font-semibold text-gray-500">خریدار</h4>
        <p class="font-semibold text-gray-900 dark:text-white">{{ buyerName }}</p>
        <p class="text-gray-600 dark:text-gray-300" dir="ltr">{{ order.buyer.email }}</p>
        <p v-if="order.buyer.phone_number" class="text-gray-600 dark:text-gray-300" dir="ltr">{{ order.buyer.phone_number }}</p>
      </section>

      <section>
        <h4 class="mb-1.5 text-xs font-semibold text-gray-500">دوره‌ها</h4>
        <ul class="space-y-1">
          <li v-for="item in order.items" :key="item.course_slug" class="flex justify-between gap-3">
            <span class="text-gray-900 dark:text-white">{{ item.course_title }}</span>
            <span class="shrink-0 text-gray-500">{{ formatToman(item.price_at_purchase) }}</span>
          </li>
        </ul>
        <p v-if="order.coupon_code" class="mt-1.5 text-xs text-gray-500">کد تخفیف: <span dir="ltr">{{ order.coupon_code }}</span></p>
        <p class="mt-1.5 text-xs text-gray-500">
          ثبت: {{ formatDateTime(order.created_at) }}
          <template v-if="order.paid_at"> · پرداخت: {{ formatDateTime(order.paid_at) }}</template>
        </p>
      </section>

      <section>
        <h4 class="mb-1.5 text-xs font-semibold text-gray-500">تراکنش‌های درگاه</h4>
        <p v-if="!order.payments.length" class="text-gray-500">این سفارش هنوز به درگاه نرفته است.</p>
        <ul v-else class="space-y-2">
          <li v-for="p in order.payments" :key="p.id" class="rounded-xl bg-black/[0.03] px-3 py-2 dark:bg-white/5">
            <div class="flex flex-wrap items-center justify-between gap-2">
              <SalesStatusBadge :map="PAYMENT_STATUS" :status="p.status" />
              <span class="text-xs text-gray-500">{{ formatDateTime(p.created_at) }}</span>
            </div>
            <p v-if="p.ref_id" class="mt-1 text-xs text-gray-600 dark:text-gray-300">کد پیگیری: <span dir="ltr">{{ p.ref_id }}</span></p>
            <p class="mt-0.5 truncate text-[11px] text-gray-400" dir="ltr">{{ p.authority }}</p>
            <p v-if="p.note" class="mt-1 text-xs text-gray-500">{{ p.note }}</p>
          </li>
        </ul>
      </section>

      <section v-if="order.refunds.length">
        <h4 class="mb-1.5 text-xs font-semibold text-gray-500">استرداد</h4>
        <ul class="space-y-2">
          <li v-for="r in order.refunds" :key="r.id" class="rounded-xl bg-black/[0.03] px-3 py-2 dark:bg-white/5">
            <div class="flex items-center justify-between gap-2">
              <SalesStatusBadge :map="REFUND_STATUS" :status="r.status" />
              <span class="text-xs text-gray-500">{{ formatDateTime(r.created_at) }}</span>
            </div>
            <p v-if="r.reason" class="mt-1 text-xs text-gray-600 dark:text-gray-300">دلیل دانشجو: {{ r.reason }}</p>
            <p v-if="r.admin_note" class="mt-1 text-xs text-gray-500">یادداشت شما: {{ r.admin_note }}</p>
          </li>
        </ul>
      </section>

      <section v-if="order.status === 'paid' && Number(order.total_amount) > 0">
        <p v-if="done" class="rounded-xl bg-emerald-500/10 px-3 py-2 text-emerald-700 dark:text-emerald-300">
          استرداد ثبت شد؛ دسترسی دانشجو به دوره‌های این سفارش بسته شد و به او اطلاع داده شد.
        </p>
        <button
          v-else-if="!refunding"
          type="button"
          class="text-sm font-semibold text-red-600 hover:underline"
          @click="refunding = true"
        >
          ثبت استرداد وجه این سفارش…
        </button>
        <form v-else class="space-y-3 rounded-xl border border-red-500/20 p-3" @submit.prevent="recordRefund">
          <p class="text-xs leading-6 text-gray-600 dark:text-gray-300">
            اول مبلغ را از پنل زرین‌پال (یا کارت‌به‌کارت) به دانشجو برگردانید، بعد اینجا ثبتش کنید.
            با ثبت، دسترسی او به دوره‌های این سفارش بسته می‌شود.
          </p>
          <input v-model="reference" placeholder="شناسه‌ی استرداد در زرین‌پال / بانک (اختیاری)" class="glass w-full rounded-md px-3 py-2 text-sm" dir="auto">
          <input v-model="note" placeholder="یادداشت (اختیاری)" class="glass w-full rounded-md px-3 py-2 text-sm">
          <p v-if="error" class="text-xs text-red-600">{{ error }}</p>
          <div class="flex gap-2">
            <button type="submit" :disabled="saving" class="rounded-xl bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-500 disabled:opacity-60">
              {{ saving ? 'در حال ثبت…' : 'ثبت استرداد' }}
            </button>
            <button type="button" class="rounded-xl px-4 py-2 text-sm text-gray-600 hover:bg-black/5 dark:text-gray-300" @click="refunding = false">انصراف</button>
          </div>
        </form>
      </section>
    </div>
  </ChatModal>
</template>
