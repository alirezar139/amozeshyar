<script setup lang="ts">
// One open conversation: history (older pages on scroll-up), live updates
// by polling `?after=`, optimistic sending with upload progress, read
// receipts (✓ sent, ✓✓ seen) and date separators.
const props = defineProps<{ conversation: any }>()
const emit = defineEmits<{ back: []; activity: []; updated: [row: any]; deleted: [] }>()
const { prefs } = useChatPrefs()
const showInfo = ref(false)
const isGroup = computed(() => ['course', 'custom'].includes(props.conversation.kind))
const kindLabel = computed(() => ({ course: 'گروه دوره', custom: 'گروه', peer: 'هم‌کلاسی', direct: 'خصوصی' } as Record<string, string>)[props.conversation.kind])

async function pinMessage(m: any) {
  emit('updated', await request<any>(`/conversations/${props.conversation.id}/pin/`, { method: 'POST', body: { message_id: m.id } }))
}
function jumpToPinned() {
  const el = scroller.value?.querySelector(`[data-mid="${props.conversation.pinned?.id}"]`)
  el?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  el?.classList.add('flash')
  setTimeout(() => el?.classList.remove('flash'), 1400)
}

const { request } = useApi()
const { upload, uploadErrorMessage } = useUpload()
const { formatGregorianDate } = useJalali()
const { refresh: refreshUnread } = useUnreadMessages()

interface ChatMessage {
  id: number
  sender: { id: number; name: string; is_teacher: boolean; avatar: string | null }
  is_mine: boolean
  text: string
  attachment_kind: '' | 'image' | 'file' | 'voice'
  attachment_name: string
  attachment_size: number
  attachment_url: string | null
  duration_seconds: number | null
  created_at: string
  reply_to?: { id: number; sender_name: string; text: string; attachment_kind: string; deleted?: boolean } | null
  /** Automated sender, e.g. 'exam' for the exam assistant's result messages. */
  bot?: string
  seen_count?: number | null
  is_deleted?: boolean
  reactions?: { emoji: string; count: number; mine: boolean }[]
  // client-only, for optimistic sends
  pending?: boolean
  progress?: number
  failed?: string
  retry?: () => void
}

const messages = ref<ChatMessage[]>([])
const hasMore = ref(false)
const othersLastRead = ref(0)
const loading = ref(true)
const loadingOlder = ref(false)
const scroller = ref<HTMLElement | null>(null)
const atBottom = ref(true)
const newBelow = ref(0)
let tempId = -1

const lastServerId = computed(() => messages.value.reduce((m, x) => (x.id > 0 && x.id > m ? x.id : m), 0))

function scrollToBottom(smooth = false) {
  nextTick(() => {
    const el = scroller.value
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: smooth ? 'smooth' : 'auto' })
    newBelow.value = 0
  })
}

function onScroll() {
  const el = scroller.value
  if (!el) return
  atBottom.value = el.scrollHeight - el.scrollTop - el.clientHeight < 80
  if (atBottom.value) newBelow.value = 0
  if (el.scrollTop < 60 && hasMore.value && !loadingOlder.value) loadOlder()
}

async function markRead() {
  if (!lastServerId.value || document.visibilityState !== 'visible') return
  await request(`/conversations/${props.conversation.id}/read/`, { method: 'POST', body: { message_id: lastServerId.value } }).catch(() => {})
  refreshUnread()
  emit('activity')
}

async function loadInitial() {
  loading.value = true
  try {
    const data = await request<any>(`/conversations/${props.conversation.id}/messages/`)
    serverTime = data.server_time
    messages.value = data.messages
    hasMore.value = data.has_more
    othersLastRead.value = data.others_last_read
    if (data.conversation) emit('updated', data.conversation)
    scrollToBottom()
    markRead()
  } finally {
    loading.value = false
  }
}

async function loadOlder() {
  const first = messages.value.find((m) => m.id > 0)
  if (!first) return
  loadingOlder.value = true
  const el = scroller.value
  const before = el?.scrollHeight ?? 0
  try {
    const data = await request<any>(`/conversations/${props.conversation.id}/messages/?before=${first.id}`)
    messages.value = [...data.messages, ...messages.value]
    hasMore.value = data.has_more
    // keep the viewport on the same message after prepending
    nextTick(() => {
      if (el) el.scrollTop += el.scrollHeight - before
    })
  } finally {
    loadingOlder.value = false
  }
}

