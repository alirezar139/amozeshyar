<script setup lang="ts">
// Three layers: a gradient invitation card that overlaps the top edge, the
// glass footer itself (brand + numbers, links, contact, app), and the site's
// name set huge and outlined along the bottom as a signature.
const authStore = useAuthStore()
const { openLogin, openRegister } = useAuthModal()
const { owner, siteName } = useSite()
const socialLinks = computed(() => publicSocialLinks(owner.value?.social_links))

// The year in the Persian calendar, written in Persian digits (e.g. ۱۴۰۵).
const currentYear = new Intl.DateTimeFormat('fa-IR-u-ca-persian', { year: 'numeric' }).format(new Date())

const fa = (n: number) => n.toLocaleString('fa-IR')
const stats = computed(() => {
  const out: { value: string; label: string }[] = []
  const students = owner.value?.total_students ?? 0
  const rating = Number(owner.value?.rating_avg ?? 0)
  if (students > 0) out.push({ value: `${fa(students)}+`, label: 'دانشجو' })
  if (rating > 0) out.push({ value: rating.toLocaleString('fa-IR', { maximumFractionDigits: 1 }), label: 'امتیاز از ۵' })
  return out
})

const userHome = computed(() => (authStore.isAdmin ? '/admin' : '/dashboard'))
const userHomeLabel = computed(() => (authStore.isAdmin ? 'پنل مدیریت' : 'داشبورد'))

// The Android app download, once one is published (manage.py publish_android_app).
// Not offered where it can't be used: on iPhone/iPad, or inside the app itself.
const apkUrl = `${useRuntimeConfig().public.apiBase}/site/android.apk`
const canInstallApk = ref(false)
onMounted(() => {
  const ua = navigator.userAgent
  const isIos = /iPhone|iPad|iPod/.test(ua) || (ua.includes('Macintosh') && navigator.maxTouchPoints > 1)
  const inApp = 'Capacitor' in window
  canInstallApk.value = !isIos && !inApp
})

function backToTop() {
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  window.scrollTo({ top: 0, behavior: reduce ? 'auto' : 'smooth' })
}

const linkClass = 'group inline-flex items-center gap-1.5 text-gray-600 transition hover:text-gray-900 dark:text-gray-400 dark:hover:text-white'
</script>

