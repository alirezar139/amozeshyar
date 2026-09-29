<script setup lang="ts">
// Lightweight emoji picker: a few curated categories, recently used first.
const emit = defineEmits<{ pick: [emoji: string] }>()

const CATEGORIES: { key: string; icon: string; label: string; emojis: string[] }[] = [
  {
    key: 'smileys', icon: '😊', label: 'چهره‌ها',
    emojis: ['😀', '😃', '😄', '😁', '😆', '😅', '😂', '🤣', '😊', '😇', '🙂', '😉', '😌', '😍', '🥰', '😘', '😋', '😎', '🤩', '🥳', '🤗', '🤔', '🤨', '😐', '😶', '🙄', '😏', '😮', '😯', '😲', '😴', '🤤', '😪', '😵', '🤐', '🥴', '😷', '🤒', '🤕', '😢', '😭', '😤', '😠', '😡', '🤯', '😳', '🥺', '😬', '🙏'],
  },
  {
    key: 'gestures', icon: '👍', label: 'دست‌ها',
    emojis: ['👍', '👎', '👌', '✌️', '🤞', '🤟', '🤘', '👏', '🙌', '👐', '🤲', '🤝', '✋', '👋', '💪', '✍️', '👀', '🧠', '🫡', '🤙', '☝️', '👇', '👉', '👈'],
  },
  {
    key: 'study', icon: '📚', label: 'درس و کار',
    emojis: ['📚', '📖', '📝', '✏️', '🖊️', '📌', '📎', '📅', '⏰', '🎓', '🏆', '🥇', '💡', '🔍', '💻', '🖥️', '📱', '🎧', '🎤', '📊', '📈', '✅', '❌', '❓', '❗', '⭐', '🌟', '🔥', '🚀', '🎯'],
  },
  {
    key: 'hearts', icon: '❤️', label: 'قلب‌ها',
    emojis: ['❤️', '🧡', '💛', '💚', '💙', '💜', '🤍', '🖤', '💖', '💗', '💝', '💯', '✨', '🎉', '🎊', '🌹', '🌷', '🌸', '🍀', '☕', '🍰', '🎁'],
  },
]

const RECENT_KEY = 'chat-recent-emojis'
const recent = ref<string[]>([])
onMounted(() => {
  try {
    recent.value = JSON.parse(localStorage.getItem(RECENT_KEY) || '[]').slice(0, 16)
  } catch {
    recent.value = []
  }
})

const active = ref(CATEGORIES[0].key)
const shown = computed(() => (active.value === 'recent' ? recent.value : CATEGORIES.find((c) => c.key === active.value)?.emojis ?? []))

function pick(emoji: string) {
  recent.value = [emoji, ...recent.value.filter((e) => e !== emoji)].slice(0, 16)
  try {
    localStorage.setItem(RECENT_KEY, JSON.stringify(recent.value))
  } catch {
    /* private mode — recents just won't persist */
  }
  emit('pick', emoji)
}
</script>

<template>
  <div class="w-72 overflow-hidden rounded-2xl bg-white shadow-2xl ring-1 ring-black/10 dark:bg-gray-800 dark:ring-white/10">
    <div class="flex gap-1 border-b border-black/5 p-1.5 dark:border-white/10">
      <button
        v-if="recent.length"
        type="button"
        :class="['flex h-8 flex-1 items-center justify-center rounded-lg text-base transition', active === 'recent' ? 'bg-primary-500/15' : 'hover:bg-black/5 dark:hover:bg-white/10']"
        title="اخیر"
        @click="active = 'recent'"
      >
        🕘
      </button>
      <button
        v-for="c in CATEGORIES"
        :key="c.key"
        type="button"
        :class="['flex h-8 flex-1 items-center justify-center rounded-lg text-base transition', active === c.key ? 'bg-primary-500/15' : 'hover:bg-black/5 dark:hover:bg-white/10']"
        :title="c.label"
        @click="active = c.key"
      >
        {{ c.icon }}
      </button>
    </div>
    <div class="grid max-h-56 grid-cols-8 gap-0.5 overflow-y-auto p-2">
      <button
        v-for="e in shown"
        :key="e"
        type="button"
        class="flex h-8 w-8 items-center justify-center rounded-lg text-xl transition hover:scale-125 hover:bg-black/5 dark:hover:bg-white/10"
        @click="pick(e)"
      >
        {{ e }}
      </button>
    </div>
  </div>
</template>