let serverTime = ''

// Every poll costs the server several queries, so a quiet thread backs off:
// 3s while messages are flowing, easing to 12s after about a minute of nothing.
// Anything happening (a new or changed message, sending, coming back to the tab) speeds it up again.
const POLL_FAST_MS = 3000
const POLL_SLOW_MS = 12000
const QUIET_POLLS_BEFORE_SLOWING = 20
let quietPolls = 0
function pollDelay() {
  const extra = Math.max(0, quietPolls - QUIET_POLLS_BEFORE_SLOWING) * 1000
  return Math.min(POLL_SLOW_MS, POLL_FAST_MS + extra)
}
function noteActivity() {
  quietPolls = 0
}

async function poll() {
  if (loading.value) return
  quietPolls++
  try {
    const since = serverTime ? `&since=${encodeURIComponent(serverTime)}` : ''
    const data = await request<any>(`/conversations/${props.conversation.id}/messages/?after=${lastServerId.value}${since}`)
    serverTime = data.server_time
    othersLastRead.value = data.others_last_read
    // deletions and reactions on messages already on screen
    for (const changed of (data.changed ?? []) as ChatMessage[]) {
      const index = messages.value.findIndex((m) => m.id === changed.id)
      if (index !== -1) messages.value.splice(index, 1, changed)
      for (const m of messages.value) {
        if (changed.is_deleted && m.reply_to?.id === changed.id) m.reply_to = { ...m.reply_to, text: '', attachment_kind: '', deleted: true }
      }
    }
    if (data.changed?.length) noteActivity()
    if (data.conversation) emit('updated', data.conversation)
    const known = new Set(messages.value.map((m) => m.id))
    const fresh = (data.messages as ChatMessage[]).filter((m) => !known.has(m.id))
    if (!fresh.length) return
    noteActivity()
    messages.value.push(...fresh)
    const fromOthers = fresh.some((m) => !m.is_mine)
    if (atBottom.value) scrollToBottom(true)
    else if (fromOthers) newBelow.value += fresh.filter((m) => !m.is_mine).length
    if (fromOthers) {
      markRead()
      if (prefs.value.sound) playChatChime()
    }
  } catch {
    /* transient; next tick retries */
  }
}

let pollTimer: ReturnType<typeof setTimeout> | null = null
let unmounted = false
function schedulePoll() {
  if (unmounted) return
  pollTimer = setTimeout(async () => {
    if (document.visibilityState === 'visible') await poll()
    schedulePoll()
  }, pollDelay())
}
function onVisible() {
  if (document.visibilityState === 'visible') {
    noteActivity()
    poll()
    markRead()
  }
}
onMounted(() => {
  loadInitial()
  schedulePoll()
  document.addEventListener('visibilitychange', onVisible)
})
onBeforeUnmount(() => {
  unmounted = true
  if (pollTimer) clearTimeout(pollTimer)
  document.removeEventListener('visibilitychange', onVisible)
})

// ---------- message actions (menu on each bubble) ----------
const menuFor = ref<number | null>(null)
const replyTo = ref<ChatMessage | null>(null)
const viewersFor = ref<ChatMessage | null>(null)
const viewers = ref<any[]>([])
const viewersLoading = ref(false)

const menuUp = ref(false)
function toggleMenu(m: ChatMessage, e: MouseEvent) {
  if (m.id < 0 || m.is_deleted) return
  // Clicks on the bubble's own controls (voice player, links, image, file,
  // reaction chips) do their own thing instead of opening the menu.
  const target = e.target as HTMLElement
  const bubble = e.currentTarget as HTMLElement
  if (e.type === 'click' && target.closest('a, button, input') && bubble.contains(target.closest('a, button, input'))) return
  if (menuFor.value === m.id) {
    menuFor.value = null
    return
  }
  // Open upwards for bubbles in the lower half, so the menu isn't cut off.
  const box = scroller.value?.getBoundingClientRect()
  menuUp.value = !!box && bubble.getBoundingClientRect().top - box.top > box.height / 2
  menuFor.value = m.id
}
function closeMenu(e: MouseEvent) {
  if (!(e.target as HTMLElement).closest('[data-msg-menu]')) menuFor.value = null
}
onMounted(() => document.addEventListener('mousedown', closeMenu))
onBeforeUnmount(() => document.removeEventListener('mousedown', closeMenu))

