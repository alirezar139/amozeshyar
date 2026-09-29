<script setup lang="ts">
// Message text with clickable links. Built from text nodes and <a> elements
// (no v-html), so whatever someone types can never become markup.
const props = defineProps<{ text: string; mine?: boolean }>()

const LINK = /(https?:\/\/[^\s<]+[^\s<.,;:!?)\]'"»،؛]|www\.[^\s<]+[^\s<.,;:!?)\]'"»،؛])/gi

const parts = computed(() => {
  const out: { text: string; href?: string }[] = []
  let last = 0
  for (const match of props.text.matchAll(LINK)) {
    const start = match.index ?? 0
    if (start > last) out.push({ text: props.text.slice(last, start) })
    const url = match[0]
    out.push({ text: url, href: url.startsWith('www.') ? `https://${url}` : url })
    last = start + url.length
  }
  if (last < props.text.length) out.push({ text: props.text.slice(last) })
  return out
})
</script>

<template>
  <p class="whitespace-pre-wrap break-words" dir="auto">
    <template v-for="(part, i) in parts" :key="i">
      <a
        v-if="part.href"
        :href="part.href"
        target="_blank"
        rel="noopener noreferrer nofollow"
        dir="ltr"
        :class="['break-all underline underline-offset-2', mine ? 'text-white decoration-white/60 hover:decoration-white' : 'text-primary-600 decoration-primary-400/60 hover:decoration-primary-600 dark:text-primary-300']"
        @click.stop
      >{{ part.text }}</a>
      <template v-else>{{ part.text }}</template>
    </template>
  </p>
</template>
