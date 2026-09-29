<script setup lang="ts">
// Two-pane messenger (list | conversation) used by both the student panel
// and the teacher's admin panel. On phones it shows one pane at a time.
// `?c=<id>` keeps the open conversation in the URL. The list is split into
// private chats and course groups, with tabs to show just one kind.
const route = useRoute()
const router = useRouter()
const { request } = useApi()
const authStore = useAuthStore()
const { refresh: refreshUnread } = useUnreadMessages()
const isTeacher = computed(() => authStore.isAdmin)

const conversations = ref<any[]>([])
const loading = ref(true)
const search = ref('')
const tab = ref<'all' | 'direct' | 'course'>('all')

async function loadList() {
  try {
    conversations.value = await request<any[]>('/conversations/')
  } finally {
    loading.value = false
  }
}

const activeId = computed(() => Number(route.query.c) || null)
const active = computed(() => conversations.value.find((c) => c.id === activeId.value) ?? null)

function open(conversation: any) {
  router.replace({ query: { ...route.query, c: conversation.id } })
  conversation.unread = 0
}
function close() {
  const { c, ...rest } = route.query
  router.replace({ query: rest })
}

function byRecent(a: any, b: any) {
  const ta = a.last_message_at ? Date.parse(a.last_message_at) : 0
  const tb = b.last_message_at ? Date.parse(b.last_message_at) : 0
  return tb - ta
}
const matching = computed(() => {
  const q = search.value.trim()
  return q ? conversations.value.filter((c) => c.title.includes(q) || c.subtitle?.includes(q)) : conversations.value
})
const directs = computed(() => matching.value.filter((c) => c.kind === 'direct').sort(byRecent))
const groups = computed(() => matching.value.filter((c) => c.kind === 'course').sort(byRecent))
const sections = computed(() =>
  [
    { key: 'direct' as const, title: isTeacher.value ? 'گفتگو با دانشجوها' : 'گفتگوی خصوصی', items: directs.value },
    { key: 'course' as const, title: 'گروه‌های دوره', items: groups.value },
  ].filter((s) => (tab.value === 'all' || tab.value === s.key) && s.items.length),
)
const unreadOf = (list: any[]) => list.reduce((n, c) => n + (c.unread || 0), 0)
const tabs = computed(() => [
  { key: 'all' as const, label: 'همه', unread: unreadOf(conversations.value) },
  { key: 'direct' as const, label: 'خصوصی', unread: unreadOf(conversations.value.filter((c) => c.kind === 'direct')) },
  { key: 'course' as const, label: 'گروه‌ها', unread: unreadOf(conversations.value.filter((c) => c.kind === 'course')) },
])

function preview(c: any) {
  const m = c.last_message
  if (!m) return c.kind === 'course' ? 'هنوز پیامی در گروه نیست' : isTeacher.value ? 'بدون پیام' : 'سوالی دارید؟ به استاد پیام بدهید'
  const body = m.text || { image: '📷 عکس', file: '📎 فایل', voice: '🎤 پیام صوتی' }[m.attachment_kind as string] || ''
  const who = m.is_mine ? 'شما: ' : c.kind === 'course' ? `${m.sender_name}: ` : ''
  return who + body
}

function timeOf(iso: string | null) {
  if (!iso) return ''
  const d = new Date(iso)
  const sameDay = new Date().toDateString() === d.toDateString()
  return sameDay
    ? d.toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit' })
    : d.toLocaleDateString('fa-IR', { month: 'short', day: 'numeric' })
}

// ---- teacher: start a chat with any student ----
const starting = ref(false)
const studentQuery = ref('')
const studentResults = ref<any[]>([])
let searchTimer: ReturnType<typeof setTimeout> | null = null
watch(studentQuery, (q) => {
  if (searchTimer) clearTimeout(searchTimer)
  if (!q.trim()) {
    studentResults.value = []
    return
  }
  searchTimer = setTimeout(async () => {
    const page = await request<{ results: any[] }>(`/auth/admin/users/?search=${encodeURIComponent(q.trim())}`).catch(() => ({ results: [] }))
    studentResults.value = page.results.filter((u) => u.role === 'student').slice(0, 8)
  }, 300)
})
async function startWith(student: any) {
  const conversation = await request<any>('/conversations/start/', { method: 'POST', body: { student_id: student.id } })
  if (!conversations.value.some((c) => c.id === conversation.id)) conversations.value.unshift(conversation)
  starting.value = false
  studentQuery.value = ''
  open(conversation)
}

// ---- polling ----
let timer: ReturnType<typeof setInterval> | null = null
onMounted(async () => {
  await loadList()
  // A student lands on their teacher chat by default on wide screens.
  if (!activeId.value && !isTeacher.value && window.matchMedia('(min-width: 768px)').matches) {
    const direct = conversations.value.find((c) => c.kind === 'direct')
    if (direct) open(direct)
  }
  timer = setInterval(() => document.visibilityState === 'visible' && loadList(), 10000)
})
onBeforeUnmount(() => timer && clearInterval(timer))

function onActivity() {
  loadList()
  refreshUnread()
}
</script>

