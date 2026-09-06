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
    <div class="aspect-video w-full overflow-hidden bg-gray-100 dark:bg-gray-800">
      <NuxtImg
        v-if="course.cover_image"
        :src="course.cover_image"
        :alt="course.title"
        class="h-full w-full object-cover transition group-hover:scale-105"
        loading="lazy"
      />
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
