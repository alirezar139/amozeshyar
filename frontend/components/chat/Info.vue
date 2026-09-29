<script setup lang="ts">
// Side panel for a conversation: who's in it, the pinned message, and — for
// the teacher in a group — its settings (name, announcement-only mode,
// members, delete).
const props = defineProps<{ conversation: any }>()
const emit = defineEmits<{ close: []; updated: [row: any]; deleted: [] }>()

const { request } = useApi()
const members = ref<any[]>([])
const loading = ref(true)
const error = ref('')
const title = ref(props.conversation.title)
const adding = ref(false)
const toAdd = ref<number[]>([])

const isCustom = computed(() => props.conversation.kind === 'custom')
const manage = computed(() => props.conversation.can_manage)

async function loadMembers() {
  loading.value = true
  try {
    members.value = await request<any[]>(`/conversations/${props.conversation.id}/members/`)
  } finally {
    loading.value = false
  }
}
onMounted(loadMembers)
watch(() => props.conversation.id, loadMembers)

async function saveSettings(body: Record<string, unknown>) {
  error.value = ''
  try {
    emit('updated', await request<any>(`/conversations/${props.conversation.id}/settings/`, { method: 'PATCH', body }))
  } catch (err) {
    error.value = getErrorMessage(err, 'ذخیره نشد.')
  }
}

async function unpin() {
  emit('updated', await request<any>(`/conversations/${props.conversation.id}/pin/`, { method: 'POST', body: { message_id: null } }))
}

async function addMembers() {
  if (!toAdd.value.length) return
  members.value = await request<any[]>(`/conversations/${props.conversation.id}/members/`, { method: 'POST', body: { user_ids: toAdd.value } })
  toAdd.value = []
  adding.value = false
  emit('updated', { ...props.conversation, members: members.value.length })
}

async function removeMember(member: any) {
  if (!confirm(`${member.name} از گروه حذف شود؟`)) return
  await request(`/conversations/${props.conversation.id}/members/${member.id}/`, { method: 'DELETE' })
  members.value = members.value.filter((m) => m.id !== member.id)
  emit('updated', { ...props.conversation, members: members.value.length })
}

async function deleteGroup() {
  if (!confirm(`گروه «${props.conversation.title}» و همه‌ی پیام‌هایش حذف شود؟ این کار برگشت‌پذیر نیست.`)) return
  await request(`/conversations/${props.conversation.id}/`, { method: 'DELETE' })
  emit('deleted')
}
</script>

