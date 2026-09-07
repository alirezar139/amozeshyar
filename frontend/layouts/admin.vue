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
      <div class="flex items-center justify-between px-4 py-4">
        <NuxtLink to="/admin" class="flex items-center gap-2 text-lg font-bold text-header-700 dark:text-header-400">
          <span class="flex h-7 w-7 items-center justify-center rounded-lg bg-header-600 text-xs font-extrabold text-white">آ</span>
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
          class="flex items-center gap-2.5 rounded-md px-3 py-2 text-sm text-gray-700 transition hover:bg-nav-500/10 hover:text-nav-700 dark:text-gray-200 dark:hover:bg-nav-500/10 dark:hover:text-nav-300"
          exact-active-class="bg-nav-500/15 text-nav-700 dark:bg-nav-500/15 dark:text-nav-300"
        >
          <svg class="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" /></svg>
          نمای کلی
        </NuxtLink>
        <NuxtLink
          to="/admin/board"
          class="flex items-center gap-2.5 rounded-md px-3 py-2 text-sm text-gray-700 transition hover:bg-nav-500/10 hover:text-nav-700 dark:text-gray-200 dark:hover:bg-nav-500/10 dark:hover:text-nav-300"
          active-class="bg-nav-500/15 text-nav-700 dark:bg-nav-500/15 dark:text-nav-300"
        >
          <svg class="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 3v18M3 5a2 2 0 012-2h14a2 2 0 012 2v14a2 2 0 01-2 2H5a2 2 0 01-2-2V5z" /></svg>
          تخته‌ی دوره‌ها
        </NuxtLink>
        <NuxtLink
          to="/admin/courses"
          class="flex items-center gap-2.5 rounded-md px-3 py-2 text-sm text-gray-700 transition hover:bg-nav-500/10 hover:text-nav-700 dark:text-gray-200 dark:hover:bg-nav-500/10 dark:hover:text-nav-300"
          active-class="bg-nav-500/15 text-nav-700 dark:bg-nav-500/15 dark:text-nav-300"
        >
          <svg class="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" /></svg>
          تایید دوره‌ها
        </NuxtLink>
        <NuxtLink
          to="/admin/instructors"
          class="flex items-center gap-2.5 rounded-md px-3 py-2 text-sm text-gray-700 transition hover:bg-nav-500/10 hover:text-nav-700 dark:text-gray-200 dark:hover:bg-nav-500/10 dark:hover:text-nav-300"
          active-class="bg-nav-500/15 text-nav-700 dark:bg-nav-500/15 dark:text-nav-300"
        >
          <svg class="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M17 20h5v-2a4 4 0 00-3-3.87M9 20H4v-2a4 4 0 013-3.87m5-3.13a4 4 0 100-8 4 4 0 000 8zm6 3.13a4 4 0 010 6.74M9 12.13a4 4 0 000 6.74" /></svg>
          تایید مدرس‌ها
        </NuxtLink>
        <NuxtLink
          to="/admin/calendar"
          class="flex items-center gap-2.5 rounded-md px-3 py-2 text-sm text-gray-700 transition hover:bg-nav-500/10 hover:text-nav-700 dark:text-gray-200 dark:hover:bg-nav-500/10 dark:hover:text-nav-300"
          active-class="bg-nav-500/15 text-nav-700 dark:bg-nav-500/15 dark:text-nav-300"
        >
          <svg class="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
          تقویم کلاس‌ها
        </NuxtLink>
        <NuxtLink
          to="/admin/users"
          class="flex items-center gap-2.5 rounded-md px-3 py-2 text-sm text-gray-700 transition hover:bg-nav-500/10 hover:text-nav-700 dark:text-gray-200 dark:hover:bg-nav-500/10 dark:hover:text-nav-300"
          active-class="bg-nav-500/15 text-nav-700 dark:bg-nav-500/15 dark:text-nav-300"
        >
          <svg class="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" /></svg>
          مدیریت دسترسی کاربران
        </NuxtLink>
        <NuxtLink
          to="/profile"
          class="flex items-center gap-2.5 rounded-md px-3 py-2 text-sm text-gray-700 transition hover:bg-nav-500/10 hover:text-nav-700 dark:text-gray-200 dark:hover:bg-nav-500/10 dark:hover:text-nav-300"
          active-class="bg-nav-500/15 text-nav-700 dark:bg-nav-500/15 dark:text-nav-300"
        >
          <svg class="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>
          پروفایل من
        </NuxtLink>
        <button
          class="mt-2 flex items-center gap-2.5 rounded-md px-3 py-2 text-start text-sm text-red-600 hover:bg-red-50/50 dark:hover:bg-red-950/40"
          @click="onLogout"
        >
          <svg class="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" /></svg>
          خروج از حساب
        </button>
      </nav>
    </aside>
    <main class="relative flex-1 p-4 sm:p-6 lg:p-8">
      <slot />
    </main>
  </div>
</template>
