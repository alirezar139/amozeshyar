<script setup lang="ts">
// Colored badge with the file's extension — lets a list of handouts be scanned at a glance.
const props = defineProps<{ extension?: string; size?: 'sm' | 'md' }>()

const GROUPS: { match: string[]; class: string }[] = [
  { match: ['pdf'], class: 'bg-red-500' },
  { match: ['doc', 'docx', 'odt', 'rtf', 'txt', 'md'], class: 'bg-blue-600' },
  { match: ['ppt', 'pptx', 'odp'], class: 'bg-orange-500' },
  { match: ['xls', 'xlsx', 'csv', 'ods'], class: 'bg-emerald-600' },
  { match: ['zip', 'rar', '7z', 'tar', 'gz'], class: 'bg-amber-600' },
  { match: ['png', 'jpg', 'jpeg', 'webp', 'gif', 'psd', 'ai', 'fig', 'sketch'], class: 'bg-fuchsia-600' },
  { match: ['mp3', 'm4a', 'wav', 'ogg'], class: 'bg-violet-600' },
]

const ext = computed(() => (props.extension || '').toLowerCase())
const color = computed(() => GROUPS.find((g) => g.match.includes(ext.value))?.class ?? 'bg-slate-600')
</script>

<template>
  <span
    :class="[
      'relative flex shrink-0 items-end justify-center rounded-lg pb-1 font-bold uppercase text-white shadow-sm',
      color,
      size === 'sm' ? 'h-9 w-8 text-[8px]' : 'h-11 w-10 text-[9px]',
    ]"
    dir="ltr"
  >
    <!-- folded corner -->
    <span class="absolute end-0 top-0 h-2.5 w-2.5 rounded-bl-md bg-white/35" />
    {{ ext.slice(0, 4) || 'file' }}
  </span>
</template>
