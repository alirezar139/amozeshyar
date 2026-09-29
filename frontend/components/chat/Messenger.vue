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
const PRIVATE_KINDS = ['direct', 'peer']
const GROUP_KINDS = ['course', 'custom']
const directs = computed(() => matching.value.filter((c) => PRIVATE_KINDS.includes(c.kind)).sort(byRecent))
const groups = computed(() => matching.value.filter((c) => GROUP_KINDS.includes(c.kind)).sort(byRecent))
const sections = computed(() =>
  [
    { key: 'direct' as const, title: isTeacher.value ? 'گفت‌وگو با دانشجوها' : 'گفت‌وگوی خصوصی', items: directs.value },
    { key: 'course' as const, title: 'گروه‌ها', items: groups.value },
  ].filter((s) => (tab.value === 'all' || tab.value === s.key) && s.items.length),
)
const unreadOf = (list: any[]) => list.reduce((n, c) => n + (c.unread || 0), 0)
const tabs = computed(() => [
  { key: 'all' as const, label: 'همه', unread: unreadOf(conversations.value) },
  { key: 'direct' as const, label: 'خصوصی', unread: unreadOf(conversations.value.filter((c) => PRIVATE_KINDS.includes(c.kind))) },
  { key: 'course' as const, label: 'گروه‌ها', unread: unreadOf(conversations.value.filter((c) => GROUP_KINDS.includes(c.kind))) },
])

