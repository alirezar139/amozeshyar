<script setup lang="ts">
const route = useRoute()
const { request } = useApi()
const authStore = useAuthStore()

const { data: course } = await useAsyncData(`course-${route.params.slug}`, () =>
  request<any>(`/courses/${route.params.slug}/`)
)

const { owner, siteName, teacherName } = useSite()

const levelLabels: Record<string, string> = { beginner: 'مقدماتی', intermediate: 'متوسط', advanced: 'پیشرفته' }
const lessonCount = computed(() => course.value?.lessons?.length ?? 0)
const durationLabel = computed(() => {
  const total = Number(course.value?.total_duration_seconds) || 0
  if (!total) return ''
  const hours = Math.floor(total / 3600)
  const minutes = Math.round((total % 3600) / 60)
  return [hours && `${hours.toLocaleString('fa-IR')} ساعت`, minutes && `${minutes.toLocaleString('fa-IR')} دقیقه`]
    .filter(Boolean)
    .join(' و ')
})
const hasDiscount = computed(
  () => course.value?.discount_price != null && Number(course.value.discount_price) < Number(course.value.price),
)

useSeoMeta({
  title: () => `${course.value?.title ?? ''} | ${siteName.value}`,
  description: () => course.value?.subtitle || course.value?.description?.slice(0, 160),
  ogTitle: () => course.value?.title,
  // Facebook's "product" type; unhead's typings only list Open Graph's core types.
  ogType: 'product' as unknown as 'website',
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
              '@type': 'Person',
              name: teacherName.value,
            },
            offers: {
              '@type': 'Offer',
              // Prices are stored in Toman; schema.org wants the ISO currency (Rial).
              price: Number(course.value.effective_price) * 10,
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

const { openLogin } = useAuthModal()
const couponCode = ref('')
const buying = ref(false)
const buyError = ref('')

// A free course (or a 100% coupon) comes back from /orders/ already paid,
// so the student is enrolled on the spot and never sees the gateway.
async function buyNow() {
  if (!authStore.isAuthenticated) {
    openLogin()
    return
  }
  if (buying.value) return
  buying.value = true
  buyError.value = ''
  try {
    const body: Record<string, unknown> = { course_ids: [course.value.id] }
    if (couponCode.value.trim()) body.coupon_code = couponCode.value.trim()
    const order = await request<{ id: number; status: string }>('/payments/orders/', { method: 'POST', body })
    if (order.status === 'paid') {
      await navigateTo(`/checkout/callback?order_id=${order.id}&status=paid`)
      return
    }
    const { redirect_url } = await request<{ redirect_url: string }>(
      `/payments/initiate/${order.id}/`,
      { method: 'POST' }
    )
    window.location.href = redirect_url
  } catch (error) {
    buyError.value = getFirstErrorMessage(error, 'ثبت سفارش انجام نشد. لطفاً دوباره تلاش کنید.')
    buying.value = false
  }
}
</script>

<template>
  <div v-if="course" class="mx-auto max-w-5xl px-4 py-10 sm:px-6 lg:px-8">
    <div class="grid grid-cols-1 gap-8 lg:grid-cols-3">
      <div class="lg:col-span-2">
        <img
          v-if="course.cover_image"
          :src="course.cover_image"
          :alt="course.title"
          class="mb-6 aspect-video w-full rounded-2xl object-cover shadow-lg ring-1 ring-black/5 dark:ring-white/10"
        >
        <h1 class="text-2xl font-bold text-gray-900 sm:text-3xl dark:text-white">{{ course.title }}</h1>
        <p v-if="course.subtitle" class="mt-2 text-gray-600 dark:text-gray-300">{{ course.subtitle }}</p>

        <ul class="mt-4 flex flex-wrap gap-2 text-xs font-medium">
          <li v-if="course.category_name" class="glass rounded-full px-3 py-1 text-gray-700 dark:text-gray-200">{{ course.category_name }}</li>
          <li v-if="levelLabels[course.level]" class="glass rounded-full px-3 py-1 text-gray-700 dark:text-gray-200">سطح {{ levelLabels[course.level] }}</li>
          <li v-if="lessonCount" class="glass rounded-full px-3 py-1 text-gray-700 dark:text-gray-200">{{ lessonCount.toLocaleString('fa-IR') }} جلسه</li>
          <li v-if="durationLabel" class="glass rounded-full px-3 py-1 text-gray-700 dark:text-gray-200">{{ durationLabel }}</li>
        </ul>

        <p v-if="course.description" class="mt-6 whitespace-pre-line leading-8 text-gray-700 dark:text-gray-200">{{ course.description }}</p>

        <h2 class="mt-8 text-lg font-semibold text-gray-900 dark:text-white">سرفصل‌ها</h2>
        <p v-if="!lessonCount" class="glass mt-3 rounded-md px-4 py-6 text-center text-sm text-gray-600 dark:text-gray-300">
          سرفصل‌های این دوره به‌زودی اضافه می‌شوند.
        </p>
        <ul v-else data-tour="lesson-list" class="glass mt-3 divide-y divide-white/30 rounded-md dark:divide-white/10">
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

          <div class="mt-4 flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <span class="text-xl font-bold text-gray-900 dark:text-white">
              <template v-if="Number(course.effective_price) > 0">{{ Number(course.effective_price).toLocaleString('fa-IR') }} تومان</template>
              <template v-else>رایگان</template>
            </span>
            <span v-if="hasDiscount" class="text-sm text-gray-500 line-through dark:text-gray-400">
              {{ Number(course.price).toLocaleString('fa-IR') }}
            </span>
          </div>
          <template v-if="course.is_enrolled">
            <p class="mt-4 rounded-md bg-emerald-500/10 px-4 py-2 text-center text-sm font-semibold text-emerald-600">
              شما در این دوره ثبت‌نام کرده‌اید
            </p>
            <NuxtLink
              :to="`/dashboard/courses/${course.slug}`"
              data-tour="course-enter"
              class="mt-3 block w-full rounded-md bg-primary-600 px-4 py-2 text-center text-sm font-semibold text-white hover:bg-primary-500"
            >
              ورود به دوره
            </NuxtLink>
          </template>
          <template v-else>
            <input
              v-if="Number(course.effective_price) > 0"
              v-model="couponCode"
              type="text"
              dir="ltr"
              placeholder="کد تخفیف (اختیاری)"
              class="glass mt-4 block w-full rounded-md px-3 py-2 text-center text-sm text-gray-900 placeholder:text-gray-400 dark:text-white"
              @keyup.enter="buyNow"
            >
            <button
              data-tour="course-buy-cta"
              :disabled="buying"
              class="mt-3 w-full rounded-md bg-accent-500 px-4 py-2 text-sm font-semibold text-white hover:bg-accent-400 disabled:cursor-wait disabled:opacity-60"
              @click="buyNow"
            >
              {{ buying ? 'در حال انتقال...' : Number(course.effective_price) > 0 ? 'ثبت‌نام در دوره' : 'ثبت‌نام رایگان' }}
            </button>
            <p v-if="buyError" class="mt-2 text-center text-xs text-red-600 dark:text-red-400">{{ buyError }}</p>
          </template>
        </div>

        <NuxtLink v-if="owner" to="/" class="glass mt-4 flex items-center gap-3 rounded-lg p-4 transition hover:-translate-y-0.5">
          <img v-if="owner.avatar" :src="owner.avatar" :alt="teacherName" class="h-12 w-12 shrink-0 rounded-full object-cover">
          <span v-else class="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-primary-600 font-bold text-white">
            {{ teacherName[0] }}
          </span>
          <span class="min-w-0">
            <span class="block text-xs text-gray-500 dark:text-gray-400">مدرس دوره</span>
            <span class="block truncate font-semibold text-gray-900 dark:text-white">{{ teacherName }}</span>
            <span v-if="owner.headline" class="block truncate text-xs text-gray-600 dark:text-gray-300">{{ owner.headline }}</span>
          </span>
        </NuxtLink>
      </div>
    </div>
  </div>
</template>
