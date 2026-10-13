<script setup lang="ts">
// Developer-only: live feed of API errors, server crashes and browser errors from every user,
// plus the instructor's support reports. The API refuses everyone else (403) as well.
definePageMeta({ layout: 'admin' })
const authStore = useAuthStore()
if (!authStore.isDeveloper) await navigateTo('/admin', { replace: true })

const { request } = useApi()

interface ErrorEvent {
  id: number
  created_at: string
  source: 'api' | 'server' | 'browser'
  level: 'error' | 'warning'
  method: string
  path: string
  status: number | null
  user_label: string
  message: string
  detail: string
  page_url: string
}

const tab = ref<'events' | 'reports'>('events')
const events = ref<ErrorEvent[]>([])
const source = ref('')
const level = ref('')
const paused = ref(false)
const expanded = ref<number | null>(null)
const error = ref('')
const MAX_SHOWN = 500

const SOURCE: Record<string, string> = { api: 'API', server: 'سرور', browser: 'مرورگر' }

function query(after?: number) {
  const params = new URLSearchParams()
  if (after) params.set('after', String(after))
  if (source.value) params.set('source', source.value)
  if (level.value) params.set('level', level.value)
  return `/monitoring/events/?${params}`
}

async function loadEvents() {
  try {
    events.value = await request<ErrorEvent[]>(query())
    error.value = ''
  } catch (err) {
    error.value = getErrorMessage(err, 'لاگ بارگذاری نشد.')
  }
}

async function poll() {
  if (paused.value || tab.value !== 'events') return
  try {
    const fresh = await request<ErrorEvent[]>(query(events.value[0]?.id))
    if (fresh.length) events.value = [...fresh, ...events.value].slice(0, MAX_SHOWN)
    error.value = ''
  } catch (err) {
    error.value = getErrorMessage(err, 'اتصال به لاگ قطع شد؛ دوباره تلاش می‌شود.')
  }
}

async function clearEvents() {
  if (!confirm('همه‌ی رویدادها (جز آن‌هایی که به گزارش پشتیبانی ضمیمه‌اند) پاک شوند؟')) return
  await request('/monitoring/events/', { method: 'DELETE' })
  events.value = []
}

watch([source, level], loadEvents)

const reports = ref<any[]>([])
const showResolved = ref(false)
const openReport = ref<number | null>(null)

async function loadReports() {
  try {
    const page = await request<{ results: any[] }>(`/monitoring/reports/?resolved=${showResolved.value}`)
    reports.value = page.results
  } catch (err) {
    error.value = getErrorMessage(err, 'گزارش‌ها بارگذاری نشد.')
  }
}

async function setResolved(report: any, resolved: boolean) {
  try {
    await request(`/monitoring/reports/${report.id}/`, { method: 'PATCH', body: { resolved } })
    reports.value = reports.value.filter((r) => r.id !== report.id)
  } catch (err) {
    error.value = getErrorMessage(err, 'ذخیره نشد.')
  }
}

watch(showResolved, loadReports)
watch(tab, (t) => (t === 'reports' ? loadReports() : loadEvents()))

let timer: ReturnType<typeof setInterval> | undefined
onMounted(() => {
  loadEvents()
  timer = setInterval(poll, 4000)
})
onBeforeUnmount(() => clearInterval(timer))

const time = (iso: string) => new Date(iso).toLocaleString('fa-IR')
</script>

