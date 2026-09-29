<script setup lang="ts">
// Logo + site name, as set in «تنظیمات سایت». Without an uploaded logo,
// the name's first letter on the header color stands in.
withDefaults(defineProps<{ size?: 'md' | 'lg' }>(), { size: 'md' })
const { owner, siteName } = useSite()
</script>

<template>
  <span class="flex min-w-0 items-center gap-2.5">
    <img
      v-if="owner?.logo"
      :src="owner.logo"
      :alt="siteName"
      :class="['shrink-0 object-contain', size === 'lg' ? 'h-11 w-11' : 'h-9 w-9']"
    >
    <span
      v-else
      :class="[
        'flex shrink-0 items-center justify-center rounded-xl bg-header-600 font-extrabold text-white',
        size === 'lg' ? 'h-11 w-11 text-lg' : 'h-9 w-9 text-sm',
      ]"
    >
      {{ siteName[0] }}
    </span>
    <span :class="['truncate font-bold text-header-700 dark:text-header-400', size === 'lg' ? 'text-xl' : 'text-lg sm:text-xl']">
      {{ siteName }}
    </span>
  </span>
</template>
