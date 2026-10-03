<script setup lang="ts">
// Logo + site name, as set in «تنظیمات سایت». Without an uploaded logo,
// the name's first letter on the header color stands in. The logo keeps its
// own aspect ratio (fixed height, auto width) — uploads are often wide.
withDefaults(defineProps<{ size?: 'md' | 'lg' }>(), { size: 'md' })
const { owner, siteName } = useSite()
</script>

<template>
  <span class="flex min-w-0 items-center gap-2.5">
    <img
      v-if="owner?.logo"
      :src="owner.logo"
      :alt="siteName"
      :class="['w-auto max-w-[9rem] shrink-0 rounded-lg object-contain', size === 'lg' ? 'h-14' : 'h-12']"
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