function startReply(m: ChatMessage) {
  replyTo.value = m
  menuFor.value = null
}
async function copyText(m: ChatMessage) {
  menuFor.value = null
  try {
    await navigator.clipboard.writeText(m.text)
  } catch {
    /* clipboard blocked */
  }
}
async function showViewers(m: ChatMessage) {
  menuFor.value = null
  viewersFor.value = m
  viewersLoading.value = true
  try {
    viewers.value = await request<any[]>(`/conversations/${props.conversation.id}/messages/${m.id}/viewers/`)
  } finally {
    viewersLoading.value = false
  }
}
async function deleteMessage(m: ChatMessage) {
  menuFor.value = null
  if (!confirm('این پیام برای همه حذف شود؟')) return
  try {
    await request(`/conversations/${props.conversation.id}/messages/${m.id}/`, { method: 'DELETE' })
  } catch (err) {
    alert(getErrorMessage(err, 'حذف پیام انجام نشد.'))
    return
  }
  Object.assign(m, { is_deleted: true, text: '', attachment_kind: '', attachment_url: null, reply_to: null, reactions: [] })
  for (const x of messages.value) {
    if (x.reply_to?.id === m.id) x.reply_to = { ...x.reply_to, text: '', attachment_kind: '', deleted: true }
  }
  emit('activity')
}
const QUICK_REACTIONS = ['👍', '❤️', '😂', '😮', '😢', '🙏', '🔥', '👏']
async function react(m: ChatMessage, emoji: string) {
  menuFor.value = null
  try {
    const updated = await request<ChatMessage>(`/conversations/${props.conversation.id}/messages/${m.id}/react/`, {
      method: 'POST',
      body: { emoji },
    })
    m.reactions = updated.reactions
  } catch {
    /* e.g. the message was just deleted; the next poll shows that */
  }
}

function canDelete(m: ChatMessage) {
  return m.id > 0 && (m.is_mine || props.conversation.can_manage)
}
function canSeeViewers(m: ChatMessage) {
  return m.id > 0 && (m.is_mine || props.conversation.can_manage)
}
function jumpTo(id: number) {
  const el = scroller.value?.querySelector(`[data-mid="${id}"]`)
  el?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  el?.classList.add('flash')
  setTimeout(() => el?.classList.remove('flash'), 1400)
}
function quoteLabel(q: { text: string; attachment_kind: string; deleted?: boolean }) {
  if (q.deleted) return '🚫 پیام حذف‌شده'
  return q.text || ({ image: '📷 تصویر', file: '📎 فایل', voice: '🎤 پیام صوتی' } as Record<string, string>)[q.attachment_kind] || ''
}
function timeAgo(iso: string) {
  const d = new Date(iso)
  const today = new Date().toDateString() === d.toDateString()
  const time = d.toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit' })
  return today ? `امروز، ${time}` : `${d.toLocaleDateString('fa-IR', { month: 'long', day: 'numeric' })}، ${time}`
}

