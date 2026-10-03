<script setup lang="ts">
// Dev-only corner panel listing the errors caught on this page (see
// plugins/live-log.client.ts). Collapsed to a badge until something fails.
const { entries } = useLiveLog()
const open = ref(false)
const unseen = ref(0)
const expanded = ref<number | null>(null)

watch(() => entries.value.length, (n, old) => {
  if (n > (old ?? 0) && !open.value) unseen.value += n - (old ?? 0)
})

function toggle() {
  open.value = !open.value
  if (open.value) unseen.value = 0
}

const KIND: Record<string, string> = { js: 'JS', promise: 'Promise', vue: 'Vue', api: 'API' }
</script>

<template>
  <div class="fixed bottom-3 start-3 z-[200] text-start" dir="ltr">
    <div v-if="open" class="mb-2 max-h-[60vh] w-[min(36rem,calc(100vw-1.5rem))] overflow-y-auto rounded-2xl bg-gray-950/95 p-2 font-mono text-xs text-gray-100 shadow-2xl ring-1 ring-white/10">
      <div class="flex items-center justify-between px-2 py-1">
        <span class="font-sans font-bold">Live log · {{ entries.length }}</span>
        <button type="button" class="rounded px-2 py-0.5 font-sans text-gray-400 hover:bg-white/10" @click="entries = []">Clear</button>
      </div>
      <p v-if="!entries.length" class="px-2 py-4 text-center font-sans text-gray-500">No errors on this page.</p>
      <button
        v-for="e in entries"
        :key="e.id"
        type="button"
        class="block w-full rounded-lg px-2 py-1.5 text-start hover:bg-white/5"
        @click="expanded = expanded === e.id ? null : e.id"
      >
        <span :class="['me-1.5 rounded px-1 text-[10px] font-bold', e.level === 'error' ? 'bg-red-600' : 'bg-amber-500 text-black']">{{ KIND[e.kind] }}</span>
        <span class="text-gray-500">{{ e.at }}</span>
        <span class="mt-0.5 block break-words" dir="auto">{{ e.message }}</span>
        <pre v-if="expanded === e.id && e.detail" class="mt-1 whitespace-pre-wrap break-words text-[11px] text-gray-400" dir="auto">{{ e.detail }}</pre>
      </button>
    </div>
    <button
      type="button"
      :class="[
        'flex h-9 items-center gap-1.5 rounded-full px-3 font-sans text-xs font-bold text-white shadow-lg transition',
        unseen ? 'animate-pulse bg-red-600' : 'bg-gray-800/80 hover:bg-gray-800',
      ]"
      title="Live error log (dev only)"
      @click="toggle"
    >
      🐞 <span v-if="unseen">{{ unseen }}</span>
    </button>
  </div>
</template>
