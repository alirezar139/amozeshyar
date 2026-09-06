<script setup lang="ts">
defineProps<{
  course: {
    slug: string
    title: string
    subtitle?: string
    cover_image?: string | null
    effective_price: number | string
    instructor_name?: string
    category_name?: string
  }
}>()

function formatPrice(value: number | string) {
  const n = Number(value)
  if (n === 0) return 'رایگان'
  return `${n.toLocaleString('fa-IR')} تومان`
}
</script>

<template>
  <NuxtLink
    :to="`/courses/${course.slug}`"
    class="glass group flex flex-col overflow-hidden rounded-xl transition hover:-translate-y-0.5 hover:shadow-lg"
  >
    <div class="relative aspect-video w-full overflow-hidden">
      <NuxtImg
        v-if="course.cover_image"
        :src="course.cover_image"
        :alt="course.title"
        class="h-full w-full object-cover transition group-hover:scale-105"
        loading="lazy"
      />
      <div v-else class="flex h-full w-full items-center justify-center bg-gradient-to-br from-primary-700 to-primary-950">
        <svg class="h-10 w-10 text-white/70" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
        </svg>
      </div>
    </div>
    <div class="flex flex-1 flex-col p-4">
      <span v-if="course.category_name" class="text-xs font-medium text-primary-600">{{ course.category_name }}</span>
      <h3 class="mt-1 line-clamp-2 text-base font-semibold text-gray-900 dark:text-white">{{ course.title }}</h3>
      <p v-if="course.instructor_name" class="mt-1 text-sm text-gray-500 dark:text-gray-400">
        {{ course.instructor_name }}
      </p>
      <div class="mt-auto pt-3 text-sm font-bold text-accent-600 dark:text-accent-400">
        {{ formatPrice(course.effective_price) }}
      </div>
    </div>
  </NuxtLink>
</template>
