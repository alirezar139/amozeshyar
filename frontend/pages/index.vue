<script setup lang="ts">
const { request } = useApi()
const { owner, siteName, teacherName, teacherTitle } = useSite()
const authStore = useAuthStore()
const { openRegister } = useAuthModal()

const seoDescription = computed(() => owner.value?.bio || owner.value?.headline || 'دوره‌های آموزشی تخصصی، همراه با پیش‌نمایش رایگان.')
useSeoMeta({
  title: () => [siteName.value, teacherName.value !== siteName.value ? teacherName.value : '', owner.value?.headline].filter(Boolean).join(' | '),
  description: seoDescription,
  ogTitle: siteName,
  ogDescription: seoDescription,
  ogImage: () => owner.value?.cover_image || undefined,
  ogType: 'website',
})

// Independent fetches: started together, awaited as a group.
const categoriesAsync = useAsyncData('home-categories', async () => {
  const page = await request<{ results: any[] }>('/categories/')
  // Skip categories with no published course yet — no point linking
  // to a filtered course list that would just come back empty.
  return page.results.filter((c) => c.course_count > 0).slice(0, 6)
})
const catalogAsync = useAsyncData('home-featured-courses', async () => {
  const page = await request<{ count: number; results: any[] }>('/courses/')
  return { total: page.count, featured: page.results.slice(0, 3) }
})
await Promise.all([categoriesAsync, catalogAsync])
const { data: categories } = categoriesAsync
const { data: catalog } = catalogAsync
const featuredCourses = computed(() => catalog.value?.featured ?? [])

const socialLinks = computed(() => publicSocialLinks(owner.value?.social_links))

// Only numbers that are actually true about this site — a "0 students" badge hurts more than no badge.
const stats = computed(() => {
  const rows: { value: string; label: string }[] = []
  if (catalog.value?.total) rows.push({ value: catalog.value.total.toLocaleString('fa-IR'), label: 'دوره‌ی آموزشی' })
  if (owner.value?.total_students) rows.push({ value: owner.value.total_students.toLocaleString('fa-IR'), label: 'دانشجو' })
  if (Number(owner.value?.rating_avg)) rows.push({ value: Number(owner.value!.rating_avg).toLocaleString('fa-IR', { maximumFractionDigits: 1 }), label: 'امتیاز دانشجویان' })
  return rows
})

function formatPrice(value: number | string) {
  const n = Number(value)
  return n === 0 ? 'رایگان' : `${n.toLocaleString('fa-IR')} تومان`
}

const levelLabels: Record<string, string> = { beginner: 'مقدماتی', intermediate: 'متوسط', advanced: 'پیشرفته' }
</script>

