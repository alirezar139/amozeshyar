<script setup lang="ts">
import type { StatusStyle } from '~/utils/sales'

const props = defineProps<{ map: Record<string, StatusStyle>; status: string }>()
const style = computed(() => statusOf(props.map, props.status))
</script>

<template>
  <span class="inline-block whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-semibold" :class="style.tone">
    {{ style.label }}
  </span>
</template>
