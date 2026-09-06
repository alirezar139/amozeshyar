<script setup lang="ts">
const { request } = useApi()

useSeoMeta({
  title: 'آموزش‌یار | یادگیری آنلاین از بهترین مدرس‌ها',
  description: 'دوره‌های آموزشی تخصصی با پیش‌نمایش رایگان. مدرس‌های برتر را کشف کنید و همین امروز یادگیری را شروع کنید.',
  ogTitle: 'آموزش‌یار',
  ogDescription: 'دوره‌های آموزشی تخصصی با پیش‌نمایش رایگان.',
  ogType: 'website',
})

const { data: featuredInstructors } = await useAsyncData('home-featured-instructors', async () => {
  const page = await request<{ results: any[] }>('/instructors/')
  return page.results.slice(0, 3)
})

const { data: featuredCourses } = await useAsyncData('home-featured-courses', async () => {
  const page = await request<{ results: any[] }>('/courses/')
  return page.results.slice(0, 4)
})
</script>

<template>
  <div class="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
    <!-- Hero: one large glass panel, gradient body shows through -->
    <section class="glass overflow-hidden rounded-3xl">
      <div class="grid grid-cols-1 items-center gap-10 p-8 sm:p-12 lg:grid-cols-2 lg:p-16">
        <div>
          <span class="glass inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold text-primary-800 dark:text-primary-300">
            <span class="h-1.5 w-1.5 rounded-full bg-primary-500" />
            پلتفرم آموزش آنلاین
          </span>
          <h1 class="mt-5 text-4xl font-extrabold leading-[1.15] tracking-tight text-gray-900 sm:text-5xl dark:text-white">
            یاد بگیر از کسانی که
            <span class="relative inline-block text-primary-700 dark:text-primary-300">بلدن</span>
          </h1>
          <p class="mt-5 max-w-lg text-base leading-7 text-gray-700 sm:text-lg dark:text-gray-300">
            دوره‌های تخصصی با پیش‌نمایش رایگان — قبل از خرید، خودتان کیفیت تدریس را ببینید.
          </p>
          <div class="mt-8 flex flex-col gap-3 sm:flex-row">
            <NuxtLink
              to="/courses"
              class="rounded-lg bg-primary-600 px-7 py-3 text-center text-sm font-semibold text-white shadow-lg shadow-primary-600/30 transition hover:bg-primary-500"
            >
              مشاهده‌ی دوره‌ها
            </NuxtLink>
            <NuxtLink
              to="/auth/register"
              class="glass rounded-lg px-7 py-3 text-center text-sm font-semibold text-gray-800 transition hover:bg-white/70 dark:text-gray-100"
            >
              شروع رایگان
            </NuxtLink>
          </div>
        </div>

        <!-- Teaching-scene illustration instead of a generic video-card mockup -->
        <IllustrationTeachingScene class="mx-auto aspect-[4/3] w-full max-w-md lg:mx-0 lg:ms-auto" />
      </div>
    </section>

    <!-- Feature panels — glass cards, varied sizes -->
    <section class="mt-8 grid grid-cols-1 gap-5 md:grid-cols-3">
      <div class="glass rounded-2xl p-8 md:col-span-2">
        <p class="text-sm font-semibold text-primary-700 dark:text-primary-300">پیش‌نمایش رایگان</p>
        <p class="mt-3 max-w-md text-xl font-bold leading-relaxed text-gray-900 dark:text-white">
          قبل از خرید هر دوره، بخشی از تدریس را رایگان تماشا کنید — بدون سورپرایز، بدون ریسک.
        </p>
      </div>
      <div class="glass rounded-2xl p-6">
        <div class="glass flex h-9 w-9 items-center justify-center rounded-lg text-emerald-700 dark:text-emerald-300">
          <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" /></svg>
        </div>
        <p class="mt-3 font-semibold text-gray-900 dark:text-white">مدرس‌های تاییدشده</p>
        <p class="mt-1 text-sm text-gray-700 dark:text-gray-300">هر پروفایل و دوره پیش از انتشار بررسی می‌شود.</p>
      </div>
      <div class="glass rounded-2xl p-6">
        <div class="glass flex h-9 w-9 items-center justify-center rounded-lg text-accent-700 dark:text-accent-300">
          <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V6m0 10v2" /></svg>
        </div>
        <p class="mt-3 font-semibold text-gray-900 dark:text-white">پرداخت امن</p>
        <p class="mt-1 text-sm text-gray-700 dark:text-gray-300">خرید سریع با درگاه زرین‌پال.</p>
      </div>
      <div class="glass rounded-2xl p-6 md:col-span-2">
        <div class="glass flex h-9 w-9 items-center justify-center rounded-lg text-primary-700 dark:text-primary-300">
          <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 14l9-5-9-5-9 5 9 5zm0 0l6.16-3.42A12.083 12.083 0 0112 21a12.083 12.083 0 01-6.16-10.42L12 14z" /></svg>
        </div>
        <p class="mt-3 font-semibold text-gray-900 dark:text-white">دسترسی همیشگی</p>
        <p class="mt-1 text-sm text-gray-700 dark:text-gray-300">بعد از خرید، دوره برای همیشه در حساب شما باقی می‌ماند.</p>
      </div>
    </section>

    <!-- Featured courses — real data, with a play-icon hint that a video preview exists -->
    <section v-if="featuredCourses && featuredCourses.length" class="mt-12">
      <div class="flex items-center justify-between">
        <h2 class="text-xl font-bold text-gray-900 dark:text-white">دوره‌های پیشنهادی</h2>
        <NuxtLink to="/courses" class="text-sm font-medium text-primary-600 hover:underline dark:text-primary-400">
          مشاهده‌ی همه
        </NuxtLink>
      </div>
      <div class="mt-5 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <NuxtLink
          v-for="course in featuredCourses"
          :key="course.slug"
          :to="`/courses/${course.slug}`"
          class="glass group flex flex-col overflow-hidden rounded-xl transition hover:-translate-y-0.5 hover:shadow-lg"
        >
          <div class="relative aspect-video w-full overflow-hidden bg-black/10">
            <NuxtImg
              v-if="course.cover_image"
              :src="course.cover_image"
              :alt="course.title"
              class="h-full w-full object-cover transition group-hover:scale-105"
              loading="lazy"
            />
            <div class="absolute inset-0 flex items-center justify-center">
              <span class="glass flex h-10 w-10 items-center justify-center rounded-full">
                <svg class="h-4 w-4 text-primary-700 dark:text-primary-300" fill="currentColor" viewBox="0 0 20 20"><path d="M6 4l10 6-10 6V4z" /></svg>
              </span>
            </div>
          </div>
          <div class="flex flex-1 flex-col p-4">
            <h3 class="line-clamp-2 text-sm font-semibold text-gray-900 dark:text-white">{{ course.title }}</h3>
            <p v-if="course.instructor_name" class="mt-1 text-xs text-gray-600 dark:text-gray-400">{{ course.instructor_name }}</p>
            <div class="mt-auto pt-3 text-sm font-bold text-accent-600 dark:text-accent-400">
              {{ Number(course.effective_price) === 0 ? 'رایگان' : `${Number(course.effective_price).toLocaleString('fa-IR')} تومان` }}
            </div>
          </div>
        </NuxtLink>
      </div>
    </section>

    <!-- Featured instructors — photo + short bio -->
    <section v-if="featuredInstructors && featuredInstructors.length" class="mt-12">
      <div class="flex items-center justify-between">
        <h2 class="text-xl font-bold text-gray-900 dark:text-white">مدرس‌های ما</h2>
        <NuxtLink to="/instructors" class="text-sm font-medium text-primary-600 hover:underline dark:text-primary-400">
          مشاهده‌ی همه
        </NuxtLink>
      </div>
      <div class="mt-5 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
        <NuxtLink
          v-for="instructor in featuredInstructors"
          :key="instructor.slug"
          :to="`/instructors/${instructor.slug}`"
          class="glass flex items-center gap-4 rounded-2xl p-5 transition hover:-translate-y-0.5 hover:shadow-lg"
        >
          <NuxtImg
            v-if="instructor.cover_image"
            :src="instructor.cover_image"
            :alt="instructor.display_name"
            class="h-16 w-16 shrink-0 rounded-full object-cover"
          />
          <div v-else class="flex h-16 w-16 shrink-0 items-center justify-center rounded-full bg-primary-100 text-lg font-bold text-primary-700 dark:bg-primary-900/40 dark:text-primary-300">
            {{ instructor.display_name?.[0] }}
          </div>
          <div class="min-w-0">
            <p class="font-semibold text-gray-900 dark:text-white">{{ instructor.display_name }}</p>
            <InstructorRatingStars :rating="instructor.rating_avg" class="mt-0.5" />
            <p class="mt-1 line-clamp-2 text-sm text-gray-600 dark:text-gray-400">{{ instructor.headline }}</p>
          </div>
        </NuxtLink>
      </div>
    </section>

    <!-- CTA panel -->
    <section class="glass mt-8 flex flex-col items-center gap-6 rounded-3xl p-10 text-center sm:p-16">
      <h2 class="text-2xl font-bold text-gray-900 sm:text-3xl dark:text-white">مدرس هستید؟</h2>
      <p class="max-w-xl text-gray-700 dark:text-gray-300">
        دوره‌های خود را منتشر کنید، به هزاران دانشجو دسترسی پیدا کنید و درآمد کسب کنید.
      </p>
      <NuxtLink
        to="/auth/register"
        class="rounded-lg bg-accent-500 px-7 py-3 text-sm font-semibold text-white shadow-lg shadow-accent-500/30 transition hover:bg-accent-400"
      >
        شروع تدریس
      </NuxtLink>
    </section>
  </div>
</template>