<template>
  <div class="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
    <!-- Hero: who teaches here. Text on the reading side, portrait opposite. -->
    <section class="relative grid grid-cols-1 items-center gap-12 py-6 lg:grid-cols-12 lg:gap-8 lg:py-12">
      <div class="lg:col-span-7">
        <span class="glass inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold text-gray-700 dark:text-gray-200">
          <span class="relative flex h-2 w-2">
            <span class="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
            <span class="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
          </span>
          دوره‌های آموزشی و آموزش آنلاین
        </span>

        <h1 class="mt-6 text-4xl font-black leading-[1.2] tracking-tight text-gray-900 sm:text-6xl dark:text-white">
          {{ teacherName }}
        </h1>
        <p v-if="owner?.headline" class="mt-3 bg-gradient-to-l from-primary-600 to-accent-500 bg-clip-text text-xl font-bold text-transparent sm:text-2xl dark:from-primary-300 dark:to-accent-300">
          {{ owner.headline }}
        </p>
        <p class="mt-5 line-clamp-4 max-w-xl whitespace-pre-line text-base leading-8 text-gray-600 sm:text-lg dark:text-gray-300">
          {{ owner?.bio || 'دوره‌های تخصصی با پیش‌نمایش رایگان؛ پیش از ثبت‌نام، شیوه‌ی تدریس را از نزدیک ببینید.' }}
        </p>

        <div class="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center">
          <NuxtLink
            to="/courses"
            data-tour="hero-cta"
            class="group inline-flex items-center justify-center gap-2 rounded-xl bg-primary-600 px-7 py-3.5 text-sm font-semibold text-white shadow-xl shadow-primary-600/30 transition hover:-translate-y-0.5 hover:bg-primary-500"
          >
            مشاهده‌ی دوره‌ها
            <svg class="h-4 w-4 transition group-hover:-translate-x-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" /></svg>
          </NuxtLink>
          <button
            v-if="!authStore.isAuthenticated"
            type="button"
            class="glass rounded-xl px-7 py-3.5 text-sm font-semibold text-gray-800 transition hover:-translate-y-0.5 hover:bg-white/70 dark:text-gray-100 dark:hover:bg-white/10"
            @click="openRegister"
          >
            ثبت‌نام رایگان
          </button>
        </div>

        <div v-if="socialLinks.length" class="mt-8 flex flex-wrap items-center gap-2">
          <a
            v-for="link in socialLinks"
            :key="link.label"
            :href="link.url"
            target="_blank"
            rel="noopener"
            class="glass inline-flex items-center gap-2 rounded-full py-1 pe-3 ps-1 text-xs font-medium text-gray-700 transition hover:-translate-y-0.5 dark:text-gray-200"
          >
            <span :class="['flex h-6 w-6 items-center justify-center rounded-full text-[11px] font-bold text-white', socialBadgeClass(link)]">
              {{ link.label[0] }}
            </span>
            {{ link.label }}
          </a>
        </div>
      </div>

      <!-- Portrait: animated stack of color cards behind, floating badges in front, so even a plain ID photo reads as a designed hero -->
      <div class="relative mx-auto w-full max-w-[17rem] sm:max-w-[22rem] lg:col-span-5">
        <div class="absolute -inset-6 -z-10 rounded-full bg-primary-500/20 blur-3xl" />
        <IllustrationPortraitStack :src="owner?.cover_image" :alt="teacherName" />

        <div class="glass absolute -bottom-5 -start-3 flex items-center gap-3 rounded-2xl px-4 py-3 shadow-xl sm:-start-10">
          <span class="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/15 text-emerald-600 dark:text-emerald-400">
            <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
          </span>
          <div>
            <p class="text-sm font-bold text-gray-900 dark:text-white">دوره‌ی آنلاین</p>
            <p class="text-xs text-gray-500 dark:text-gray-400">گفت‌وگوی مستقیم با استاد</p>
          </div>
        </div>
        <div v-if="catalog?.total" class="glass absolute -end-2 top-8 rounded-2xl px-4 py-3 text-center shadow-xl sm:-end-8">
          <p class="text-2xl font-black text-primary-700 dark:text-primary-300">{{ catalog.total.toLocaleString('fa-IR') }}</p>
          <p class="text-xs text-gray-600 dark:text-gray-300">دوره‌ی آموزشی</p>
        </div>
      </div>
    </section>

    <!-- Stats strip — only rendered when there's something real to show -->
    <section v-if="stats.length > 1" class="glass mt-16 grid grid-cols-1 divide-y divide-white/30 rounded-2xl sm:grid-cols-3 sm:divide-x sm:divide-y-0 sm:divide-x-reverse dark:divide-white/10">
      <div v-for="stat in stats" :key="stat.label" class="px-6 py-5 text-center">
        <p class="text-3xl font-black text-gray-900 dark:text-white">{{ stat.value }}</p>
        <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">{{ stat.label }}</p>
      </div>
    </section>

    <!-- Courses first: that's what a visitor came for -->
    <section v-if="featuredCourses.length" data-tour="featured-courses" class="mt-20">
      <div class="flex items-end justify-between gap-4">
        <div>
          <p class="text-sm font-semibold text-primary-600 dark:text-primary-400">دوره‌ها</p>
          <h2 class="mt-1 text-2xl font-extrabold text-gray-900 sm:text-3xl dark:text-white">مسیر یادگیری خود را انتخاب کنید</h2>
        </div>
        <NuxtLink to="/courses" class="shrink-0 text-sm font-medium text-primary-600 hover:underline dark:text-primary-400">
          مشاهده‌ی همه‌ی دوره‌ها ←
        </NuxtLink>
      </div>
      <div class="mt-6 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
        <NuxtLink
          v-for="course in featuredCourses"
          :key="course.slug"
          :to="`/courses/${course.slug}`"
          class="glass group flex flex-col overflow-hidden rounded-2xl transition hover:-translate-y-1 hover:shadow-xl"
        >
          <div class="relative aspect-video w-full overflow-hidden bg-gradient-to-br from-primary-500/20 to-accent-500/20">
            <NuxtImg
              v-if="course.cover_image"
              :src="course.cover_image"
              :alt="course.title"
              class="h-full w-full object-cover transition duration-500 group-hover:scale-105"
              loading="lazy"
            />
            <span class="absolute inset-0 flex items-center justify-center opacity-0 transition group-hover:opacity-100">
              <span class="flex h-12 w-12 items-center justify-center rounded-full bg-white/90 shadow-lg">
                <svg class="h-5 w-5 text-primary-700" fill="currentColor" viewBox="0 0 20 20"><path d="M6 4l10 6-10 6V4z" /></svg>
              </span>
            </span>
            <span class="absolute start-3 top-3 rounded-full bg-black/55 px-2.5 py-0.5 text-[11px] font-medium text-white backdrop-blur">
              پیش‌نمایش رایگان
            </span>
          </div>
          <div class="flex flex-1 flex-col p-5">
            <div class="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
              <span v-if="course.category_name">{{ course.category_name }}</span>
              <span v-if="course.category_name && levelLabels[course.level]">·</span>
              <span v-if="levelLabels[course.level]">{{ levelLabels[course.level] }}</span>
            </div>
            <h3 class="mt-2 line-clamp-2 font-bold text-gray-900 dark:text-white">{{ course.title }}</h3>
            <p v-if="course.subtitle" class="mt-1 line-clamp-2 text-sm text-gray-600 dark:text-gray-400">{{ course.subtitle }}</p>
            <div class="mt-auto flex items-center justify-between pt-4">
              <span class="font-bold text-accent-600 dark:text-accent-400">{{ formatPrice(course.effective_price) }}</span>
              <span
                v-if="Number(course.discount_price) && Number(course.price) > Number(course.effective_price)"
                class="text-xs text-gray-400 line-through"
              >
                {{ formatPrice(course.price) }}
              </span>
            </div>
          </div>
        </NuxtLink>
      </div>
    </section>

    <!-- Why learn here -->
    <section data-tour="features" class="mt-20">
      <p class="text-sm font-semibold text-primary-600 dark:text-primary-400">چرا این دوره‌ها؟</p>
      <h2 class="mt-1 text-2xl font-extrabold text-gray-900 sm:text-3xl dark:text-white">یادگیری مطمئن، با همراهی استاد</h2>
      <div class="mt-6 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <div class="glass rounded-2xl p-6">
          <span class="flex h-11 w-11 items-center justify-center rounded-xl bg-primary-500/15 text-primary-700 dark:text-primary-300">
            <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path stroke-linecap="round" stroke-linejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>
          </span>
          <p class="mt-4 font-bold text-gray-900 dark:text-white">پیش از خرید، ببینید</p>
          <p class="mt-1.5 text-sm leading-6 text-gray-600 dark:text-gray-400">بخشی از هر دوره به‌رایگان در دسترس است تا با خیال آسوده انتخاب کنید.</p>
        </div>
        <div class="glass rounded-2xl p-6">
          <span class="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-500/15 text-emerald-600 dark:text-emerald-400">
            <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" /></svg>
          </span>
          <p class="mt-4 font-bold text-gray-900 dark:text-white">دوره‌های آنلاین</p>
          <p class="mt-1.5 text-sm leading-6 text-gray-600 dark:text-gray-400">در جلسه‌های آنلاین شرکت کنید و پرسش‌های خود را مستقیماً با {{ teacherTitle }} در میان بگذارید.</p>
        </div>
        <div class="glass rounded-2xl p-6">
          <span class="flex h-11 w-11 items-center justify-center rounded-xl bg-accent-500/15 text-accent-600 dark:text-accent-400">
            <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
          </span>
          <p class="mt-4 font-bold text-gray-900 dark:text-white">ادامه از همان لحظه</p>
          <p class="mt-1.5 text-sm leading-6 text-gray-600 dark:text-gray-400">هر ویدیو درست از همان جایی که متوقف کرده‌اید ادامه می‌یابد.</p>
        </div>
        <div class="glass rounded-2xl p-6">
          <span class="flex h-11 w-11 items-center justify-center rounded-xl bg-sky-500/15 text-sky-600 dark:text-sky-400">
            <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>
          </span>
          <p class="mt-4 font-bold text-gray-900 dark:text-white">دسترسی همیشگی</p>
          <p class="mt-1.5 text-sm leading-6 text-gray-600 dark:text-gray-400">با یک بار خرید، دوره برای همیشه در حساب کاربری شما می‌ماند؛ پرداخت از طریق درگاه امن زرین‌پال انجام می‌شود.</p>
        </div>
      </div>
    </section>

    <!-- Topics -->
    <section v-if="categories && categories.length > 1" data-tour="categories" class="mt-20">
      <h2 class="text-xl font-bold text-gray-900 dark:text-white">موضوع‌های آموزشی</h2>
      <CourseCategoryCarousel :categories="categories" class="mt-5" />
    </section>

    <!-- Closing CTA -->
    <section class="relative mt-20 overflow-hidden rounded-3xl bg-gradient-to-br from-primary-600 to-primary-800 px-8 py-14 text-center sm:px-16">
      <div class="absolute -end-16 -top-16 h-56 w-56 rounded-full bg-accent-400/30 blur-3xl" />
      <div class="absolute -bottom-20 -start-10 h-56 w-56 rounded-full bg-white/10 blur-3xl" />
      <h2 class="relative text-2xl font-extrabold text-white sm:text-4xl">
        {{ authStore.isAuthenticated ? 'یادگیری را ادامه دهید' : 'همین امروز شروع کنید' }}
      </h2>
      <p class="relative mx-auto mt-4 max-w-xl text-primary-50/90">
        {{ authStore.isAuthenticated
          ? 'دوره‌های شما و جلسه‌های آنلاین پیش‌رو در داشبورد در انتظارتان است.'
          : `ثبت‌نام رایگان است؛ پیش‌نمایش دوره‌ها را ببینید و هر زمان آماده بودید، یادگیری را با ${teacherTitle} آغاز کنید.` }}
      </p>
      <div class="relative mt-8 flex justify-center">
        <NuxtLink
          v-if="authStore.isAuthenticated"
          to="/dashboard"
          class="rounded-xl bg-white px-8 py-3.5 text-sm font-bold text-primary-700 shadow-xl transition hover:-translate-y-0.5"
        >
          رفتن به داشبورد
        </NuxtLink>
        <button
          v-else
          type="button"
          class="rounded-xl bg-white px-8 py-3.5 text-sm font-bold text-primary-700 shadow-xl transition hover:-translate-y-0.5"
          @click="openRegister"
        >
          ثبت‌نام رایگان
        </button>
      </div>
    </section>
  </div>
</template>
