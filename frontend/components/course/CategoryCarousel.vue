<script setup lang="ts">
const props = defineProps<{
  categories: { slug: string; name: string; image?: string | null; course_count: number }[]
}>()

const active = ref(0)
const paused = ref(false)
let timer: ReturnType<typeof setInterval> | null = null

function goTo(i: number) {
  active.value = (i + props.categories.length) % props.categories.length
}
function next() {
  goTo(active.value + 1)
}
function prev() {
  goTo(active.value - 1)
}

function startAuto() {
  stopAuto()
  timer = setInterval(() => {
    if (!paused.value) next()
  }, 5000)
}
function stopAuto() {
  if (timer) clearInterval(timer)
  timer = null
}

onMounted(startAuto)
onUnmounted(stopAuto)
</script>

<template>
  <div
    class="group/carousel relative overflow-hidden rounded-2xl"
    @mouseenter="paused = true"
    @mouseleave="paused = false"
  >
    <div
      class="flex transition-transform duration-500 ease-out"
      style="direction: ltr"
      :style="{ transform: `translateX(-${active * 100}%)` }"
    >
      <NuxtLink
        v-for="category in categories"
        :key="category.slug"
        :to="`/courses?category=${category.slug}`"
        class="relative flex h-40 w-full shrink-0 items-end sm:h-52 lg:h-60"
      >
        <NuxtImg
          v-if="category.image"
          :src="category.image"
          :alt="category.name"
          class="absolute inset-0 h-full w-full object-cover"
          loading="lazy"
        />
        <div v-else class="absolute inset-0 bg-gradient-to-br from-primary-700 to-primary-950" />
        <div class="absolute inset-0 bg-gradient-to-t from-black/80 via-black/10 to-transparent" />
        <div class="relative z-10 p-6 text-white" style="direction: rtl">
          <p class="text-2xl font-bold">{{ category.name }}</p>
          <p class="mt-1 text-sm text-white/80">{{ category.course_count }} دوره</p>
        </div>
      </NuxtLink>
    </div>

    <!-- Manual controls — always visible, not hover-only, since this is meant to be selectable -->
    <button
      type="button"
      aria-label="دسته‌بندی قبلی"
      class="glass absolute right-3 top-1/2 z-20 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-full text-white"
      @click.prevent="prev"
    >
      ‹
    </button>
    <button
      type="button"
      aria-label="دسته‌بندی بعدی"
      class="glass absolute left-3 top-1/2 z-20 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-full text-white"
      @click.prevent="next"
    >
      ›
    </button>

    <div class="absolute inset-x-0 bottom-3 z-20 flex justify-center gap-2">
      <button
        v-for="(category, i) in categories"
        :key="category.slug"
        type="button"
        :aria-label="`رفتن به ${category.name}`"
        class="h-2 rounded-full transition-all"
        :class="i === active ? 'w-6 bg-white' : 'w-2 bg-white/50'"
        @click.prevent="goTo(i)"
      />
    </div>
  </div>
</template>
