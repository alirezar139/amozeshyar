<script setup lang="ts">
const { openLogin, openRegister } = useAuthModal()
</script>

<template>
  <footer class="glass mt-16 border-x-0 border-b-0 py-10">
    <div class="mx-auto grid max-w-7xl grid-cols-1 gap-8 px-4 sm:grid-cols-2 sm:px-6 lg:grid-cols-4 lg:px-8">
      <div>
        <p class="text-lg font-bold text-primary-600">آموزش‌یار</p>
        <p class="mt-2 text-sm text-gray-600 dark:text-gray-400">پلتفرم آموزش آنلاین و ویترین مدرس‌ها</p>
      </div>
      <div>
        <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">دوره‌ها</h3>
        <ul class="mt-3 space-y-2 text-sm text-gray-600 dark:text-gray-400">
          <li><NuxtLink to="/courses">همه‌ی دوره‌ها</NuxtLink></li>
        </ul>
      </div>
      <div>
        <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">مدرس‌ها</h3>
        <ul class="mt-3 space-y-2 text-sm text-gray-600 dark:text-gray-400">
          <li><NuxtLink to="/instructors">همه‌ی مدرس‌ها</NuxtLink></li>
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
  </footer>
</template>