<template>
  <aside class="info-panel flex h-full w-full flex-col bg-white/80 backdrop-blur-xl dark:bg-gray-900/85">
    <header class="flex items-center justify-between border-b border-black/5 px-4 py-3 dark:border-white/10">
      <p class="font-bold text-gray-900 dark:text-white">{{ conversation.kind === 'course' || isCustom ? 'اطلاعات گروه' : 'اطلاعات گفت‌وگو' }}</p>
      <button type="button" class="rounded-full p-1.5 text-gray-400 hover:bg-black/5 hover:text-gray-700 dark:hover:bg-white/10" aria-label="بستن" @click="emit('close')">
        <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
      </button>
    </header>

    <div class="min-h-0 flex-1 space-y-5 overflow-y-auto p-4">
      <div class="flex flex-col items-center gap-2 text-center">
        <ChatAvatar :src="conversation.avatar" :name="conversation.title" :group="conversation.kind === 'course' || isCustom" size="lg" class="!h-20 !w-20" />
        <p class="text-lg font-extrabold text-gray-900 dark:text-white">{{ conversation.title }}</p>
        <p class="text-xs text-gray-500 dark:text-gray-400">
          {{ conversation.subtitle }} · {{ conversation.members.toLocaleString('fa-IR') }} عضو
        </p>
      </div>

      <!-- pinned -->
      <section v-if="conversation.pinned" class="rounded-2xl bg-primary-500/[0.07] p-3 ring-1 ring-primary-500/15">
        <p class="flex items-center gap-1.5 text-xs font-bold text-primary-700 dark:text-primary-300">📌 پیام سنجاق‌شده</p>
        <p class="mt-1 line-clamp-3 text-sm text-gray-700 dark:text-gray-200" dir="auto">
          {{ conversation.pinned.text || { image: '📷 تصویر', file: '📎 فایل', voice: '🎤 پیام صوتی' }[conversation.pinned.attachment_kind as string] }}
        </p>
        <button v-if="manage" type="button" class="mt-2 text-xs text-red-600 hover:underline" @click="unpin">برداشتن سنجاق</button>
      </section>

      <!-- settings (teacher, groups) -->
      <section v-if="manage" class="space-y-3 rounded-2xl bg-black/[0.03] p-3 dark:bg-white/5">
        <p class="text-xs font-bold text-gray-500 dark:text-gray-400">تنظیمات گروه</p>
        <form v-if="isCustom" class="flex gap-2" @submit.prevent="saveSettings({ title })">
          <input v-model="title" class="min-w-0 flex-1 rounded-xl bg-white px-3 py-2 text-sm text-gray-900 outline-none ring-1 ring-black/10 focus:ring-2 focus:ring-primary-500/40 dark:bg-white/10 dark:text-white dark:ring-white/10">
          <button type="submit" :disabled="!title.trim() || title === conversation.title" class="rounded-xl bg-primary-600 px-3 text-sm font-semibold text-white disabled:opacity-40">ذخیره</button>
        </form>
        <label class="flex cursor-pointer items-center justify-between gap-3">
          <span>
            <span class="block text-sm font-medium text-gray-800 dark:text-gray-100">فقط اطلاع‌رسانی</span>
            <span class="block text-[11px] text-gray-500 dark:text-gray-400">دانشجویان فقط پیام‌ها را می‌خوانند و نمی‌توانند پیام بفرستند.</span>
          </span>
          <button
            type="button"
            role="switch"
            :aria-checked="conversation.announcement_only"
            :class="['relative h-6 w-11 shrink-0 rounded-full transition', conversation.announcement_only ? 'bg-primary-600' : 'bg-gray-300 dark:bg-white/15']"
            @click="saveSettings({ announcement_only: !conversation.announcement_only })"
          >
            <span :class="['absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-all', conversation.announcement_only ? 'start-[1.375rem]' : 'start-0.5']" />
          </button>
        </label>
        <p v-if="error" class="text-xs text-red-600">{{ error }}</p>
      </section>

      <!-- members -->
      <section>
        <div class="mb-2 flex items-center justify-between">
          <p class="text-xs font-bold text-gray-500 dark:text-gray-400">اعضا</p>
          <button v-if="manage && isCustom" type="button" class="text-xs font-semibold text-primary-600 hover:underline dark:text-primary-400" @click="adding = !adding">
            {{ adding ? 'انصراف' : '+ افزودن عضو' }}
          </button>
        </div>
        <div v-if="adding" class="mb-3 rounded-2xl bg-black/[0.03] p-3 dark:bg-white/5">
          <ChatPeoplePicker v-model="toAdd" multiple :exclude="members.map((m) => m.id)" />
          <button
            type="button"
            :disabled="!toAdd.length"
            class="mt-3 w-full rounded-xl bg-primary-600 py-2 text-sm font-semibold text-white disabled:opacity-40"
            @click="addMembers"
          >
            افزودن {{ toAdd.length ? toAdd.length.toLocaleString('fa-IR') + ' نفر' : '' }}
          </button>
        </div>
        <div v-if="loading" class="py-6 text-center text-sm text-gray-500">در حال بارگذاری...</div>
        <ul v-else class="space-y-0.5">
          <li v-for="m in members" :key="m.id" class="group flex items-center gap-3 rounded-xl px-2 py-1.5 hover:bg-black/[0.03] dark:hover:bg-white/5">
            <ChatAvatar :src="m.avatar" :name="m.name" />
            <span class="min-w-0 flex-1">
              <span class="flex items-center gap-1.5 truncate text-sm font-medium text-gray-900 dark:text-white">
                {{ m.name }}
                <span v-if="m.is_teacher" class="rounded bg-accent-500/15 px-1.5 text-[10px] font-semibold text-accent-700 dark:text-accent-300">استاد</span>
              </span>
            </span>
            <button
              v-if="manage && isCustom && !m.is_teacher"
              type="button"
              class="rounded-lg p-1 text-gray-400 opacity-0 transition hover:text-red-600 group-hover:opacity-100"
              aria-label="حذف از گروه"
              @click="removeMember(m)"
            >
              <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </li>
        </ul>
      </section>

      <button v-if="manage && isCustom" type="button" class="w-full rounded-xl py-2.5 text-sm font-semibold text-red-600 ring-1 ring-red-500/30 hover:bg-red-500/10" @click="deleteGroup">
        حذف گروه
      </button>
    </div>
  </aside>
</template>

<style scoped>
.info-panel {
  animation: slide-in 0.25s cubic-bezier(0.22, 1, 0.36, 1);
}
@keyframes slide-in {
  from { opacity: 0; transform: translateX(-12px); }
}
</style>