<template>
  <footer class="relative mt-32 px-3 pb-3 sm:px-4">
    <div class="relative mx-auto max-w-7xl">
      <!-- Invitation card, half above the footer -->
      <section class="cta-card relative z-10 mx-2 -mb-16 overflow-hidden rounded-3xl bg-gradient-to-l from-primary-600 via-primary-500 to-accent-500 px-6 py-8 text-white shadow-2xl shadow-primary-600/25 sm:mx-8 sm:px-10 sm:py-10">
        <span aria-hidden="true" class="cta-grid pointer-events-none absolute inset-0 opacity-20" />
        <span aria-hidden="true" class="orb pointer-events-none absolute -start-10 -top-16 h-48 w-48 rounded-full bg-white/25 blur-3xl" />
        <span aria-hidden="true" class="orb orb-late pointer-events-none absolute -bottom-20 end-10 h-56 w-56 rounded-full bg-accent-300/40 blur-3xl" />

        <div class="relative flex flex-col items-start justify-between gap-6 md:flex-row md:items-center">
          <div>
            <p class="text-xs font-semibold tracking-wide text-white/80">قدم بعدی</p>
            <h2 class="mt-1 text-2xl font-extrabold leading-snug sm:text-3xl">یادگیری از همین امروز شروع می‌شه</h2>
            <p class="mt-2 max-w-lg text-sm text-white/85">دوره‌ها رو ببین، هرجا و هر وقت که خواستی یاد بگیر، و هر سؤالی داشتی مستقیم از استاد بپرس.</p>
          </div>
          <div class="flex shrink-0 flex-wrap gap-3">
            <NuxtLink
              to="/courses"
              class="group inline-flex items-center gap-2 rounded-full bg-white px-5 py-2.5 text-sm font-bold text-primary-700 shadow-lg transition hover:-translate-y-0.5 hover:shadow-xl"
            >
              مشاهده‌ی دوره‌ها
              <svg class="h-4 w-4 transition-transform group-hover:-translate-x-1" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" /></svg>
            </NuxtLink>
            <NuxtLink
              v-if="authStore.isAuthenticated"
              :to="userHome"
              class="inline-flex items-center rounded-full border border-white/40 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-white/15"
            >
              {{ userHomeLabel }}
            </NuxtLink>
            <button
              v-else
              type="button"
              class="inline-flex items-center rounded-full border border-white/40 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-white/15"
              @click="openRegister"
            >
              ثبت‌نام
            </button>
          </div>
        </div>
      </section>

      <!-- The footer card -->
      <div class="glass relative overflow-hidden rounded-3xl pt-24">
        <div class="relative grid grid-cols-1 gap-10 px-6 sm:grid-cols-2 sm:px-10 lg:grid-cols-12">
          <div class="lg:col-span-5">
            <NuxtLink to="/" class="inline-block">
              <LayoutSiteBrand size="lg" />
            </NuxtLink>
            <p v-if="owner?.headline" class="mt-3 max-w-sm text-sm leading-7 text-gray-600 dark:text-gray-400">{{ owner.headline }}</p>
            <dl v-if="stats.length" class="mt-5 flex gap-3">
              <div
                v-for="s in stats"
                :key="s.label"
                class="rounded-2xl bg-gray-900/[0.04] px-4 py-2.5 dark:bg-white/[0.06]"
              >
                <dt class="sr-only">{{ s.label }}</dt>
                <dd class="text-lg font-extrabold text-gray-900 dark:text-white">{{ s.value }}</dd>
                <dd class="text-[11px] text-gray-500 dark:text-gray-400">{{ s.label }}</dd>
              </div>
            </dl>
          </div>

          <div class="lg:col-span-2">
            <h3 class="footer-heading">دسترسی سریع</h3>
            <ul class="mt-4 space-y-3 text-sm">
              <li><NuxtLink to="/" :class="linkClass"><span class="link-dot" />خانه</NuxtLink></li>
              <li><NuxtLink to="/courses" :class="linkClass"><span class="link-dot" />همه‌ی دوره‌ها</NuxtLink></li>
            </ul>
          </div>

          <div class="lg:col-span-2">
            <h3 class="footer-heading">حساب کاربری</h3>
            <ul class="mt-4 space-y-3 text-sm">
              <li v-if="authStore.isAuthenticated">
                <NuxtLink :to="userHome" :class="linkClass"><span class="link-dot" />{{ userHomeLabel }}</NuxtLink>
              </li>
              <template v-else>
                <li><button type="button" :class="linkClass" @click="openLogin"><span class="link-dot" />ورود</button></li>
                <li><button type="button" :class="linkClass" @click="openRegister"><span class="link-dot" />ثبت‌نام</button></li>
              </template>
            </ul>
          </div>

          <div v-if="owner?.phone_number || socialLinks.length || (owner?.android_app && canInstallApk)" class="lg:col-span-3">
            <h3 class="footer-heading">در ارتباط باشیم</h3>
            <a
              v-if="owner?.phone_number"
              :href="`tel:${owner.phone_number}`"
              dir="ltr"
              class="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-gray-800 transition hover:text-primary-600 dark:text-gray-100 dark:hover:text-primary-400"
            >
              <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.95.68l1.5 4.49a1 1 0 01-.5 1.21l-2.26 1.13a11.04 11.04 0 005.52 5.52l1.13-2.26a1 1 0 011.21-.5l4.49 1.5a1 1 0 01.68.95V19a2 2 0 01-2 2h-1C9.72 21 3 14.28 3 6V5z" /></svg>
              {{ owner.phone_number }}
            </a>
            <div v-if="socialLinks.length" class="mt-4 flex flex-wrap gap-2">
              <a
                v-for="link in socialLinks"
                :key="link.label"
                :href="link.url"
                target="_blank"
                rel="noopener"
                :title="link.label"
                :aria-label="link.label"
                :class="['social-badge flex h-10 w-10 items-center justify-center rounded-2xl text-sm font-bold text-white shadow-md', socialBadgeClass(link)]"
              >
                {{ link.label[0] }}
              </a>
            </div>
            <a
              v-if="owner?.android_app && canInstallApk"
              :href="apkUrl"
              class="mt-5 inline-flex items-center gap-3 rounded-2xl bg-gray-900 px-4 py-2.5 text-white transition hover:-translate-y-0.5 hover:bg-gray-800 dark:bg-white dark:text-gray-900 dark:hover:bg-gray-100"
            >
              <svg class="h-6 w-6" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M17.6 9.48l1.84-3.18a.38.38 0 00-.66-.38l-1.86 3.22a11.5 11.5 0 00-9.84 0L5.22 5.92a.38.38 0 00-.66.38L6.4 9.48A10.8 10.8 0 001 18h22a10.8 10.8 0 00-5.4-8.52zM7 15.25a1.25 1.25 0 110-2.5 1.25 1.25 0 010 2.5zm10 0a1.25 1.25 0 110-2.5 1.25 1.25 0 010 2.5z" /></svg>
              <span class="flex flex-col leading-tight">
                <span class="text-[10px] opacity-70">دریافت مستقیم</span>
                <span class="text-sm font-bold">اپ اندروید</span>
              </span>
            </a>
          </div>
        </div>

        <!-- Signature: the site's name, huge and outlined -->
        <div aria-hidden="true" class="signature pointer-events-none mt-10 select-none overflow-hidden whitespace-nowrap px-4 text-center font-black leading-none">
          {{ siteName }}
        </div>

        <div class="relative flex flex-col items-center justify-between gap-3 border-t border-gray-900/5 px-6 py-5 text-xs text-gray-500 sm:flex-row sm:px-10 dark:border-white/10 dark:text-gray-400">
          <p>© {{ currentYear }} {{ siteName }} · تمامی حقوق محفوظ است.</p>
          <div class="flex items-center gap-4">
            <p>
              قدرت‌گرفته از
              <a href="https://modaresyar.site" target="_blank" rel="noopener" class="font-semibold text-gray-700 hover:text-primary-600 dark:text-gray-300 dark:hover:text-primary-400">مدرس‌یار</a>
            </p>
            <button
              type="button"
              class="group flex h-9 w-9 items-center justify-center rounded-full bg-gray-900/[0.05] text-gray-700 transition hover:bg-gray-900 hover:text-white dark:bg-white/10 dark:text-gray-200 dark:hover:bg-white dark:hover:text-gray-900"
              aria-label="برگشت به بالای صفحه"
              title="برگشت به بالا"
              @click="backToTop"
            >
              <svg class="h-4 w-4 transition-transform group-hover:-translate-y-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M5 15l7-7 7 7" /></svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  </footer>
