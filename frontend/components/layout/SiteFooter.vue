<script setup lang="ts">
const { openLogin, openRegister } = useAuthModal()
const currentYear = new Date().getFullYear()
const { owner, siteName } = useSite()
const socialLinks = computed(() => publicSocialLinks(owner.value?.social_links))

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
</script>

<template>
  <footer class="glass mt-16 border-x-0 border-b-0 py-10">
    <div class="mx-auto grid max-w-7xl grid-cols-1 gap-8 px-4 sm:grid-cols-2 sm:px-6 lg:grid-cols-4 lg:px-8">
      <div>
        <LayoutSiteBrand size="lg" />
        <p v-if="owner?.headline" class="mt-2 text-sm text-gray-600 dark:text-gray-400">{{ owner.headline }}</p>
      </div>
      <div>
        <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">دوره‌ها</h3>
        <ul class="mt-3 space-y-2 text-sm text-gray-600 dark:text-gray-400">
          <li><NuxtLink to="/courses">همه‌ی دوره‌ها</NuxtLink></li>
        </ul>
      </div>
      <div v-if="owner?.phone_number || socialLinks.length">
        <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">تماس و شبکه‌های اجتماعی</h3>
        <ul class="mt-3 space-y-2 text-sm text-gray-600 dark:text-gray-400">
          <li v-if="owner?.phone_number"><a :href="`tel:${owner.phone_number}`" dir="ltr">{{ owner.phone_number }}</a></li>
          <li v-for="link in socialLinks" :key="link.label">
            <a :href="link.url" target="_blank" rel="noopener" class="hover:text-primary-600 dark:hover:text-primary-400">{{ link.label }}</a>
          </li>
        </ul>
      </div>
      <div v-if="owner?.android_app && canInstallApk">
        <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">اپلیکیشن</h3>
        <a
          :href="apkUrl"
          class="mt-3 inline-flex items-center gap-2 rounded-xl bg-gray-900 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-gray-700 dark:bg-white dark:text-gray-900 dark:hover:bg-gray-200"
        >
          <svg class="h-5 w-5" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M17.6 9.48l1.84-3.18a.38.38 0 00-.66-.38l-1.86 3.22a11.5 11.5 0 00-9.84 0L5.22 5.92a.38.38 0 00-.66.38L6.4 9.48A10.8 10.8 0 001 18h22a10.8 10.8 0 00-5.4-8.52zM7 15.25a1.25 1.25 0 110-2.5 1.25 1.25 0 010 2.5zm10 0a1.25 1.25 0 110-2.5 1.25 1.25 0 010 2.5z" /></svg>
          دانلود اپ اندروید
        </a>
      </div>
      <div>
        <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">حساب کاربری</h3>
        <ul class="mt-3 space-y-2 text-sm text-gray-600 dark:text-gray-400">
          <li><button type="button" @click="openLogin">ورود</button></li>
          <li><button type="button" @click="openRegister">ثبت‌نام</button></li>
        </ul>
      </div>
    </div>
    <div class="mx-auto mt-8 max-w-7xl border-t border-white/30 px-4 pt-6 text-center text-sm text-gray-500 sm:px-6 lg:px-8 dark:border-white/10 dark:text-gray-400">
      <p>© {{ currentYear }} {{ siteName }}. تمامی حقوق محفوظ است.</p>
      <p class="mt-2 text-xs">
        قدرت‌گرفته از
        <a href="https://modaresyar.site" target="_blank" rel="noopener" class="font-medium hover:text-primary-600 dark:hover:text-primary-400">مدرس‌یار</a>
      </p>
    </div>
  </footer>
</template>
