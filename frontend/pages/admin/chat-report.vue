<script setup lang="ts">
// The teacher's read-only record of every conversation on the site —
// classmate chats and student groups included — with deleted messages kept
// and marked (who deleted them, and when).
definePageMeta({ layout: 'admin' })
useSeoMeta({ title: 'گزارش گفت‌وگوها' })

const { request } = useApi()
const { formatGregorianDate } = useJalali()

const KIND_LABELS: Record<string, string> = {
  direct: 'خصوصی با استاد',
  peer: 'هم‌کلاسی‌ها',
  course: 'گروه دوره',
  custom: 'گروه',
}

const { data: rows, pending } = await useAsyncData('chat-report', () => request<any[]>('/conversations/report/'))
const filter = ref<'all' | 'private' | 'deleted'>('all')
const search = ref('')
const shown = computed(() =>
  (rows.value ?? []).filter((r) => {
    if (filter.value === 'private' && !r.private) return false
    if (filter.value === 'deleted' && !r.deleted) return false
    return !search.value.trim() || r.title.includes(search.value.trim())
  }),
)

const active = ref<any | null>(null)
const messages = ref<any[]>([])
const hasMore = ref(false)
const loading = ref(false)

async function open(row: any) {
  active.value = row
  loading.value = true
  try {
    const data = await request<any>(`/conversations/report/${row.id}/`)
    messages.value = data.messages
    hasMore.value = data.has_more
  } finally {
    loading.value = false
  }
}
async function loadOlder() {
  const first = messages.value[0]
  if (!first) return
  const data = await request<any>(`/conversations/report/${active.value.id}/?before=${first.id}`)
  messages.value = [...data.messages, ...messages.value]
  hasMore.value = data.has_more
}

function when(iso: string) {
  const d = new Date(iso)
  return `${formatGregorianDate(d)}، ${d.toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit' })}`
}
</script>