</template>

<style scoped>
.footer-heading {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  color: rgb(17 24 39);
}
html.dark .footer-heading {
  color: rgb(243 244 246);
}

/* A small dot that stretches into a dash when its link is hovered. */
.link-dot {
  display: inline-block;
  width: 4px;
  height: 4px;
  border-radius: 9999px;
  background: currentColor;
  opacity: 0.35;
  transition: width 0.25s cubic-bezier(0.22, 1, 0.36, 1), opacity 0.25s ease;
}
.group:hover .link-dot,
.group:focus-visible .link-dot {
  width: 12px;
  opacity: 1;
}

.social-badge {
  transition: transform 0.25s cubic-bezier(0.22, 1, 0.36, 1);
}
.social-badge:hover {
  transform: translateY(-3px) rotate(-6deg);
}

/* Fine grid texture on the invitation card. */
.cta-grid {
  background-image:
    linear-gradient(rgb(255 255 255 / 0.5) 1px, transparent 1px),
    linear-gradient(90deg, rgb(255 255 255 / 0.5) 1px, transparent 1px);
  background-size: 28px 28px;
  mask-image: radial-gradient(ellipse at 30% 40%, black, transparent 70%);
  -webkit-mask-image: radial-gradient(ellipse at 30% 40%, black, transparent 70%);
}

/* Slow drifting light behind the card's text. */
.orb {
  animation: orb-drift 12s ease-in-out infinite alternate;
}
.orb-late {
  animation-delay: -6s;
}
@keyframes orb-drift {
  from { transform: translate(0, 0) scale(1); }
  to { transform: translate(40px, 20px) scale(1.15); }
}

/* The name as an outline fading down into the footer's bottom edge. */
.signature {
  font-size: clamp(3.5rem, 15vw, 11rem);
  margin-bottom: -0.18em;
  color: transparent;
  -webkit-text-stroke: 1.5px rgb(var(--c-header-500) / 0.35);
  background: linear-gradient(to bottom, rgb(var(--c-header-500) / 0.14), transparent 85%);
  -webkit-background-clip: text;
  background-clip: text;
}
html.dark .signature {
  -webkit-text-stroke-color: rgb(var(--c-header-400) / 0.25);
}

@media (prefers-reduced-motion: reduce) {
  .orb {
    animation: none;
  }
  .link-dot,
  .social-badge {
    transition: none;
  }
}
</style>
