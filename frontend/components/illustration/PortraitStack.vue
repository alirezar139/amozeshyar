<script setup lang="ts">
// The instructor's portrait on a small stack of "pages": two colored cards
// behind it swing out to either side and back while the front card floats,
// and hovering fans them out further. Used by the homepage hero and the
// live preview on the site settings page, so both always match.
defineProps<{
  src?: string | null
  alt?: string
  size?: 'lg' | 'sm'
}>()
</script>

<template>
  <div :class="['portrait-stack group relative', size === 'sm' ? 'is-sm' : '']">
    <div class="page page-back absolute inset-0 bg-gradient-to-br from-accent-400 to-accent-600 opacity-70" />
    <div class="page page-mid absolute inset-0 bg-gradient-to-br from-primary-500 to-primary-700 opacity-85" />
    <div class="page page-front relative overflow-hidden bg-gray-100 shadow-2xl ring-1 ring-black/5 dark:bg-gray-800 dark:ring-white/10">
      <img v-if="src" :src="src" :alt="alt ?? ''" class="aspect-[4/5] w-full object-cover object-top">
      <IllustrationTeachingScene v-else class="aspect-[4/5] w-full !rounded-none !p-3 !shadow-none" />
    </div>
  </div>
</template>

<style scoped>
.page {
  border-radius: 2.5rem;
  transform-origin: 50% 90%;
  transition: transform 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.is-sm .page {
  border-radius: 1.75rem;
}

.page-back {
  animation: swing-left 6s ease-in-out infinite;
}
.page-mid {
  animation: swing-right 6s ease-in-out infinite;
}
.page-front {
  animation: float 6s ease-in-out infinite;
}

/* Hover: pause the loop and fan the pages out */
.portrait-stack:hover .page {
  animation-play-state: paused;
}
.portrait-stack:hover .page-back {
  transform: rotate(-14deg) translateX(-8%);
}
.portrait-stack:hover .page-mid {
  transform: rotate(12deg) translateX(8%);
}
.portrait-stack:hover .page-front {
  transform: translateY(-6px) scale(1.02);
}

@keyframes swing-left {
  0%, 100% { transform: rotate(-3deg) translateX(0); }
  50% { transform: rotate(-10deg) translateX(-5%); }
}
@keyframes swing-right {
  0%, 100% { transform: rotate(4deg) translateX(0); }
  50% { transform: rotate(9deg) translateX(5%); }
}
@keyframes float {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  25% { transform: translateY(-6px) rotate(-1deg); }
  75% { transform: translateY(-3px) rotate(1deg); }
}

@media (prefers-reduced-motion: reduce) {
  .page {
    animation: none !important;
    transition: none;
  }
  .page-back { transform: rotate(-6deg); }
  .page-mid { transform: rotate(6deg); }
}
</style>