// ---------- sending ----------
function send(payload: { text: string; file?: File; voice?: boolean; duration?: number }) {
  const quoting = replyTo.value
  replyTo.value = null
  const temp: ChatMessage = reactive({
    id: tempId--,
    sender: { id: 0, name: '', is_teacher: false, avatar: null },
    is_mine: true,
    text: payload.text,
    attachment_kind: payload.voice ? 'voice' : payload.file ? (payload.file.type.startsWith('image/') ? 'image' : 'file') : '',
    attachment_name: payload.file?.name ?? '',
    attachment_size: payload.file?.size ?? 0,
    attachment_url: payload.file && (payload.voice || payload.file.type.startsWith('image/')) ? URL.createObjectURL(payload.file) : null,
    duration_seconds: payload.duration ?? null,
    created_at: new Date().toISOString(),
    reply_to: quoting ? { id: quoting.id, sender_name: quoting.sender.name || 'شما', text: quoting.text, attachment_kind: quoting.attachment_kind } : null,
    pending: true,
    progress: 0,
  })

  const attempt = async () => {
    temp.failed = ''
    temp.pending = true
    try {
      let saved: ChatMessage
      const path = `/conversations/${props.conversation.id}/messages/`
      if (payload.file) {
        const fields: Record<string, string | Blob> = { text: payload.text, file: payload.file }
        if (quoting) fields.reply_to = String(quoting.id)
        if (payload.voice) {
          fields.voice = 'true'
          fields.duration_seconds = String(payload.duration ?? 0)
        }
        saved = await upload<ChatMessage>(path, fields, (p) => (temp.progress = p.percent)).promise
      } else {
        saved = await request<ChatMessage>(path, { method: 'POST', body: { text: payload.text, reply_to: quoting?.id ?? null } })
      }
      noteActivity() // a reply is likely; keep polling fast
      const index = messages.value.indexOf(temp)
      if (index !== -1 && !messages.value.some((m) => m.id === saved.id)) messages.value.splice(index, 1, saved)
      else if (index !== -1) messages.value.splice(index, 1)
      emit('activity')
    } catch (err) {
      temp.pending = false
      temp.failed = payload.file ? uploadErrorMessage(err, 'ارسال نشد.') : getErrorMessage(err, 'ارسال نشد.')
    }
  }
  temp.retry = attempt
  messages.value.push(temp)
  scrollToBottom(true)
  attempt()
}

