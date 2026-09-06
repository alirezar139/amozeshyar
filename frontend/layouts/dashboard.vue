<script setup lang="ts">
const sidebarOpen = ref(false)
</script>

<template>
  <div class="relative flex min-h-screen flex-col md:flex-row">
    <LayoutAmbientBackground />
    <aside class="glass w-full shrink-0 border-x-0 border-t-0 md:w-64 md:border-y-0 md:border-e">
      <div class="flex items-center justify-between px-4 py-4 md:block">
        <NuxtLink to="/" class="text-lg font-bold text-primary-600">آموزش‌یار</NuxtLink>
        <button class="md:hidden" aria-label="Toggle sidebar" @click="sidebarOpen = !sidebarOpen">☰</button>
      </div>
      <nav :class="['flex-col gap-1 px-2 pb-4', sidebarOpen ? 'flex' : 'hidden md:flex']">
        <NuxtLink to="/dashboard" class="rounded-md px-3 py-2 text-sm text-gray-700 hover:bg-white/40 dark:text-gray-200 dark:hover:bg-white/10">
          خانه
        </NuxtLink>
        <NuxtLink to="/dashboard/my-courses" class="rounded-md px-3 py-2 text-sm text-gray-700 hover:bg-white/40 dark:text-gray-200 dark:hover:bg-white/10">
          دوره‌های من
        </NuxtLink>
        <NuxtLink to="/dashboard/orders" class="rounded-md px-3 py-2 text-sm text-gray-700 hover:bg-white/40 dark:text-gray-200 dark:hover:bg-white/10">
          سفارش‌ها
        </NuxtLink>
      </nav>
    </aside>
    <main class="relative flex-1 p-4 sm:p-6 lg:p-8">
      <slot />
    </main>
  </div>
</template>
