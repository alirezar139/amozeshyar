<script setup lang="ts">
const { openLogin, openRegister } = useAuthModal()
const currentYear = new Date().getFullYear()
const { owner, siteName } = useSite()
const socialLinks = computed(() => publicSocialLinks(owner.value?.social_links))
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
      <div>
        <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">حساب کاربری</h3>
        <ul class="mt-3 space-y-2 text-sm text-gray-600 dark:text-gray-400">
          <li><button type="button" @click="openLogin">ورود</button></li>
          <li><button type="button" @click="openRegister">ثبت‌نام</button></li>
        </ul>
      </div>
    </div>
    <div class="mx-auto mt-8 max-w-7xl border-t border-white/30 px-4 pt-6 text-center text-sm text-gray-500 sm:px-6 lg:px-8 dark:border-white/10 dark:text-gray-400">
      © {{ currentYear }} {{ siteName }}. تمامی حقوق محفوظ است.
    </div>
  </footer>
</template>