// ---------- rendering helpers ----------
function dayKey(iso: string) {
  const d = new Date(iso)
  return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`
}
function dayLabel(iso: string) {
  const d = new Date(iso)
  const today = new Date()
  const yesterday = new Date(Date.now() - 86400000)
  if (dayKey(iso) === dayKey(today.toISOString())) return 'امروز'
  if (dayKey(iso) === dayKey(yesterday.toISOString())) return 'دیروز'
  return formatGregorianDate(d)
}
function timeLabel(iso: string) {
  return new Date(iso).toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit' })
}
function showDay(i: number) {
  return i === 0 || dayKey(messages.value[i].created_at) !== dayKey(messages.value[i - 1].created_at)
}
const BOT_NAMES: Record<string, string> = { exam: '🤖 دستیار آزمون' }
function showSender(i: number) {
  const m = messages.value[i]
  if (m.bot) return true
  if (m.is_mine || !isGroup.value) return false
  const prev = messages.value[i - 1]
  return !prev || showDay(i) || prev.bot === 'system' || prev.sender.id !== m.sender.id
}
</script>

<template>
  <div class="flex h-full min-h-0 flex-col">
    <!-- header -->
    <header class="relative z-10 flex items-center gap-3 border-b border-white/40 bg-white/60 px-4 py-3 shadow-sm backdrop-blur-xl dark:border-white/10 dark:bg-gray-900/60">
      <button type="button" class="rounded-lg p-1.5 text-gray-500 hover:bg-black/5 md:hidden dark:hover:bg-white/10" aria-label="بازگشت" @click="emit('back')">
        <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" /></svg>
      </button>
      <button type="button" data-tour="chat-info" class="flex min-w-0 flex-1 items-center gap-3 rounded-xl text-start transition hover:opacity-80" @click="showInfo = !showInfo">
      <ChatAvatar :src="conversation.avatar" :name="conversation.title" :group="isGroup" />
      <div class="min-w-0">
        <p class="flex items-center gap-2 truncate font-bold text-gray-900 dark:text-white">
          {{ conversation.title }}
          <span
            :class="[
              'rounded-full px-2 py-0.5 text-[10px] font-semibold',
              isGroup ? 'bg-accent-500/15 text-accent-700 dark:text-accent-300' : 'bg-primary-500/15 text-primary-700 dark:text-primary-300',
            ]"
          >
            {{ kindLabel }}
          </span>
          <span v-if="conversation.announcement_only" class="rounded-full bg-amber-500/15 px-2 py-0.5 text-[10px] font-semibold text-amber-700 dark:text-amber-300">اطلاع‌رسانی</span>
        </p>
        <p class="truncate text-xs text-gray-500 dark:text-gray-400">
          {{ isGroup ? `${conversation.members.toLocaleString('fa-IR')} عضو · برای مشاهده‌ی اطلاعات بزنید` : conversation.subtitle }}
        </p>
      </div>
      </button>
      <button type="button" class="shrink-0 rounded-full p-2 text-gray-500 hover:bg-black/5 dark:hover:bg-white/10" aria-label="اطلاعات" @click="showInfo = !showInfo">
        <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
      </button>
    </header>

    <!-- students are told their private chats are on record for the teacher -->
    <p
      v-if="conversation.private"
      class="border-b border-amber-500/20 bg-amber-500/10 px-4 py-1.5 text-center text-[11px] text-amber-800 dark:text-amber-300"
    >
      🛡 برای حفظ امنیت کلاس، گفت‌وگوها در گزارش استاد ثبت می‌شود.
    </p>

    <!-- pinned message -->
    <button
      v-if="conversation.pinned"
      type="button"
      class="flex items-center gap-3 border-b border-black/5 bg-white/70 px-4 py-2 text-start backdrop-blur dark:border-white/10 dark:bg-gray-900/70"
      @click="jumpToPinned"
    >
      <span class="h-8 w-1 shrink-0 rounded-full bg-primary-500" />
      <span class="min-w-0 flex-1">
        <span class="block text-[11px] font-bold text-primary-700 dark:text-primary-300">📌 پیام سنجاق‌شده</span>
        <span class="block truncate text-sm text-gray-700 dark:text-gray-200" dir="auto">
          {{ conversation.pinned.text || { image: '📷 تصویر', file: '📎 فایل', voice: '🎤 پیام صوتی' }[conversation.pinned.attachment_kind as string] }}
        </span>
      </span>
    </button>

    <!-- messages -->
    <div class="relative flex min-h-0 flex-1">
    <div ref="scroller" data-tour="chat-messages" :class="['chat-bg relative min-h-0 flex-1 overflow-y-auto px-3 py-4 sm:px-6', `wp-${prefs.wallpaper}`]" @scroll.passive="onScroll">
      <div v-if="loading" class="flex h-full items-center justify-center">
        <span class="h-6 w-6 animate-spin rounded-full border-2 border-primary-500/30 border-t-primary-500" />
      </div>
      <div v-else-if="!messages.length" class="flex h-full flex-col items-center justify-center gap-2 text-center">
        <span class="text-4xl">👋</span>
        <p class="font-semibold text-gray-700 dark:text-gray-200">هنوز پیامی ارسال نشده است</p>
        <p class="text-sm text-gray-500 dark:text-gray-400">نخستین پیام را شما بفرستید.</p>
      </div>
      <template v-else>
        <div v-if="loadingOlder" class="mb-3 flex justify-center">
          <span class="h-5 w-5 animate-spin rounded-full border-2 border-primary-500/30 border-t-primary-500" />
        </div>
        <template v-for="(m, i) in messages" :key="m.id">
          <div v-if="showDay(i)" class="my-3 flex justify-center">
            <span class="rounded-full bg-black/10 px-3 py-0.5 text-[11px] text-gray-700 backdrop-blur dark:bg-white/10 dark:text-gray-200">{{ dayLabel(m.created_at) }}</span>
          </div>
          <!-- system line, e.g. "X joined the group" -->
          <div v-if="m.bot === 'system'" :data-mid="m.id" class="my-2 flex justify-center">
            <span class="max-w-[85%] rounded-full bg-black/10 px-3 py-1 text-center text-xs text-gray-700 backdrop-blur dark:bg-white/10 dark:text-gray-200" dir="auto">{{ m.text }}</span>
          </div>
          <div v-else :data-mid="m.id" :class="['msg-row group/msg mb-1.5 flex items-center gap-1', m.is_mine ? 'justify-start' : 'justify-end']">
            <div
              data-msg-menu
              :class="[
                'bubble relative max-w-[85%] rounded-[1.25rem] px-3.5 py-2 sm:max-w-[70%]',
                m.is_mine
                  ? 'bubble-mine rounded-ss-md bg-gradient-to-br from-primary-500 to-primary-700 text-white shadow-md shadow-primary-700/20'
                  : 'bubble-theirs rounded-se-md bg-white/95 text-gray-900 shadow-md shadow-black/5 ring-1 ring-black/5 dark:bg-gray-800/95 dark:text-gray-100 dark:ring-white/5',
                m.failed ? 'ring-2 ring-red-500' : '',
                menuFor === m.id ? 'ring-2 ring-primary-400/70' : '',
                m.id > 0 ? 'cursor-pointer' : '',
              ]"
              @click="toggleMenu(m, $event)"
              @contextmenu.prevent="toggleMenu(m, $event)"
            >
              <!-- action menu -->
              <Transition name="fade">
                <div
                  v-if="menuFor === m.id"
                  data-msg-menu
                  :class="[
                    'absolute z-30 w-60',
                    menuUp ? 'bottom-full mb-1' : 'top-full mt-1',
                    ' overflow-hidden rounded-2xl bg-white p-1 text-sm text-gray-800 shadow-2xl ring-1 ring-black/10 dark:bg-gray-800 dark:text-gray-100 dark:ring-white/10',
                    m.is_mine ? 'start-0' : 'end-0',
                  ]"
                  @click.stop
                >
                  <div class="mb-1 flex justify-between gap-0.5 border-b border-black/5 px-1 pb-1.5 dark:border-white/10">
                    <button
                      v-for="e in QUICK_REACTIONS"
                      :key="e"
                      type="button"
                      :class="['flex h-7 w-7 items-center justify-center rounded-full text-lg transition hover:scale-125 hover:bg-black/5 dark:hover:bg-white/10', m.reactions?.some((r) => r.mine && r.emoji === e) ? 'bg-primary-500/15' : '']"
                      @click="react(m, e)"
                    >
                      {{ e }}
                    </button>
                  </div>
                  <button type="button" class="menu-item" @click="startReply(m)"><span>↩️</span> پاسخ</button>
                  <button v-if="m.text" type="button" class="menu-item" @click="copyText(m)"><span>📋</span> کپی متن</button>
                  <button v-if="conversation.can_manage" type="button" class="menu-item" @click="pinMessage(m); menuFor = null"><span>📌</span> سنجاق کردن</button>
                  <button v-if="canSeeViewers(m)" type="button" class="menu-item" @click="showViewers(m)"><span>👁</span> دیده‌شده توسط</button>
                  <button v-if="canDelete(m)" type="button" class="menu-item text-red-600" @click="deleteMessage(m)"><span>🗑</span> حذف</button>
                </div>
              </Transition>
              <p v-if="showSender(i)" :class="['mb-0.5 flex items-center gap-1.5 text-xs font-bold', m.is_mine ? 'text-white' : 'text-primary-700 dark:text-primary-300']">
                {{ m.bot ? BOT_NAMES[m.bot] ?? '🤖 دستیار' : m.sender.name }}
                <span v-if="m.sender.is_teacher && !m.bot" class="rounded bg-accent-500/15 px-1.5 text-[10px] font-semibold text-accent-700 dark:text-accent-300">استاد</span>
              </p>

              <!-- quoted message (reply) -->
              <button
                v-if="m.reply_to"
                type="button"
                :class="[
                  'mb-1.5 block w-full rounded-lg border-s-[3px] px-2.5 py-1 text-start',
                  m.is_mine ? 'border-white/70 bg-white/15' : 'border-primary-500 bg-primary-500/[0.08]',
                ]"
                @click.stop="jumpTo(m.reply_to.id)"
              >
                <span :class="['block text-[11px] font-bold', m.is_mine ? 'text-white' : 'text-primary-700 dark:text-primary-300']">{{ m.reply_to.sender_name }}</span>
                <span :class="['block truncate text-xs', m.is_mine ? 'text-white/85' : 'text-gray-600 dark:text-gray-300']" dir="auto">{{ quoteLabel(m.reply_to) }}</span>
              </button>

              <!-- image -->
              <a
                v-if="m.attachment_kind === 'image' && m.attachment_url"
                :href="m.attachment_url"
                target="_blank"
                rel="noopener"
                class="mb-1 block overflow-hidden rounded-xl"
              >
                <img :src="m.attachment_url" :alt="m.attachment_name" class="max-h-72 w-full object-cover" loading="lazy">
              </a>
              <!-- voice -->
              <ChatVoicePlayer
                v-else-if="m.attachment_kind === 'voice' && m.attachment_url"
                :src="m.attachment_url"
                :duration="m.duration_seconds"
                :mine="m.is_mine"
                class="py-1"
              />
              <!-- file -->
              <a
                v-else-if="m.attachment_kind === 'file' || (m.attachment_kind && !m.attachment_url)"
                :href="m.attachment_url || undefined"
                target="_blank"
                rel="noopener"
                :class="['mb-1 flex items-center gap-3 rounded-xl p-2', m.is_mine ? 'bg-white/15' : 'bg-black/[0.04] dark:bg-white/5']"
              >
                <CourseFileIcon :extension="m.attachment_name.split('.').pop()" size="sm" />
                <span class="min-w-0">
                  <span class="block truncate text-sm font-medium" dir="auto">{{ m.attachment_name }}</span>
                  <span :class="['text-[11px]', m.is_mine ? 'text-white/75' : 'text-gray-500']">{{ formatBytes(m.attachment_size) }}</span>
                </span>
              </a>

              <p v-if="m.is_deleted" :class="['flex items-center gap-1.5 italic', m.is_mine ? 'text-white/80' : 'text-gray-500 dark:text-gray-400', `chat-text-${prefs.fontSize}`]">
                🚫 این پیام حذف شد
              </p>
              <ChatText v-else-if="m.text" :text="m.text" :mine="m.is_mine" :class="`chat-text-${prefs.fontSize}`" />

              <!-- reactions -->
              <div v-if="m.reactions?.length" class="mt-1.5 flex flex-wrap gap-1">
                <button
                  v-for="r in m.reactions"
                  :key="r.emoji"
                  type="button"
                  :class="[
                    'flex items-center gap-1 rounded-full px-2 py-0.5 text-xs transition hover:scale-105',
                    r.mine
                      ? (m.is_mine ? 'bg-white text-primary-700 ring-1 ring-white' : 'bg-primary-500/15 text-primary-700 ring-1 ring-primary-400/50 dark:text-primary-300')
                      : (m.is_mine ? 'bg-white/20 text-white' : 'bg-black/5 text-gray-700 dark:bg-white/10 dark:text-gray-200'),
                  ]"
                  :title="r.mine ? 'برداشتن واکنش' : 'افزودن همین واکنش'"
                  @click.stop="react(m, r.emoji)"
                >
                  <span class="text-sm">{{ r.emoji }}</span>
                  <span class="font-semibold tabular-nums">{{ r.count.toLocaleString('fa-IR') }}</span>
                </button>
              </div>

              <!-- upload progress -->
              <div v-if="m.pending && m.attachment_kind" class="mt-1.5 h-1 overflow-hidden rounded-full bg-white/25">
                <div class="h-full rounded-full bg-white transition-[width]" :style="{ width: `${m.progress ?? 0}%` }" />
              </div>

              <div :class="['mt-0.5 flex items-center justify-end gap-1 text-[10px]', m.is_mine ? 'text-white/75' : 'text-gray-400']">
                <span class="tabular-nums">{{ timeLabel(m.created_at) }}</span>
                <span
                  v-if="m.is_mine && isGroup && m.seen_count"
                  class="flex items-center gap-0.5"
                  :title="`دیده‌شده توسط ${m.seen_count.toLocaleString('fa-IR')} نفر`"
                >
                  <svg class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.2"><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path stroke-linecap="round" stroke-linejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>
                  {{ m.seen_count.toLocaleString('fa-IR') }}
                </span>
                <template v-if="m.is_mine">
                  <svg v-if="m.pending" class="h-3 w-3 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>
                  <span v-else-if="!m.failed" :class="m.id <= othersLastRead ? 'text-sky-200' : ''" :title="m.id <= othersLastRead ? 'خوانده شد' : 'ارسال شد'">
                    {{ m.id <= othersLastRead ? '✓✓' : '✓' }}
                  </span>
                </template>
              </div>
              <button v-if="m.failed" type="button" class="mt-1 text-xs font-semibold text-red-200 underline" @click="m.retry?.()">
                {{ m.failed }} — تلاش دوباره
              </button>
            </div>
          </div>
        </template>
      </template>

      <button
        v-if="newBelow"
        type="button"
        class="sticky bottom-2 mx-auto mt-2 flex w-fit items-center gap-1.5 rounded-full bg-primary-600 px-3 py-1.5 text-xs font-semibold text-white shadow-lg"
        @click="scrollToBottom(true)"
      >
        {{ newBelow.toLocaleString('fa-IR') }} پیام جدید ↓
      </button>
    </div>

    <Transition name="fade">
      <ChatInfo
        v-if="showInfo"
        :conversation="conversation"
        class="absolute inset-y-0 end-0 z-20 w-full border-s border-black/5 shadow-2xl sm:w-80 dark:border-white/10"
        @close="showInfo = false"
        @updated="emit('updated', $event)"
        @deleted="emit('deleted')"
      />
    </Transition>
    </div>

    <Transition name="fade">
      <div v-if="replyTo" class="flex items-center gap-3 border-t border-black/5 bg-white/80 px-4 py-2 backdrop-blur dark:border-white/10 dark:bg-gray-900/80">
        <span class="text-primary-600">↩️</span>
        <span class="min-w-0 flex-1 border-s-[3px] border-primary-500 ps-2.5">
          <span class="block text-[11px] font-bold text-primary-700 dark:text-primary-300">پاسخ به {{ replyTo.is_mine ? 'پیام خودتان' : replyTo.sender.name }}</span>
          <span class="block truncate text-xs text-gray-600 dark:text-gray-300" dir="auto">{{ quoteLabel(replyTo) }}</span>
        </span>
        <button type="button" class="rounded-full p-1 text-gray-400 hover:text-gray-700" aria-label="لغو پاسخ" @click="replyTo = null">
          <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
        </button>
      </div>
    </Transition>

    <!-- who saw a message -->
    <ChatModal v-if="viewersFor" title="دیده‌شده توسط" @close="viewersFor = null">
      <div class="p-4">
        <p class="mb-3 line-clamp-2 rounded-xl bg-black/[0.04] px-3 py-2 text-sm text-gray-600 dark:bg-white/5 dark:text-gray-300" dir="auto">{{ quoteLabel(viewersFor) }}</p>
        <div v-if="viewersLoading" class="py-8 text-center text-sm text-gray-500">در حال بارگذاری...</div>
        <p v-else-if="!viewers.length" class="py-8 text-center text-sm text-gray-500 dark:text-gray-400">هنوز کسی این پیام را ندیده است.</p>
        <ul v-else class="space-y-1">
          <li v-for="v in viewers" :key="v.id" class="flex items-center gap-3 rounded-xl px-2 py-1.5">
            <ChatAvatar :src="v.avatar" :name="v.name" />
            <span class="min-w-0 flex-1">
              <span class="block truncate text-sm font-semibold text-gray-900 dark:text-white">{{ v.name }}</span>
              <span class="block text-[11px] text-gray-500 dark:text-gray-400">{{ timeAgo(v.read_at) }}</span>
            </span>
            <span class="text-sky-500">✓✓</span>
          </li>
        </ul>
        <p v-if="viewers.length && isGroup" class="mt-3 text-center text-[11px] text-gray-400">
          {{ viewers.length.toLocaleString('fa-IR') }} نفر از {{ (conversation.members - 1).toLocaleString('fa-IR') }} عضو دیگر
        </p>
      </div>
    </ChatModal>

    <ChatComposer
      data-tour="chat-composer"
      :readonly-note="conversation.can_send === false ? 'در این گروه فقط استاد پیام می‌فرستد.' : ''"
      @send="send"
    />
  </div>
</template>

<style scoped>
.msg-row.flash > div:not(button) {
  animation: flash 1.2s ease;
}
@keyframes flash {
  0%, 100% { box-shadow: none; }
  30% { box-shadow: 0 0 0 4px rgb(var(--c-accent-500) / 0.45); }
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.menu-item {
  display: flex;
  width: 100%;
  align-items: center;
  gap: 0.6rem;
  border-radius: 0.75rem;
  padding: 0.5rem 0.75rem;
  text-align: start;
  transition: background-color 0.15s;
}
.menu-item:hover {
  background: rgb(0 0 0 / 0.05);
}
html.dark .menu-item:hover {
  background: rgb(255 255 255 / 0.08);
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* New messages pop in. */
.bubble {
  animation: bubble-in 0.22s cubic-bezier(0.22, 1, 0.36, 1);
}
@keyframes bubble-in {
  from { opacity: 0; transform: translateY(6px) scale(0.98); }
  to { opacity: 1; transform: none; }
}
</style>
