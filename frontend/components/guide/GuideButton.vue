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
    <svg class="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
      <path stroke-linecap="round" stroke-linejoin="round" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  </button>
</template>
