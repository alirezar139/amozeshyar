<script setup lang="ts">
defineProps<{ src?: string | null; name: string; group?: boolean; size?: 'md' | 'lg' }>()
</script>

<template>
  <span :class="['relative shrink-0', size === 'lg' ? 'h-12 w-12' : 'h-10 w-10']">
    <img v-if="src" :src="src" :alt="name" class="h-full w-full rounded-full object-cover object-top">
    <span
      v-else
      :class="[
        'flex h-full w-full items-center justify-center rounded-full font-bold text-white',
        group ? 'bg-gradient-to-br from-accent-500 to-accent-700' : 'bg-gradient-to-br from-primary-500 to-primary-700',
      ]"
    >
      <svg v-if="group" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M17 20h5v-2a4 4 0 00-3-3.87M9 20H4v-2a4 4 0 013-3.87m6-4.13a4 4 0 10-4-4 4 4 0 004 4zm6 0a4 4 0 10-4-4" /></svg>
      <template v-else>{{ name?.[0] }}</template>
    </span>
  </span>
</template>
