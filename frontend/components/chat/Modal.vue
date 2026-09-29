<script setup lang="ts">
defineProps<{ title: string; wide?: boolean }>()
const emit = defineEmits<{ close: [] }>()
function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close')
}
onMounted(() => document.addEventListener('keydown', onKey))
onBeforeUnmount(() => document.removeEventListener('keydown', onKey))
</script>

<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-[70] flex items-end justify-center bg-black/40 p-0 backdrop-blur-sm sm:items-center sm:p-4" @click.self="emit('close')">
      <div :class="['modal-card flex max-h-[88vh] w-full flex-col overflow-hidden rounded-t-3xl bg-white shadow-2xl sm:rounded-3xl dark:bg-gray-900', wide ? 'sm:max-w-lg' : 'sm:max-w-md']">
        <header class="flex items-center justify-between border-b border-black/5 px-5 py-4 dark:border-white/10">
          <h3 class="text-lg font-bold text-gray-900 dark:text-white">{{ title }}</h3>
          <button type="button" class="rounded-full p-1.5 text-gray-400 hover:bg-black/5 hover:text-gray-700 dark:hover:bg-white/10" aria-label="بستن" @click="emit('close')">
            <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </header>
        <div class="min-h-0 flex-1 overflow-y-auto">
          <slot />
        </div>
        <footer v-if="$slots.footer" class="border-t border-black/5 px-5 py-3 dark:border-white/10">
          <slot name="footer" />
        </footer>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.modal-card {
  animation: modal-in 0.22s cubic-bezier(0.22, 1, 0.36, 1);
}
@keyframes modal-in {
  from { opacity: 0; transform: translateY(16px) scale(0.98); }
}
</style>