<template>
  <div>
    <h1 class="text-xl font-bold text-gray-900 dark:text-white">لاگ زنده</h1>
    <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
      خطاهای API، کرش‌های سرور و خطاهای مرورگر همه‌ی کاربران، هر ۴ ثانیه به‌روز می‌شود. فقط حساب برنامه‌نویس این صفحه را می‌بیند.
    </p>

    <div class="mt-4 flex flex-wrap items-center gap-2">
      <button
        v-for="t in [{ key: 'events', label: 'رویدادها' }, { key: 'reports', label: 'گزارش‌های پشتیبانی' }]"
        :key="t.key"
        type="button"
        :class="['rounded-md px-4 py-1.5 text-sm', tab === t.key ? 'bg-primary-600 text-white' : 'glass text-gray-700 dark:text-gray-200']"
        @click="tab = t.key as any"
      >
        {{ t.label }}
      </button>
    </div>

    <p v-if="error" class="mt-3 text-sm text-red-600">{{ error }}</p>

    <section v-if="tab === 'events'" class="mt-4">
      <div class="flex flex-wrap items-center gap-2 text-sm">
        <select v-model="source" class="glass rounded-md px-3 py-1.5 text-gray-900 dark:text-white">
          <option value="">همه‌ی منابع</option>
          <option value="api">API</option>
          <option value="server">سرور (کرش)</option>
          <option value="browser">مرورگر</option>
        </select>
        <select v-model="level" class="glass rounded-md px-3 py-1.5 text-gray-900 dark:text-white">
          <option value="">همه‌ی سطح‌ها</option>
          <option value="error">خطا</option>
          <option value="warning">هشدار</option>
        </select>
        <button type="button" class="glass rounded-md px-3 py-1.5 text-gray-700 dark:text-gray-200" @click="paused = !paused">
          {{ paused ? '▶ ادامه' : '⏸ توقف' }}
        </button>
        <button type="button" class="rounded-md px-3 py-1.5 text-red-600 hover:bg-red-500/10" @click="clearEvents">پاک کردن</button>
        <span class="text-xs text-gray-500">{{ events.length }} رویداد</span>
      </div>

      <p v-if="!events.length" class="mt-6 text-center text-sm text-gray-500">خطایی ثبت نشده است. 🎉</p>
      <div class="mt-3 space-y-1 font-mono text-xs" dir="ltr">
        <button
          v-for="e in events"
          :key="e.id"
          type="button"
          class="glass block w-full rounded-lg px-3 py-2 text-start"
          @click="expanded = expanded === e.id ? null : e.id"
        >
          <span :class="['me-2 rounded px-1.5 py-0.5 font-sans text-[10px] font-bold', e.level === 'error' ? 'bg-red-600 text-white' : 'bg-amber-400 text-black']">
            {{ SOURCE[e.source] }}
          </span>
          <span class="text-gray-500">{{ time(e.created_at) }}</span>
          <span class="ms-2 text-gray-500">{{ e.user_label || 'anon' }}</span>
          <span class="mt-1 block break-words text-gray-900 dark:text-gray-100" dir="auto">{{ e.message }}</span>
          <span v-if="e.page_url" class="block text-gray-500">{{ e.page_url }}</span>
          <pre v-if="expanded === e.id && e.detail" class="mt-2 whitespace-pre-wrap break-words text-[11px] text-gray-600 dark:text-gray-400" dir="auto">{{ e.detail }}</pre>
        </button>
      </div>
    </section>

    <section v-else class="mt-4">
      <label class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-200">
        <input v-model="showResolved" type="checkbox">
        نمایش گزارش‌های بسته‌شده
      </label>
      <p v-if="!reports.length" class="mt-6 text-center text-sm text-gray-500">گزارشی نیست.</p>
      <div v-for="r in reports" :key="r.id" class="glass mt-3 rounded-2xl p-4">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div class="text-sm text-gray-600 dark:text-gray-400">
            #{{ r.id }} · {{ r.user_label }} · {{ time(r.created_at) }} · <span dir="ltr">{{ r.page_url }}</span>
          </div>
          <button
            type="button"
            class="rounded-md bg-emerald-600 px-3 py-1 text-xs font-semibold text-white hover:bg-emerald-500"
            @click="setResolved(r, !r.resolved)"
          >
            {{ r.resolved ? 'باز کردن دوباره' : 'حل شد' }}
          </button>
        </div>
        <p class="mt-2 whitespace-pre-wrap text-sm text-gray-900 dark:text-white">{{ r.message }}</p>
        <button type="button" class="mt-2 text-xs text-primary-600 hover:underline dark:text-primary-400" @click="openReport = openReport === r.id ? null : r.id">
          {{ openReport === r.id ? 'بستن جزئیات' : `جزئیات (${r.events.length} خطای سرور، ${r.browser_events.length} خطای مرورگر)` }}
        </button>
        <div v-if="openReport === r.id" class="mt-2 space-y-1 font-mono text-xs" dir="ltr">
          <p class="font-sans text-gray-500">{{ r.user_agent }}</p>
          <div v-for="e in r.events" :key="`s${e.id}`" class="rounded-lg bg-black/5 px-3 py-2 dark:bg-white/5">
            <span class="text-gray-500">{{ time(e.created_at) }}</span> {{ e.message }}
            <pre v-if="e.detail" class="mt-1 whitespace-pre-wrap break-words text-[11px] text-gray-500" dir="auto">{{ e.detail }}</pre>
          </div>
          <div v-for="(e, i) in r.browser_events" :key="`b${i}`" class="rounded-lg bg-black/5 px-3 py-2 dark:bg-white/5">
            <span class="text-gray-500">{{ e.at }} · {{ e.kind }}</span> <span dir="auto">{{ e.message }}</span>
            <pre v-if="e.detail" class="mt-1 whitespace-pre-wrap break-words text-[11px] text-gray-500" dir="auto">{{ e.detail }}</pre>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>
