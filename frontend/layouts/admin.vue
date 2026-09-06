<script setup lang="ts">
const sidebarOpen = ref(false)
const { logout } = useAuth()

async function onLogout() {
  await logout()
  await navigateTo('/')
}
</script>

<template>
  <div class="relative flex min-h-screen flex-col md:flex-row">
    <LayoutAmbientBackground />
    <aside class="glass w-full shrink-0 border-x-0 border-t-0 md:w-64 md:border-y-0 md:border-e">
      <div class="flex items-center justify-between px-4 py-4 md:block">
        <NuxtLink to="/admin" class="flex items-center gap-2 text-lg font-bold text-primary-700 dark:text-primary-400">
          <span class="flex h-7 w-7 items-center justify-center rounded-lg bg-primary-600 text-xs font-extrabold text-white">آ</span>
          پنل ادمین
        </NuxtLink>
        <div class="flex items-center gap-2">
          <LayoutThemeToggle />
          <button class="md:hidden" aria-label="Toggle sidebar" @click="sidebarOpen = !sidebarOpen">☰</button>
        </div>
      </div>
      <nav :class="['flex-col gap-1 px-2 pb-4', sidebarOpen ? 'flex' : 'hidden md:flex']">
        <NuxtLink
          to="/admin"
          class="rounded-md px-3 py-2 text-sm text-gray-700 hover:bg-white/40 dark:text-gray-200 dark:hover:bg-white/10"
        >
          نمای کلی
        </NuxtLink>
        <NuxtLink
          to="/admin/courses"
          class="rounded-md px-3 py-2 text-sm text-gray-700 hover:bg-white/40 dark:text-gray-200 dark:hover:bg-white/10"
        >
          تایید دوره‌ها
        </NuxtLink>
        <NuxtLink
          to="/admin/instructors"
          class="rounded-md px-3 py-2 text-sm text-gray-700 hover:bg-white/40 dark:text-gray-200 dark:hover:bg-white/10"
        >
          تایید مدرس‌ها
        </NuxtLink>
        <NuxtLink
          to="/admin/users"
          class="rounded-md px-3 py-2 text-sm text-gray-700 hover:bg-white/40 dark:text-gray-200 dark:hover:bg-white/10"
        >
          مدیریت دسترسی کاربران
        </NuxtLink>
        <NuxtLink
          to="/profile"
          class="rounded-md px-3 py-2 text-sm text-gray-700 hover:bg-white/40 dark:text-gray-200 dark:hover:bg-white/10"
        >
          پروفایل من
        </NuxtLink>
        <button
          class="mt-2 rounded-md px-3 py-2 text-start text-sm text-red-600 hover:bg-red-50/50 dark:hover:bg-red-950/40"
          @click="onLogout"
        >
          خروج از حساب
        </button>
      </nav>
    </aside>
    <main class="relative flex-1 p-4 sm:p-6 lg:p-8">
      <slot />
    </main>
  </div>
</template>
