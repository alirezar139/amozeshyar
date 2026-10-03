<script setup lang="ts">
// Images and audio clips attached to a question, an answer key or a
// student's answer. Images open full size in a new tab.
interface Media { id: number; kind: 'image' | 'audio'; url: string | null; name: string; duration_seconds?: number | null }
defineProps<{ items: Media[]; removable?: boolean }>()
const emit = defineEmits<{ remove: [id: number] }>()
</script>

<template>
  <div v-if="items.length" class="flex flex-wrap items-start gap-3">
    <div v-for="item in items" :key="item.id" class="relative">
      <a v-if="item.kind === 'image' && item.url" :href="item.url" target="_blank" rel="noopener" class="block overflow-hidden rounded-xl ring-1 ring-black/10 dark:ring-white/10">
        <img :src="item.url" :alt="item.name" class="max-h-56 max-w-full object-contain sm:max-w-sm" loading="lazy">
      </a>
      <div v-else-if="item.kind === 'audio' && item.url" class="w-64 rounded-xl bg-black/[0.04] px-3 py-2 dark:bg-white/5">
        <ChatVoicePlayer :src="item.url" :duration="item.duration_seconds" />
      </div>
      <button
        v-if="removable"
        type="button"
        class="absolute -end-2 -top-2 flex h-6 w-6 items-center justify-center rounded-full bg-red-600 text-xs text-white shadow"
        aria-label="حذف"
        @click="emit('remove', item.id)"
      >
        ✕
      </button>
    </div>
  </div>
</template>
