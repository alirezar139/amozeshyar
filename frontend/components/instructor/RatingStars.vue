<script setup lang="ts">
const props = defineProps<{ rating: number | string }>()
const rounded = computed(() => Math.round(Number(props.rating) || 0))
</script>

<template>
  <div class="flex items-center gap-0.5" :title="`امتیاز ${rating} از ۵`">
    <svg
      v-for="i in 5"
      :key="i"
      class="h-4 w-4"
      :class="i <= rounded ? 'text-amber-400' : 'text-gray-300 dark:text-gray-600'"
      fill="currentColor"
      viewBox="0 0 20 20"
    >
      <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.286 3.958a1 1 0 00.95.69h4.162c.969 0 1.371 1.24.588 1.81l-3.368 2.447a1 1 0 00-.363 1.118l1.287 3.957c.3.922-.755 1.688-1.538 1.118l-3.367-2.447a1 1 0 00-1.176 0l-3.367 2.447c-.783.57-1.838-.196-1.538-1.118l1.287-3.957a1 1 0 00-.363-1.118L2.063 9.385c-.783-.57-.38-1.81.588-1.81h4.163a1 1 0 00.95-.69l1.285-3.958z" />
    </svg>
  </div>
</template>
