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
    <div class="glass rounded-2xl p-6 sm:p-8">
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
          <div class="mt-2 flex flex-wrap items-center justify-center gap-x-3 gap-y-1 sm:justify-start">
            <InstructorRatingStars :rating="instructor.rating_avg" />
            <span class="text-sm text-gray-500 dark:text-gray-400">{{ instructor.total_students }} دانشجو</span>
          </div>
          <a
            v-if="instructor.phone_number"
            :href="`tel:${instructor.phone_number}`"
            class="mt-2 flex items-center justify-center gap-1.5 text-sm text-primary-600 hover:underline dark:text-primary-400 sm:justify-start"
          >
            <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" /></svg>
            {{ instructor.phone_number }}
          </a>
        </div>
      </div>

      <p class="mt-8 whitespace-pre-line text-gray-700 dark:text-gray-200">{{ instructor.bio }}</p>
    </div>
  </div>
</template>
