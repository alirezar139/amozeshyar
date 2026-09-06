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

const videoLessons = computed(() => (course.value?.lessons ?? []).filter((l: any) => l.has_video))

// Default to whichever lesson the student is mid-way through (if any),
// otherwise the first watchable one — matches the "continue" flow used
// on the dashboard.
const activeLessonId = ref<number | null>(null)

watchEffect(() => {
  if (activeLessonId.value !== null || !videoLessons.value.length) return
  const inProgress = videoLessons.value.find((l: any) => l.progress_seconds > 0 && !l.completed)
  activeLessonId.value = (inProgress ?? videoLessons.value[0]).id
})

const activeLesson = computed(() => videoLessons.value.find((l: any) => l.id === activeLessonId.value))

// A lesson's own video can always be selected — locked lessons just play
// a short teaser (via the preview endpoint) instead of the full manifest.
// Only enrollment or the lesson's own `is_free_preview` flag unlocks full
// playback for it.
function hasFullAccessTo(lesson: any) {
  return !!(course.value?.is_enrolled || lesson.is_free_preview)
}

function selectLesson(lesson: any) {
  if (!lesson.has_video) return
  activeLessonId.value = lesson.id
}

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
        <ul class="glass mt-3 divide-y divide-white/30 rounded-md dark:divide-white/10">
          <li
            v-for="lesson in course.lessons"
            :key="lesson.id"
            class="flex items-center justify-between px-4 py-3 text-sm transition"
            :class="[
              lesson.has_video ? 'cursor-pointer hover:bg-white/40 dark:hover:bg-white/5' : '',
              activeLessonId === lesson.id ? 'bg-white/50 dark:bg-white/10' : '',
            ]"
            @click="selectLesson(lesson)"
          >
            <span class="flex items-center gap-2 text-gray-800 dark:text-gray-100">
              <svg v-if="lesson.completed" class="h-4 w-4 shrink-0 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" /></svg>
              <svg v-else-if="lesson.has_video && !hasFullAccessTo(lesson)" class="h-4 w-4 shrink-0 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" /></svg>
              {{ lesson.title }}
            </span>
            <span v-if="lesson.is_free_preview && !course.is_enrolled" class="text-xs font-medium text-emerald-600">پیش‌نمایش رایگان</span>
          </li>
        </ul>
      </div>

      <div class="lg:col-span-1">
        <div class="glass rounded-lg p-4">
          <ClientOnly v-if="activeLesson">
            <PlayerVideoPlayer
              :key="activeLesson.video_id"
              :video-id="activeLesson.video_id"
              :lesson-id="activeLesson.id"
              :has-full-access="hasFullAccessTo(activeLesson)"
              :initial-position="activeLesson.progress_seconds"
            >
              <template #cta>
                <button
                  class="rounded-md bg-accent-500 px-5 py-2 text-sm font-semibold text-white hover:bg-accent-400"
                  @click="buyNow"
                >
                  ثبت‌نام در دوره
                </button>
              </template>
            </PlayerVideoPlayer>
          </ClientOnly>

          <div class="mt-4 text-xl font-bold text-gray-900 dark:text-white">
            {{ Number(course.effective_price).toLocaleString('fa-IR') }} تومان
          </div>
          <p v-if="course.is_enrolled" class="mt-4 rounded-md bg-emerald-500/10 px-4 py-2 text-center text-sm font-semibold text-emerald-600">
            شما در این دوره ثبت‌نام کرده‌اید
          </p>
          <button
            v-else
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
