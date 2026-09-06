<script setup lang="ts">
const route = useRoute()
const { request } = useApi()

const { data: instructor } = await useAsyncData(`instructor-${route.params.slug}`, () =>
  request<any>(`/instructors/${route.params.slug}/`)
)

useSeoMeta({
  title: () => `${instructor.value?.display_name ?? ''} | آموزش‌یار`,
  description: () => instructor.value?.headline,
})

useHead(() => ({
  script: instructor.value
    ? [
        {
          type: 'application/ld+json',
          innerHTML: JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'Person',
            name: instructor.value.display_name,
            description: instructor.value.bio,
          }),
        },
      ]
    : [],
}))
</script>

<template>
  <div v-if="instructor" class="mx-auto max-w-4xl px-4 py-10 sm:px-6 lg:px-8">
    <div class="flex flex-col items-center gap-4 text-center sm:flex-row sm:items-start sm:gap-6 sm:text-start">
      <NuxtImg
        v-if="instructor.cover_image"
        :src="instructor.cover_image"
        :alt="instructor.display_name"
        class="h-28 w-28 shrink-0 rounded-full object-cover"
      />
      <div>
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white">{{ instructor.display_name }}</h1>
        <p class="mt-1 text-gray-600 dark:text-gray-300">{{ instructor.headline }}</p>
        <p class="mt-2 text-sm text-gray-500 dark:text-gray-400">
          {{ instructor.total_students }} دانشجو &middot; امتیاز {{ instructor.rating_avg }}
        </p>
      </div>
    </div>

    <p class="mt-8 whitespace-pre-line text-gray-700 dark:text-gray-200">{{ instructor.bio }}</p>
  </div>
</template>