function preview(c: any) {
  const m = c.last_message
  if (!m) return GROUP_KINDS.includes(c.kind) ? 'هنوز پیامی در گروه ارسال نشده است' : c.kind === 'direct' && !isTeacher.value ? 'پرسشی دارید؟ به استاد پیام دهید' : 'هنوز پیامی ارسال نشده است'
  const body = m.text || { image: '📷 عکس', file: '📎 فایل', voice: '🎤 پیام صوتی' }[m.attachment_kind as string] || ''
  const who = m.is_mine ? 'شما: ' : GROUP_KINDS.includes(c.kind) ? `${m.sender_name}: ` : ''
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

// ---- new chat / new group / settings ----
const showMenu = ref(false)
const showNewChat = ref(false)
const showNewGroup = ref(false)
const showSettings = ref(false)
const peerAllowed = ref(true)
const { owner, refresh: refreshSite } = useSite()
watchEffect(() => {
  if (owner.value) peerAllowed.value = owner.value.allow_peer_chat ?? true
})

async function startWith(person: any) {
  const conversation = await request<any>('/conversations/start/', { method: 'POST', body: { student_id: person.id } })
  if (!conversations.value.some((c) => c.id === conversation.id)) conversations.value.unshift(conversation)
  showNewChat.value = false
  open(conversation)
}

const newGroup = reactive({ title: '', member_ids: [] as number[], announcement_only: false })
const creatingGroup = ref(false)
const groupError = ref('')
async function createGroup() {
  if (!newGroup.title.trim()) return
  creatingGroup.value = true
  groupError.value = ''
  try {
    const conversation = await request<any>('/conversations/groups/', { method: 'POST', body: { ...newGroup, title: newGroup.title.trim() } })
    conversations.value.unshift(conversation)
    Object.assign(newGroup, { title: '', member_ids: [], announcement_only: false })
    showNewGroup.value = false
    open(conversation)
  } catch (err) {
    groupError.value = getErrorMessage(err, 'ساخت گروه انجام نشد.')
  } finally {
    creatingGroup.value = false
  }
}

async function togglePeerChat() {
  const next = !peerAllowed.value
  peerAllowed.value = next
  try {
    await request('/site/settings/', { method: 'PATCH', body: { allow_peer_chat: next } })
    await refreshSite()
    loadList()
  } catch {
    peerAllowed.value = !next
  }
}

const { wallpaper, setWallpaper } = useChatWallpaper()

function onUpdated(row: any) {
  const index = conversations.value.findIndex((c) => c.id === row.id)
  if (index !== -1) conversations.value[index] = { ...conversations.value[index], ...row }
}
function onDeleted() {
  const id = activeId.value
  close()
  conversations.value = conversations.value.filter((c) => c.id !== id)
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
          <h2 class="text-lg font-extrabold text-gray-900 dark:text-white">گفت‌وگوها</h2>
          <div class="flex items-center gap-1.5">
            <button
              type="button"
              class="flex h-9 w-9 items-center justify-center rounded-full text-gray-500 transition hover:bg-black/5 hover:text-primary-600 dark:hover:bg-white/10"
              title="تنظیمات پیام‌رسان"
              aria-label="تنظیمات پیام‌رسان"
              data-tour="chat-settings"
              @click="showSettings = true"
            >
              <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
            </button>
            <div class="relative">
              <button
                type="button"
                data-tour="chat-new"
                :class="[
                  'flex h-9 w-9 items-center justify-center rounded-full text-white shadow-lg transition hover:scale-105',
                  showMenu ? 'rotate-45 bg-gray-500' : 'bg-gradient-to-br from-primary-500 to-primary-700 shadow-primary-600/30',
                ]"
                title="گفت‌وگو یا گروه جدید"
                aria-label="گفت‌وگو یا گروه جدید"
                @click="showMenu = !showMenu"
              >
                <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" /></svg>
              </button>
              <Transition name="drop">
                <div v-if="showMenu" class="absolute end-0 top-11 z-30 w-56 overflow-hidden rounded-2xl bg-white p-1.5 shadow-2xl ring-1 ring-black/10 dark:bg-gray-800 dark:ring-white/10" @click="showMenu = false">
                  <button type="button" class="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-start text-sm text-gray-800 hover:bg-black/5 dark:text-gray-100 dark:hover:bg-white/10" @click="showNewChat = true">
                    <span class="flex h-8 w-8 items-center justify-center rounded-full bg-primary-500/15 text-primary-600">👤</span>
                    {{ isTeacher ? 'گفت‌وگو با دانشجو' : 'گفت‌وگو با هم‌کلاسی' }}
                  </button>
                  <button v-if="isTeacher" type="button" class="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-start text-sm text-gray-800 hover:bg-black/5 dark:text-gray-100 dark:hover:bg-white/10" @click="showNewGroup = true">
                    <span class="flex h-8 w-8 items-center justify-center rounded-full bg-accent-500/15 text-accent-600">👥</span>
                    گروه جدید
                  </button>
                </div>
              </Transition>
            </div>
          </div>
        </div>

        <!-- search -->
        <label class="relative block">
          <svg class="pointer-events-none absolute start-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-4.35-4.35M17 11a6 6 0 11-12 0 6 6 0 0112 0z" /></svg>
          <input
            v-model="search"
            placeholder="جست‌وجو در گفت‌وگوها"
            class="w-full rounded-full bg-black/[0.05] py-2 pe-3 ps-9 text-sm text-gray-900 outline-none transition focus:bg-white focus:ring-2 focus:ring-primary-500/40 dark:bg-white/[0.06] dark:text-white dark:focus:bg-white/10"
          >
        </label>

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
          {{ search ? 'نتیجه‌ای یافت نشد.' : isTeacher ? 'هنوز گفت‌وگویی آغاز نشده است. پیام دانشجویان در این بخش نمایش داده می‌شود.' : 'گفت‌وگویی نیست.' }}
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
              <span :class="['inline-flex shrink-0 rounded-full p-0.5', c.unread ? 'bg-gradient-to-br from-primary-400 to-accent-500' : '']">
                <span :class="['inline-flex rounded-full', c.unread ? 'bg-white p-0.5 dark:bg-gray-900' : '']">
                  <ChatAvatar :src="c.avatar" :name="c.title" :group="c.kind === 'course' || c.kind === 'custom'" size="lg" />
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
                  <span v-else-if="c.kind === 'course' || c.kind === 'custom'" class="shrink-0 text-[10px] text-gray-400">{{ c.members.toLocaleString('fa-IR') }} عضو</span>
                </span>
              </span>
            </button>
          </TransitionGroup>
        </section>
      </div>
    </aside>

    <!-- ================= conversation ================= -->
    <section :class="['min-w-0 flex-1', active ? 'flex flex-col' : 'hidden md:flex md:flex-col']">
      <ChatThread
        v-if="active"
        :key="active.id"
        :conversation="active"
        class="h-full"
        @back="close"
        @activity="onActivity"
        @updated="onUpdated"
        @deleted="onDeleted"
      />
      <div v-else class="empty-state flex h-full flex-col items-center justify-center gap-4 p-8 text-center">
        <span class="relative flex h-24 w-24 items-center justify-center">
          <span class="absolute inset-0 animate-ping rounded-full bg-primary-500/10" />
          <span class="relative flex h-20 w-20 items-center justify-center rounded-3xl bg-gradient-to-br from-primary-500 to-accent-500 text-white shadow-xl shadow-primary-600/30">
            <svg class="h-10 w-10" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" /></svg>
          </span>
        </span>
        <p class="text-lg font-bold text-gray-800 dark:text-gray-100">یک گفت‌وگو را انتخاب کنید</p>
        <p class="max-w-xs text-sm leading-6 text-gray-500 dark:text-gray-400">در گفت‌وگوی خصوصی یا گروه هر دوره، پیام متنی، تصویر، فایل و پیام صوتی بفرستید.</p>
      </div>
    </section>

    <!-- new private chat -->
    <ChatModal v-if="showNewChat" :title="isTeacher ? 'گفت‌وگو با دانشجو' : 'گفت‌وگو با هم‌کلاسی'" @close="showNewChat = false">
      <div class="p-4">
        <ChatPeoplePicker @pick="startWith" />
      </div>
    </ChatModal>

    <!-- new group (teacher) -->
    <ChatModal v-if="showNewGroup" title="گروه جدید" wide @close="showNewGroup = false">
      <div class="space-y-4 p-5">
        <div class="flex items-center gap-3">
          <span class="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-accent-500 to-accent-700 text-2xl text-white">👥</span>
          <input
            v-model="newGroup.title"
            autofocus
            maxlength="120"
            placeholder="نام گروه، مثلاً «گروه پروژه‌ی نهایی»"
            class="min-w-0 flex-1 rounded-xl bg-black/[0.05] px-4 py-3 text-sm text-gray-900 outline-none focus:ring-2 focus:ring-primary-500/40 dark:bg-white/[0.07] dark:text-white"
          >
        </div>
        <label class="flex cursor-pointer items-center justify-between gap-3 rounded-2xl bg-black/[0.03] px-4 py-3 dark:bg-white/5">
          <span>
            <span class="block text-sm font-medium text-gray-800 dark:text-gray-100">فقط اطلاع‌رسانی</span>
            <span class="block text-[11px] text-gray-500 dark:text-gray-400">فقط شما پیام می‌فرستید و اعضا می‌خوانند.</span>
          </span>
          <input v-model="newGroup.announcement_only" type="checkbox" class="h-5 w-5 accent-primary-600">
        </label>
        <div>
          <p class="mb-2 text-sm font-medium text-gray-800 dark:text-gray-100">
            اعضا <span class="text-xs text-gray-500">({{ newGroup.member_ids.length.toLocaleString('fa-IR') }} نفر انتخاب شده)</span>
          </p>
          <ChatPeoplePicker v-model="newGroup.member_ids" multiple />
        </div>
        <p v-if="groupError" class="text-sm text-red-600">{{ groupError }}</p>
      </div>
      <template #footer>
        <button
          type="button"
          :disabled="!newGroup.title.trim() || creatingGroup"
          class="w-full rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 py-2.5 text-sm font-semibold text-white shadow-lg shadow-primary-600/30 disabled:opacity-40"
          @click="createGroup"
        >
          {{ creatingGroup ? 'در حال ساخت…' : 'ساخت گروه' }}
        </button>
      </template>
    </ChatModal>

    <!-- messenger settings -->
    <ChatModal v-if="showSettings" title="تنظیمات پیام‌رسان" @close="showSettings = false">
      <div class="space-y-5 p-5">
        <div>
          <p class="mb-2 text-sm font-bold text-gray-800 dark:text-gray-100">پس‌زمینه‌ی گفت‌وگو</p>
          <div class="grid grid-cols-3 gap-2.5">
            <button
              v-for="w in CHAT_WALLPAPERS"
              :key="w.value"
              type="button"
              :class="[
                'overflow-hidden rounded-xl text-center transition',
                wallpaper === w.value ? 'ring-2 ring-primary-500 ring-offset-2 ring-offset-white dark:ring-offset-gray-900' : 'ring-1 ring-black/10 hover:-translate-y-0.5 dark:ring-white/10',
              ]"
              @click="setWallpaper(w.value)"
            >
              <span :class="['chat-bg block h-16', `wp-${w.value}`]" />
              <span class="block py-1.5 text-xs text-gray-700 dark:text-gray-200">{{ w.label }}</span>
            </button>
          </div>
          <p class="mt-2 text-[11px] text-gray-500 dark:text-gray-400">این انتخاب فقط روی همین مرورگر ذخیره می‌شود.</p>
        </div>
        <label v-if="isTeacher" class="flex cursor-pointer items-center justify-between gap-3 rounded-2xl bg-black/[0.03] px-4 py-3 dark:bg-white/5">
          <span>
            <span class="block text-sm font-medium text-gray-800 dark:text-gray-100">گفت‌وگوی دانشجویان با یکدیگر</span>
            <span class="block text-[11px] text-gray-500 dark:text-gray-400">هم‌کلاسی‌ها بتوانند با هم گفت‌وگوی خصوصی داشته باشند.</span>
          </span>
          <button
            type="button"
            role="switch"
            :aria-checked="peerAllowed"
            :class="['relative h-6 w-11 shrink-0 rounded-full transition', peerAllowed ? 'bg-primary-600' : 'bg-gray-300 dark:bg-white/15']"
            @click="togglePeerChat"
          >
            <span :class="['absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-all', peerAllowed ? 'start-[1.375rem]' : 'start-0.5']" />
          </button>
        </label>
      </div>
    </ChatModal>
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
