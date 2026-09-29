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
    <div class="page page-front relative shadow-2xl">
      <div class="page-clip bg-gray-100 dark:bg-gray-800">
        <img v-if="src" :src="src" :alt="alt ?? ''" class="aspect-[4/5] w-full object-cover object-top">
        <IllustrationTeachingScene v-else class="aspect-[4/5] w-full !rounded-none !border-0 !bg-transparent !p-3 !shadow-none !backdrop-blur-none" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.portrait-stack {
  --radius: 2.5rem;
}
.portrait-stack.is-sm {
  --radius: 1.75rem;
}
.page {
  border-radius: var(--radius);
  transform-origin: 50% 90%;
  transition: transform 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
}
/* clip-path, not overflow:hidden: Chrome stops honoring border-radius
   clipping on a transformed parent when a child has backdrop-filter
   (the illustration's glass), which let square corners show through. */
.page-clip {
  clip-path: inset(0 round var(--radius));
  box-shadow: inset 0 0 0 1px rgb(0 0 0 / 0.05);
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
