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
    <div v-else class="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
      <NuxtLink
        v-for="instructor in instructors"
        :key="instructor.slug"
        :to="`/instructors/${instructor.slug}`"
        class="rounded-lg border border-gray-200 p-4 text-center hover:shadow-lg dark:border-gray-800"
      >
        <NuxtImg
          v-if="instructor.cover_image"
          :src="instructor.cover_image"
          class="mx-auto h-20 w-20 rounded-full object-cover"
        />
        <p class="mt-3 font-semibold text-gray-900 dark:text-white">{{ instructor.display_name }}</p>
        <p class="text-sm text-gray-500 dark:text-gray-400">{{ instructor.headline }}</p>
      </NuxtLink>
    </div>
  </div>
</template>
