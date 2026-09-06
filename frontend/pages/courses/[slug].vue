<script setup lang="ts">
const route = useRoute()
const { request } = useApi()
const authStore = useAuthStore()

const { data: course } = await useAsyncData(`course-${route.params.slug}`, () =>
  request<any>(`/courses/${route.params.slug}/`)
)

useSeoMeta({
  title: () => `${course.value?.title ?? ''} | آموزش‌یار`,
  description: () => course.value?.subtitle || course.value?.description?.slice(0, 160),
  ogTitle: () => course.value?.title,
  ogType: 'product',
  ogImage: () => course.value?.cover_image,
})

useHead(() => ({
  script: course.value
    ? [
        {
          type: 'application/ld+json',
          innerHTML: JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'Course',
            name: course.value.title,
            description: course.value.description,
            provider: {
              '@type': 'Organization',
              name: 'آموزش‌یار',
            },
            offers: {
              '@type': 'Offer',
              price: course.value.effective_price,
              priceCurrency: 'IRR',
            },
          }),
        },
      ]
    : [],
}))

const firstVideoLessonId = computed(() =>
  course.value?.lessons?.find((l: any) => l.has_video)?.id
)

async function buyNow() {
  if (!authStore.isAuthenticated) {
    return navigateTo('/auth/login')
  }
  const order = await request<{ id: number }>('/payments/orders/', {
    method: 'POST',
    body: { course_ids: [course.value.id] },
  })
  const { redirect_url } = await request<{ redirect_url: string }>(
    `/payments/initiate/${order.id}/`,
    { method: 'POST' }
  )
  window.location.href = redirect_url
}
</script>

<template>
  <div v-if="course" class="mx-auto max-w-5xl px-4 py-10 sm:px-6 lg:px-8">
    <div class="grid grid-cols-1 gap-8 lg:grid-cols-3">
      <div class="lg:col-span-2">
        <h1 class="text-2xl font-bold text-gray-900 sm:text-3xl dark:text-white">{{ course.title }}</h1>
        <p class="mt-2 text-gray-600 dark:text-gray-300">{{ course.subtitle }}</p>
        <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">مدرس: {{ course.instructor_name }}</p>

        <p class="mt-6 whitespace-pre-line text-gray-700 dark:text-gray-200">{{ course.description }}</p>

        <h2 class="mt-8 text-lg font-semibold text-gray-900 dark:text-white">سرفصل‌ها</h2>
        <ul class="mt-3 divide-y divide-gray-200 rounded-md border border-gray-200 dark:divide-gray-800 dark:border-gray-800">
          <li
            v-for="lesson in course.lessons"
            :key="lesson.id"
            class="flex items-center justify-between px-4 py-3 text-sm"
          >
            <span class="text-gray-800 dark:text-gray-100">{{ lesson.title }}</span>
            <span v-if="lesson.is_free_preview" class="text-xs font-medium text-emerald-600">پیش‌نمایش رایگان</span>
          </li>
        </ul>
      </div>

      <div class="lg:col-span-1">
        <div class="rounded-lg border border-gray-200 p-4 dark:border-gray-800">
          <ClientOnly v-if="firstVideoLessonId">
            <VideoPlayer :video-id="firstVideoLessonId" :has-full-access="false">
              <template #cta>
                <button
                  class="rounded-md bg-accent-500 px-5 py-2 text-sm font-semibold text-white hover:bg-accent-400"
                  @click="buyNow"
                >
                  ثبت‌نام در دوره
                </button>
              </template>
            </VideoPlayer>
          </ClientOnly>

          <div class="mt-4 text-xl font-bold text-gray-900 dark:text-white">
            {{ Number(course.effective_price).toLocaleString('fa-IR') }} تومان
          </div>
          <button
            class="mt-4 w-full rounded-md bg-accent-500 px-4 py-2 text-sm font-semibold text-white hover:bg-accent-400"
            @click="buyNow"
          >
            ثبت‌نام در دوره
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
