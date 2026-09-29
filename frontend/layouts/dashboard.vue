<script setup lang="ts">
const sidebarOpen = ref(false)
const { logout } = useAuth()
const { owner, teacherName } = useSite()

async function onLogout() {
  await logout()
  await navigateTo('/')
}
</script>

<template>
  <div class="relative flex min-h-screen flex-col md:flex-row">
    <LayoutAmbientBackground />
    <aside class="glass w-full shrink-0 border-x-0 border-t-0 md:w-64 md:border-y-0 md:border-e">
      <div class="flex items-center justify-between gap-2 px-4 py-4">
        <!-- A student's panel belongs to one teacher: show who, not a generic brand -->
        <NuxtLink to="/" class="flex min-w-0 items-center gap-3">
          <img
            v-if="owner?.cover_image"
            :src="owner.cover_image"
            :alt="teacherName"
            class="h-10 w-10 shrink-0 rounded-full object-cover object-top ring-2 ring-header-500/40"
          >
          <span v-else class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-header-600 font-bold text-white">
            {{ teacherName[0] }}
          </span>
          <span class="min-w-0">
            <span class="block text-[11px] text-gray-500 dark:text-gray-400">استاد شما</span>
            <span class="block truncate font-bold text-header-700 dark:text-header-400">{{ teacherName }}</span>
          </span>
        </NuxtLink>
        <div class="flex items-center gap-2">
          <LayoutThemeToggle />
          <button class="md:hidden" aria-label="Toggle sidebar" @click="sidebarOpen = !sidebarOpen">☰</button>
        </div>
      </div>
      <nav :class="['flex-col gap-1 px-2 pb-4', sidebarOpen ? 'flex' : 'hidden md:flex']">
        <NuxtLink to="/dashboard" class="rounded-md px-3 py-2 text-sm text-gray-700 transition hover:bg-nav-500/10 hover:text-nav-700 dark:text-gray-200 dark:hover:bg-nav-500/10 dark:hover:text-nav-300" exact-active-class="bg-nav-500/15 text-nav-700 dark:bg-nav-500/15 dark:text-nav-300">
          خانه
        </NuxtLink>
        <NuxtLink to="/dashboard/my-courses" class="rounded-md px-3 py-2 text-sm text-gray-700 transition hover:bg-nav-500/10 hover:text-nav-700 dark:text-gray-200 dark:hover:bg-nav-500/10 dark:hover:text-nav-300" active-class="bg-nav-500/15 text-nav-700 dark:bg-nav-500/15 dark:text-nav-300">
          دوره‌های من
        </NuxtLink>
        <NuxtLink to="/dashboard/orders" class="rounded-md px-3 py-2 text-sm text-gray-700 transition hover:bg-nav-500/10 hover:text-nav-700 dark:text-gray-200 dark:hover:bg-nav-500/10 dark:hover:text-nav-300" active-class="bg-nav-500/15 text-nav-700 dark:bg-nav-500/15 dark:text-nav-300">
          سفارش‌ها
        </NuxtLink>
        <NuxtLink to="/dashboard/calendar" class="rounded-md px-3 py-2 text-sm text-gray-700 transition hover:bg-nav-500/10 hover:text-nav-700 dark:text-gray-200 dark:hover:bg-nav-500/10 dark:hover:text-nav-300" active-class="bg-nav-500/15 text-nav-700 dark:bg-nav-500/15 dark:text-nav-300">
          تقویم کلاس‌ها
        </NuxtLink>
        <NuxtLink to="/profile" class="rounded-md px-3 py-2 text-sm text-gray-700 transition hover:bg-nav-500/10 hover:text-nav-700 dark:text-gray-200 dark:hover:bg-nav-500/10 dark:hover:text-nav-300" active-class="bg-nav-500/15 text-nav-700 dark:bg-nav-500/15 dark:text-nav-300">
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
