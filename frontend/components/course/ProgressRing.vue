<script setup lang="ts">
const props = withDefaults(defineProps<{ percent: number; size?: number; stroke?: number }>(), { size: 56, stroke: 6 })
const radius = computed(() => (props.size - props.stroke) / 2)
const circumference = computed(() => 2 * Math.PI * radius.value)
const offset = computed(() => circumference.value * (1 - Math.min(100, Math.max(0, props.percent)) / 100))
</script>

<template>
  <span class="relative inline-flex shrink-0 items-center justify-center" :style="{ width: `${size}px`, height: `${size}px` }">
    <svg :width="size" :height="size" class="-rotate-90">
      <circle :cx="size / 2" :cy="size / 2" :r="radius" fill="none" :stroke-width="stroke" class="stroke-black/5 dark:stroke-white/10" />
      <circle
        :cx="size / 2"
        :cy="size / 2"
        :r="radius"
        fill="none"
        :stroke-width="stroke"
        stroke-linecap="round"
        class="stroke-primary-500 transition-[stroke-dashoffset] duration-700"
        :stroke-dasharray="circumference"
        :stroke-dashoffset="offset"
      />
    </svg>
    <span class="absolute text-xs font-bold text-gray-900 dark:text-white">
      <slot>{{ Math.round(percent).toLocaleString('fa-IR') }}٪</slot>
    </span>
  </span>
</template>
