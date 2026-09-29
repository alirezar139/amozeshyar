<script setup lang="ts">
// Two-pane messenger (list | conversation) used by both the student panel
// and the teacher's admin panel. On phones it shows one pane at a time.
// `?c=<id>` keeps the open conversation in the URL.
const route = useRoute()
const router = useRouter()
const { request } = useApi()
const authStore = useAuthStore()
const { refresh: refreshUnread } = useUnreadMessages()
const isTeacher = computed(() => authStore.isAdmin)

const conversations = ref<any[]>([])
const loading = ref(true)
const search = ref('')

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

const filtered = computed(() => {
  const q = search.value.trim()
  const list = q ? conversations.value.filter((c) => c.title.includes(q) || c.subtitle?.includes(q)) : conversations.value
  // Private chats first for students (their teacher), then by recent activity.
  return [...list].sort((a, b) => {
    const ta = a.last_message_at ? Date.parse(a.last_message_at) : 0
    const tb = b.last_message_at ? Date.parse(b.last_message_at) : 0
    return tb - ta
  })
})

function preview(c: any) {
  const m = c.last_message
  if (!m) return c.kind === 'course' ? 'گروه دوره — هنوز پیامی نیست' : 'شروع گفتگو با استاد'
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
  <div class="glass flex h-[calc(100vh-8rem)] min-h-[32rem] overflow-hidden rounded-2xl">
    <!-- list -->
    <aside
      data-tour="chat-list"
      :class="['flex w-full min-w-0 flex-col border-white/30 md:w-80 md:shrink-0 md:border-e dark:border-white/10', active ? 'hidden md:flex' : 'flex']"
    >
      <div class="space-y-2 border-b border-white/30 p-3 dark:border-white/10">
        <div class="flex items-center gap-2">
          <input
            v-model="search"
            placeholder="جست‌وجو…"
            class="glass min-w-0 flex-1 rounded-xl px-3 py-2 text-sm text-gray-900 outline-none focus:ring-2 focus:ring-primary-500/40 dark:text-white"
          >
          <button
            v-if="isTeacher"
            type="button"
            data-tour="chat-new"
            class="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary-600 text-white hover:bg-primary-500"
            title="گفتگوی جدید با دانشجو"
            aria-label="گفتگوی جدید با دانشجو"
            @click="starting = !starting"
          >
            <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" /></svg>
          </button>
        </div>
        <div v-if="starting" class="rounded-xl bg-black/[0.03] p-2 dark:bg-white/5">
          <input
            v-model="studentQuery"
            autofocus
            placeholder="نام یا ایمیل دانشجو…"
            class="glass w-full rounded-lg px-3 py-1.5 text-sm text-gray-900 outline-none dark:text-white"
          >
          <button
            v-for="s in studentResults"
            :key="s.id"
            type="button"
            class="mt-1 flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-start text-sm hover:bg-primary-500/10"
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
      </div>

      <div class="min-h-0 flex-1 overflow-y-auto p-2">
        <div v-if="loading" class="flex justify-center py-10">
          <span class="h-6 w-6 animate-spin rounded-full border-2 border-primary-500/30 border-t-primary-500" />
        </div>
        <p v-else-if="!filtered.length" class="px-3 py-10 text-center text-sm text-gray-500 dark:text-gray-400">
          {{ isTeacher ? 'هنوز گفتگویی نیست. وقتی دانشجویی پیام بدهد، اینجا می‌آید.' : 'گفتگویی پیدا نشد.' }}
        </p>
        <button
          v-for="c in filtered"
          :key="c.id"
          type="button"
          :class="[
            'flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-start transition',
            c.id === activeId ? 'bg-primary-500/15' : 'hover:bg-black/[0.04] dark:hover:bg-white/5',
          ]"
          @click="open(c)"
        >
          <ChatAvatar :src="c.avatar" :name="c.title" :group="c.kind === 'course'" size="lg" />
          <span class="min-w-0 flex-1">
            <span class="flex items-center justify-between gap-2">
              <span class="truncate font-semibold text-gray-900 dark:text-white">{{ c.title }}</span>
              <span class="shrink-0 text-[11px] text-gray-400">{{ timeOf(c.last_message_at) }}</span>
            </span>
            <span class="mt-0.5 flex items-center justify-between gap-2">
              <span :class="['truncate text-xs', c.unread ? 'font-semibold text-gray-800 dark:text-gray-100' : 'text-gray-500 dark:text-gray-400']" dir="auto">
                {{ preview(c) }}
              </span>
              <span v-if="c.unread" class="flex h-5 min-w-5 shrink-0 items-center justify-center rounded-full bg-primary-600 px-1.5 text-[11px] font-bold text-white">
                {{ c.unread.toLocaleString('fa-IR') }}
              </span>
            </span>
          </span>
        </button>
      </div>
    </aside>

    <!-- conversation -->
    <section :class="['min-w-0 flex-1', active ? 'flex flex-col' : 'hidden md:flex md:flex-col']">
      <ChatThread v-if="active" :key="active.id" :conversation="active" class="h-full" @back="close" @activity="onActivity" />
      <div v-else class="flex h-full flex-col items-center justify-center gap-3 p-8 text-center">
        <span class="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary-500/10 text-primary-600 dark:text-primary-400">
          <svg class="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" /></svg>
        </span>
        <p class="font-semibold text-gray-800 dark:text-gray-100">یک گفتگو را انتخاب کنید</p>
        <p class="max-w-xs text-sm text-gray-500 dark:text-gray-400">پیام متنی، عکس، فایل و پیام صوتی بفرستید.</p>
      </div>
    </section>
  </div>
</template>
