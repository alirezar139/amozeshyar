<script setup lang="ts">
// Discount codes: create, edit, see how many times each was used (paid) or is held by an
// order still at the gateway. A used code can't be deleted, only ended.
definePageMeta({ layout: 'admin' })
const { request } = useApi()

const { data: coupons, pending, error, refresh } = await useAsyncData('admin-coupons', async () => {
  const page = await request<{ results: any[] }>('/payments/admin/coupons/?page_size=100')
  return page.results
})

function toLocalInput(iso: string | null) {
  if (!iso) return ''
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function blank() {
  const now = new Date()
  const month = new Date(now.getTime() + 30 * 864e5)
  return {
    id: null as number | null, code: '', kind: 'percent', value: '',
    valid_from: toLocalInput(now.toISOString()), valid_to: toLocalInput(month.toISOString()),
    max_uses: '', max_uses_per_user: '',
  }
}

const form = ref<ReturnType<typeof blank> | null>(null)
const saving = ref(false)
const formError = ref('')
const notice = ref('')

function openNew() {
  form.value = blank()
  formError.value = ''
}

function openEdit(c: any) {
  form.value = {
    id: c.id, code: c.code,
    kind: c.discount_percent ? 'percent' : 'amount',
    value: String(c.discount_percent ?? Number(c.discount_amount ?? 0)),
    valid_from: toLocalInput(c.valid_from), valid_to: toLocalInput(c.valid_to),
    max_uses: c.max_uses == null ? '' : String(c.max_uses),
    max_uses_per_user: c.max_uses_per_user == null ? '' : String(c.max_uses_per_user),
  }
  formError.value = ''
}

async function save() {
  if (!form.value) return
  const f = form.value
  saving.value = true
  formError.value = ''
  const body = {
    code: f.code.trim(),
    discount_percent: f.kind === 'percent' ? Number(f.value) || null : null,
    discount_amount: f.kind === 'amount' ? Number(f.value) || null : null,
    valid_from: new Date(f.valid_from).toISOString(),
    valid_to: new Date(f.valid_to).toISOString(),
    max_uses: f.max_uses === '' ? null : Number(f.max_uses),
    max_uses_per_user: f.max_uses_per_user === '' ? null : Number(f.max_uses_per_user),
  }
  try {
    await request(f.id ? `/payments/admin/coupons/${f.id}/` : '/payments/admin/coupons/', { method: f.id ? 'PATCH' : 'POST', body })
    notice.value = f.id ? 'کد تخفیف به‌روز شد.' : `کد ${body.code.toUpperCase()} ساخته شد.`
    form.value = null
    await refresh()
  } catch (err) {
    formError.value = getFirstErrorMessage(err, 'ذخیره انجام نشد.')
  } finally {
    saving.value = false
  }
}

async function remove(c: any) {
  if (!confirm(`کد ${c.code} حذف شود؟`)) return
  notice.value = ''
  try {
    await request(`/payments/admin/coupons/${c.id}/`, { method: 'DELETE' })
    notice.value = `کد ${c.code} حذف شد.`
    await refresh()
  } catch (err) {
    notice.value = getFirstErrorMessage(err, 'حذف انجام نشد.')
  }
}

function discountLabel(c: any) {
  return c.discount_percent ? `${Number(c.discount_percent).toLocaleString('fa-IR')}٪` : formatToman(c.discount_amount)
}

function state(c: any) {
  const now = Date.now()
  if (new Date(c.valid_to).getTime() < now) return { label: 'منقضی', tone: 'bg-gray-500/15 text-gray-700 dark:text-gray-300' }
  if (new Date(c.valid_from).getTime() > now) return { label: 'هنوز شروع نشده', tone: 'bg-sky-500/15 text-sky-700 dark:text-sky-300' }
  if (c.max_uses != null && c.used_count >= c.max_uses) return { label: 'ظرفیت تمام شده', tone: 'bg-red-500/15 text-red-700 dark:text-red-300' }
  return { label: 'فعال', tone: 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300' }
}
</script>

<template>
  <div>
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-xl font-bold text-gray-900 dark:text-white">کدهای تخفیف</h1>
        <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">دانشجو کد را هنگام خرید وارد می‌کند. سقف استفاده هم کلی است هم برای هر نفر.</p>
      </div>
      <button type="button" class="rounded-xl bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-500" @click="openNew">
        + کد تازه
      </button>
    </div>

    <p v-if="notice" class="glass mt-4 rounded-xl px-4 py-2 text-sm text-gray-800 dark:text-gray-100" role="status">{{ notice }}</p>

    <p v-if="error" class="glass mt-6 rounded-2xl px-5 py-4 text-sm text-red-600">کدهای تخفیف بارگذاری نشد.</p>
    <div v-else-if="pending && !coupons" class="mt-6 space-y-2">
      <div v-for="i in 3" :key="i" class="glass h-16 animate-pulse rounded-2xl" />
    </div>
    <div v-else-if="!coupons?.length" class="glass mt-6 rounded-2xl px-6 py-12 text-center">
      <p class="font-semibold text-gray-800 dark:text-gray-100">هنوز کد تخفیفی نساخته‌اید</p>
      <p class="mt-1 text-sm text-gray-500">مثلاً یک کد ۲۰ درصدی برای هفته‌ی اول ثبت‌نام بسازید.</p>
    </div>
    <ul v-else class="mt-6 space-y-2">
      <li v-for="c in coupons" :key="c.id" class="glass flex flex-wrap items-center gap-x-4 gap-y-2 rounded-2xl px-4 py-3 text-sm">
        <span class="font-mono text-base font-bold text-gray-900 dark:text-white" dir="ltr">{{ c.code }}</span>
        <span class="font-semibold text-primary-700 dark:text-primary-300">{{ discountLabel(c) }}</span>
        <span class="rounded-full px-2.5 py-0.5 text-xs font-semibold" :class="state(c).tone">{{ state(c).label }}</span>
        <span class="text-gray-600 dark:text-gray-300">
          استفاده: {{ c.used_count.toLocaleString('fa-IR') }}{{ c.max_uses != null ? ` از ${c.max_uses.toLocaleString('fa-IR')}` : '' }}
          <template v-if="c.held_orders"> · {{ c.held_orders.toLocaleString('fa-IR') }} در حال پرداخت</template>
          <template v-if="c.max_uses_per_user != null"> · هر نفر {{ c.max_uses_per_user.toLocaleString('fa-IR') }} بار</template>
        </span>
        <span class="text-xs text-gray-500">تا {{ formatDateTime(c.valid_to) }}</span>
        <span class="ms-auto flex gap-2">
          <button type="button" class="rounded-lg px-2.5 py-1 text-primary-700 hover:bg-primary-500/10 dark:text-primary-300" @click="openEdit(c)">ویرایش</button>
          <button v-if="!c.used_count && !c.paid_orders" type="button" class="rounded-lg px-2.5 py-1 text-red-600 hover:bg-red-500/10" @click="remove(c)">حذف</button>
        </span>
      </li>
    </ul>

    <ChatModal v-if="form" :title="form.id ? 'ویرایش کد تخفیف' : 'کد تخفیف تازه'" @close="form = null">
      <form class="space-y-4 px-5 py-4 text-sm" @submit.prevent="save">
        <label class="block">
          <span class="mb-1 block text-gray-700 dark:text-gray-200">کد</span>
          <input v-model="form.code" required maxlength="50" dir="ltr" placeholder="NOROOZ" class="glass w-full rounded-md px-3 py-2 font-mono uppercase">
        </label>
        <div class="grid grid-cols-2 gap-3">
          <label class="block">
            <span class="mb-1 block text-gray-700 dark:text-gray-200">نوع تخفیف</span>
            <select v-model="form.kind" class="glass w-full rounded-md px-3 py-2">
              <option value="percent">درصد</option>
              <option value="amount">مبلغ (تومان)</option>
            </select>
          </label>
          <label class="block">
            <span class="mb-1 block text-gray-700 dark:text-gray-200">{{ form.kind === 'percent' ? 'درصد' : 'مبلغ' }}</span>
            <input v-model="form.value" required type="number" min="1" :max="form.kind === 'percent' ? 100 : undefined" class="glass w-full rounded-md px-3 py-2" dir="ltr">
          </label>
        </div>
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <label class="block">
            <span class="mb-1 block text-gray-700 dark:text-gray-200">شروع اعتبار</span>
            <input v-model="form.valid_from" required type="datetime-local" class="glass w-full rounded-md px-3 py-2" dir="ltr">
          </label>
          <label class="block">
            <span class="mb-1 block text-gray-700 dark:text-gray-200">پایان اعتبار</span>
            <input v-model="form.valid_to" required type="datetime-local" class="glass w-full rounded-md px-3 py-2" dir="ltr">
          </label>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <label class="block">
            <span class="mb-1 block text-gray-700 dark:text-gray-200">سقف کل استفاده</span>
            <input v-model="form.max_uses" type="number" min="0" placeholder="بی‌سقف" class="glass w-full rounded-md px-3 py-2" dir="ltr">
          </label>
          <label class="block">
            <span class="mb-1 block text-gray-700 dark:text-gray-200">سقف برای هر نفر</span>
            <input v-model="form.max_uses_per_user" type="number" min="0" placeholder="بی‌سقف" class="glass w-full rounded-md px-3 py-2" dir="ltr">
          </label>
        </div>
        <p v-if="formError" class="text-sm text-red-600" role="alert">{{ formError }}</p>
        <button type="submit" :disabled="saving" class="w-full rounded-xl bg-primary-600 px-4 py-2.5 font-semibold text-white hover:bg-primary-500 disabled:opacity-60">
          {{ saving ? 'در حال ذخیره…' : 'ذخیره' }}
        </button>
      </form>
    </ChatModal>
  </div>
</template>
