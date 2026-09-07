<script setup lang="ts">
const { isOpen, isTouring, open, close } = useGuide()

function toggle() {
  if (isTouring.value) return
  isOpen.value ? close() : open()
}
</script>

<template>
  <button
    v-if="!isTouring"
    type="button"
    aria-label="راهنما"
    title="راهنما"
    class="glass fixed bottom-8 start-8 z-[80] flex h-16 w-16 items-center justify-center rounded-full text-primary-700 shadow-lg transition hover:-translate-y-0.5 dark:text-primary-300"
    @click="toggle"
  >
    <svg class="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.6">
      <circle cx="12" cy="12" r="9" />
      <path stroke-linecap="round" stroke-linejoin="round" fill="currentColor" stroke-width="0.5" d="M15.5 8.5l-2.1 5.1-5.1 2.1 2.1-5.1 5.1-2.1z" />
    </svg>
  </button>
</template>