<template>
  <div>
    <h1 class="text-xl font-bold text-gray-900 dark:text-white">گزارش گفت‌وگوها</h1>
    <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
      سابقه‌ی کامل همه‌ی گفت‌وگوهای سایت، از جمله گفت‌وگوی دانشجویان با یکدیگر؛ پیام‌های حذف‌شده هم با نام حذف‌کننده حفظ می‌شوند. این بخش فقط خواندنی است.
    </p>

    <div class="mt-5 grid grid-cols-1 gap-5 lg:grid-cols-5">
      <!-- conversations -->
      <aside class="glass rounded-2xl p-3 lg:col-span-2">
        <input
          v-model="search"
          placeholder="جست‌وجو…"
          class="w-full rounded-full bg-black/[0.05] px-4 py-2 text-sm text-gray-900 outline-none focus:ring-2 focus:ring-primary-500/40 dark:bg-white/[0.07] dark:text-white"
        >
        <div class="mt-2 flex gap-1 rounded-full bg-black/[0.05] p-1 text-xs dark:bg-white/[0.06]">
          <button
            v-for="f in [{ k: 'all', l: 'همه' }, { k: 'private', l: 'دانشجویان با هم' }, { k: 'deleted', l: 'دارای پیام حذف‌شده' }]"
            :key="f.k"
            type="button"
            :class="['flex-1 rounded-full py-1.5 font-semibold transition', filter === f.k ? 'bg-white text-primary-700 shadow-sm dark:bg-white/15 dark:text-white' : 'text-gray-500']"
            @click="filter = f.k as any"
          >
            {{ f.l }}
          </button>
        </div>
        <div v-if="pending" class="py-10 text-center text-sm text-gray-500">در حال بارگذاری...</div>
        <p v-else-if="!shown.length" class="py-10 text-center text-sm text-gray-500">گفت‌وگویی یافت نشد.</p>
        <ul v-else class="mt-2 max-h-[70vh] space-y-1 overflow-y-auto">
          <li v-for="r in shown" :key="r.id">
            <button
              type="button"
              :class="['w-full rounded-xl px-3 py-2.5 text-start transition', active?.id === r.id ? 'bg-primary-500/15' : 'hover:bg-black/[0.04] dark:hover:bg-white/5']"
              @click="open(r)"
            >
              <span class="flex items-center justify-between gap-2">
                <span class="truncate font-semibold text-gray-900 dark:text-white">{{ r.title }}</span>
                <span class="shrink-0 text-[11px] text-gray-400">{{ when(r.last_message_at) }}</span>
              </span>
              <span class="mt-1 flex flex-wrap items-center gap-1.5 text-[11px]">
                <span :class="['rounded-full px-2 py-0.5', r.private ? 'bg-amber-500/15 text-amber-700 dark:text-amber-300' : 'bg-black/5 text-gray-600 dark:bg-white/10 dark:text-gray-300']">
                  {{ KIND_LABELS[r.kind] }}{{ r.kind === 'custom' && r.private ? '‌ی دانشجویی' : '' }}
                </span>
                <span class="text-gray-500">{{ r.messages.toLocaleString('fa-IR') }} پیام</span>
                <span v-if="r.deleted" class="rounded-full bg-red-500/10 px-2 py-0.5 text-red-600">{{ r.deleted.toLocaleString('fa-IR') }} حذف‌شده</span>
              </span>
            </button>
          </li>
        </ul>
      </aside>

      <!-- messages -->
      <section class="glass flex min-h-[24rem] flex-col rounded-2xl lg:col-span-3">
        <div v-if="!active" class="flex flex-1 items-center justify-center p-8 text-sm text-gray-500 dark:text-gray-400">
          یک گفت‌وگو را از فهرست انتخاب کنید.
        </div>
        <template v-else>
          <header class="border-b border-black/5 px-5 py-3 dark:border-white/10">
            <p class="font-bold text-gray-900 dark:text-white">{{ active.title }}</p>
            <p class="text-xs text-gray-500">{{ KIND_LABELS[active.kind] }} · {{ active.members.toLocaleString('fa-IR') }} عضو</p>
          </header>
          <div class="max-h-[70vh] flex-1 space-y-2 overflow-y-auto p-4">
            <button v-if="hasMore" type="button" class="mx-auto block rounded-full bg-black/5 px-4 py-1 text-xs text-gray-600 dark:bg-white/10 dark:text-gray-300" @click="loadOlder">
              پیام‌های قدیمی‌تر
            </button>
            <div v-if="loading" class="py-10 text-center text-sm text-gray-500">در حال بارگذاری...</div>
            <article
              v-for="m in messages"
              v-else
              :key="m.id"
              :class="['rounded-xl px-3.5 py-2.5', m.deleted_at ? 'bg-red-500/[0.07] ring-1 ring-red-500/25' : 'bg-black/[0.03] dark:bg-white/5']"
            >
              <p class="flex flex-wrap items-center justify-between gap-2 text-xs">
                <span class="font-bold text-gray-800 dark:text-gray-100">
                  {{ m.sender.name }}
                  <span v-if="m.sender.is_teacher" class="ms-1 rounded bg-accent-500/15 px-1.5 text-[10px] text-accent-700 dark:text-accent-300">استاد</span>
                </span>
                <span class="text-gray-400">{{ when(m.created_at) }}</span>
              </p>
              <p v-if="m.reply_to" class="mt-1 truncate border-s-2 border-primary-400 ps-2 text-[11px] text-gray-500" dir="auto">
                در پاسخ به {{ m.reply_to.sender_name }}: {{ m.reply_to.text || m.reply_to.attachment_kind }}
              </p>
              <ChatText v-if="m.text" :text="m.text" :class="['mt-1 text-sm text-gray-800 dark:text-gray-100', m.deleted_at ? 'line-through decoration-red-400/60' : '']" />
              <a
                v-if="m.attachment_url"
                :href="m.attachment_url"
                target="_blank"
                rel="noopener"
                class="mt-1 inline-flex items-center gap-1.5 text-xs text-primary-600 hover:underline dark:text-primary-400"
              >
                {{ { image: '📷', file: '📎', voice: '🎤' }[m.attachment_kind as string] }} {{ m.attachment_name }}
              </a>
              <p v-if="m.reactions?.length" class="mt-1 text-xs text-gray-500">
                <span v-for="r in m.reactions" :key="r.emoji" class="me-2">{{ r.emoji }} {{ r.count.toLocaleString('fa-IR') }}</span>
              </p>
              <p v-if="m.deleted_at" class="mt-1.5 text-[11px] font-semibold text-red-600">
                🚫 حذف‌شده توسط {{ m.deleted_by_name }} — {{ when(m.deleted_at) }}
              </p>
            </article>
            <p v-if="!loading && !messages.length" class="py-10 text-center text-sm text-gray-500">پیامی نیست.</p>
          </div>
        </template>
      </section>
    </div>
  </div>
</template>