<template>
  <div class="messenger glass flex h-[calc(100vh-8rem)] min-h-[32rem] overflow-hidden rounded-3xl shadow-2xl shadow-black/5">
    <!-- ================= list ================= -->
    <aside
      data-tour="chat-list"
      :class="[
        'flex w-full min-w-0 flex-col bg-white/40 md:w-[21rem] md:shrink-0 md:border-e md:border-white/40 dark:bg-black/10 dark:md:border-white/10',
        active ? 'hidden md:flex' : 'flex',
      ]"
    >
      <div class="space-y-3 px-4 pb-3 pt-4">
        <div class="flex items-center justify-between">
          <h2 class="text-lg font-extrabold text-gray-900 dark:text-white">گفتگوها</h2>
          <button
            v-if="isTeacher"
            type="button"
            data-tour="chat-new"
            :class="[
              'flex h-9 w-9 items-center justify-center rounded-full text-white shadow-lg transition hover:scale-105',
              starting ? 'rotate-45 bg-gray-500' : 'bg-gradient-to-br from-primary-500 to-primary-700 shadow-primary-600/30',
            ]"
            title="گفتگوی جدید با دانشجو"
            aria-label="گفتگوی جدید با دانشجو"
            @click="starting = !starting"
          >
            <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" /></svg>
          </button>
        </div>

        <!-- search -->
        <label class="relative block">
          <svg class="pointer-events-none absolute start-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-4.35-4.35M17 11a6 6 0 11-12 0 6 6 0 0112 0z" /></svg>
          <input
            v-model="search"
            placeholder="جست‌وجو در گفتگوها"
            class="w-full rounded-full bg-black/[0.05] py-2 pe-3 ps-9 text-sm text-gray-900 outline-none transition focus:bg-white focus:ring-2 focus:ring-primary-500/40 dark:bg-white/[0.06] dark:text-white dark:focus:bg-white/10"
          >
        </label>

        <!-- start chat (teacher) -->
        <Transition name="drop">
          <div v-if="starting" class="rounded-2xl bg-primary-500/[0.07] p-2 ring-1 ring-primary-500/20">
            <input
              v-model="studentQuery"
              autofocus
              placeholder="نام یا ایمیل دانشجو…"
              class="w-full rounded-xl bg-white/70 px-3 py-2 text-sm text-gray-900 outline-none dark:bg-white/10 dark:text-white"
            >
            <button
              v-for="s in studentResults"
              :key="s.id"
              type="button"
              class="mt-1 flex w-full items-center gap-2.5 rounded-xl px-2 py-1.5 text-start text-sm transition hover:bg-white/70 dark:hover:bg-white/10"
              @click="startWith(s)"
            >
              <ChatAvatar :name="s.first_name || s.email" />
              <span class="min-w-0">
                <span class="block truncate font-medium text-gray-800 dark:text-gray-100">{{ `${s.first_name} ${s.last_name}`.trim() || s.email }}</span>
                <span class="block truncate text-[11px] text-gray-500">{{ s.email }}</span>
              </span>
            </button>
            <p v-if="studentQuery && !studentResults.length" class="mt-1 px-2 text-xs text-gray-500">دانشجویی پیدا نشد.</p>
          </div>
        </Transition>

        <!-- tabs -->
        <div class="flex gap-1 rounded-full bg-black/[0.05] p-1 dark:bg-white/[0.06]">
          <button
            v-for="t in tabs"
            :key="t.key"
            type="button"
            :class="[
              'flex flex-1 items-center justify-center gap-1.5 rounded-full py-1.5 text-xs font-semibold transition',
              tab === t.key ? 'bg-white text-primary-700 shadow-sm dark:bg-white/15 dark:text-white' : 'text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200',
            ]"
            @click="tab = t.key"
          >
            {{ t.label }}
            <span v-if="t.unread" class="flex h-4 min-w-4 items-center justify-center rounded-full bg-primary-600 px-1 text-[10px] text-white">
              {{ t.unread.toLocaleString('fa-IR') }}
            </span>
          </button>
        </div>
      </div>

      <div class="min-h-0 flex-1 overflow-y-auto px-2 pb-3">
        <div v-if="loading" class="space-y-2 px-2 pt-2">
          <div v-for="i in 5" :key="i" class="flex animate-pulse items-center gap-3 rounded-2xl p-2">
            <span class="h-12 w-12 rounded-full bg-black/10 dark:bg-white/10" />
            <span class="flex-1 space-y-2"><span class="block h-3 w-2/3 rounded bg-black/10 dark:bg-white/10" /><span class="block h-2.5 w-1/2 rounded bg-black/5 dark:bg-white/5" /></span>
          </div>
        </div>
        <p v-else-if="!sections.length" class="px-4 py-12 text-center text-sm text-gray-500 dark:text-gray-400">
          {{ search ? 'چیزی پیدا نشد.' : isTeacher ? 'هنوز گفتگویی نیست. وقتی دانشجویی پیام بدهد، اینجا می‌آید.' : 'گفتگویی نیست.' }}
        </p>

        <section v-for="(section, si) in sections" :key="section.key">
          <!-- section divider -->
          <div :class="['flex items-center gap-2 px-3 pb-1.5', si ? 'pt-4' : 'pt-1']">
            <svg v-if="section.key === 'course'" class="h-3.5 w-3.5 text-accent-600 dark:text-accent-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M17 20h5v-2a4 4 0 00-3-3.87M9 20H4v-2a4 4 0 013-3.87m6-4.13a4 4 0 10-4-4 4 4 0 004 4zm6 0a4 4 0 10-4-4" /></svg>
            <svg v-else class="h-3.5 w-3.5 text-primary-600 dark:text-primary-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>
            <span class="text-[11px] font-bold uppercase tracking-wide text-gray-500 dark:text-gray-400">{{ section.title }}</span>
            <span class="h-px flex-1 bg-gradient-to-l from-transparent via-black/10 to-black/15 dark:via-white/10 dark:to-white/15" />
            <span class="text-[11px] text-gray-400">{{ section.items.length.toLocaleString('fa-IR') }}</span>
          </div>

          <TransitionGroup tag="div" name="row" class="space-y-0.5">
            <button
              v-for="c in section.items"
              :key="c.id"
              type="button"
              :class="[
                'row group relative flex w-full items-center gap-3 rounded-2xl px-2.5 py-2.5 text-start transition',
                c.id === activeId
                  ? 'bg-gradient-to-l from-primary-500/20 to-primary-500/5 shadow-sm'
                  : 'hover:bg-white/60 dark:hover:bg-white/[0.06]',
              ]"
              @click="open(c)"
            >
              <span v-if="c.id === activeId" class="absolute inset-y-3 start-0 w-1 rounded-full bg-primary-500" />
              <span :class="['rounded-full p-0.5', c.unread ? 'bg-gradient-to-br from-primary-400 to-accent-500' : '']">
                <span :class="['block rounded-full', c.unread ? 'bg-white p-0.5 dark:bg-gray-900' : '']">
                  <ChatAvatar :src="c.avatar" :name="c.title" :group="c.kind === 'course'" size="lg" />
                </span>
              </span>
              <span class="min-w-0 flex-1">
                <span class="flex items-center justify-between gap-2">
                  <span :class="['truncate text-[15px] text-gray-900 dark:text-white', c.unread ? 'font-extrabold' : 'font-semibold']">{{ c.title }}</span>
                  <span :class="['shrink-0 text-[11px]', c.unread ? 'font-semibold text-primary-600 dark:text-primary-400' : 'text-gray-400']">{{ timeOf(c.last_message_at) }}</span>
                </span>
                <span class="mt-0.5 flex items-center justify-between gap-2">
                  <span :class="['truncate text-xs', c.unread ? 'font-medium text-gray-700 dark:text-gray-200' : 'text-gray-500 dark:text-gray-400']" dir="auto">
                    {{ preview(c) }}
                  </span>
                  <span v-if="c.unread" class="flex h-5 min-w-5 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-primary-500 to-primary-700 px-1.5 text-[11px] font-bold text-white shadow shadow-primary-600/30">
                    {{ c.unread.toLocaleString('fa-IR') }}
                  </span>
                  <span v-else-if="c.kind === 'course'" class="shrink-0 text-[10px] text-gray-400">{{ c.members.toLocaleString('fa-IR') }} عضو</span>
                </span>
              </span>
            </button>
          </TransitionGroup>
        </section>
      </div>
    </aside>

    <!-- ================= conversation ================= -->
    <section :class="['min-w-0 flex-1', active ? 'flex flex-col' : 'hidden md:flex md:flex-col']">
      <ChatThread v-if="active" :key="active.id" :conversation="active" class="h-full" @back="close" @activity="onActivity" />
      <div v-else class="empty-state flex h-full flex-col items-center justify-center gap-4 p-8 text-center">
        <span class="relative flex h-24 w-24 items-center justify-center">
          <span class="absolute inset-0 animate-ping rounded-full bg-primary-500/10" />
          <span class="relative flex h-20 w-20 items-center justify-center rounded-3xl bg-gradient-to-br from-primary-500 to-accent-500 text-white shadow-xl shadow-primary-600/30">
            <svg class="h-10 w-10" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" /></svg>
          </span>
        </span>
        <p class="text-lg font-bold text-gray-800 dark:text-gray-100">یک گفتگو را انتخاب کنید</p>
        <p class="max-w-xs text-sm leading-6 text-gray-500 dark:text-gray-400">پیام متنی، عکس، فایل و پیام صوتی بفرستید — در گفتگوی خصوصی یا گروه دوره.</p>
      </div>
    </section>
  </div>
</template>

<style scoped>
.empty-state {
  background-image: radial-gradient(rgb(var(--c-primary-500) / 0.08) 1px, transparent 1px);
  background-size: 20px 20px;
}
.drop-enter-active,
.drop-leave-active {
  transition: all 0.2s ease;
}
.drop-enter-from,
.drop-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
.row-move {
  transition: transform 0.3s ease;
}
</style>
