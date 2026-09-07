<script setup lang="ts">
const { request } = useApi()

useSeoMeta({ title: 'مدرس‌ها | آموزش‌یار' })

const { data: instructors, pending } = await useAsyncData('instructors-list', async () => {
  const page = await request<{ results: any[] }>('/instructors/')
  return page.results
})
</script>

<template>
  <div class="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
    <h1 class="text-2xl font-bold text-gray-900 dark:text-white">مدرس‌های آموزش‌یار</h1>

    <div v-if="pending" class="mt-8 text-center text-gray-500">در حال بارگذاری...</div>
    <div v-else data-tour="instructor-grid" class="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
      <div
        v-for="instructor in instructors"
        :key="instructor.slug"
        class="glass flex h-full flex-col items-center rounded-lg p-4 text-center"
      >
        <InstructorRatingStars :rating="instructor.rating_avg" />
        <NuxtImg
          v-if="instructor.cover_image"
          :src="instructor.cover_image"
          class="mt-3 h-20 w-20 rounded-full object-cover"
        />
        <div v-else class="mt-3 flex h-20 w-20 items-center justify-center rounded-full bg-primary-100 text-xl font-bold text-primary-700 dark:bg-primary-900/40 dark:text-primary-300">
          {{ instructor.display_name?.[0] }}
        </div>
        <p class="mt-3 font-semibold text-gray-900 dark:text-white">{{ instructor.display_name }}</p>
        <p class="text-sm text-gray-500 dark:text-gray-400">{{ instructor.headline }}</p>
        <a
          v-if="instructor.phone_number"
          :href="`tel:${instructor.phone_number}`"
          class="mt-2 flex items-center gap-1.5 text-sm text-primary-600 hover:underline dark:text-primary-400"
          @click.stop
        >
          <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" /></svg>
          {{ instructor.phone_number }}
        </a>
        <NuxtLink
          :to="`/instructors/${instructor.slug}`"
          class="mt-auto w-full rounded-md bg-primary-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-primary-500"
        >
          مشاهده پروفایل مدرس
        </NuxtLink>
      </div>
    </div>
  </div>
</template>
