<script setup lang="ts">
const sidebarOpen = ref(false)
const { logout } = useAuth()
const { total: unread, startPolling } = useUnreadMessages()
onMounted(startPolling)

async function onLogout() {
  await logout()
  await navigateTo('/')
}

const authStore = useAuthStore()
const { request } = useApi()
const showReport = ref(false)
const openReports = ref(0)
onMounted(async () => {
  if (!authStore.isDeveloper) return
  try {
    openReports.value = (await request<{ unresolved_reports: number }>('/monitoring/summary/')).unresolved_reports
  } catch {}
})
</script>

<template>
  <div class="relative flex min-h-screen flex-col md:flex-row">
    <aside class="glass w-full shrink-0 border-x-0 border-t-0 md:w-64 md:border-y-0 md:border-e">
      <div class="flex items-center justify-between px-4 py-4">
        <NuxtLink to="/admin" class="flex items-center gap-2 text-lg font-bold text-header-700 dark:text-header-400">
          <span class="flex h-7 w-7 items-center justify-center rounded-lg bg-header-600 text-xs font-extrabold text-white">آ</span>
          پنل مدیریت
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
          to="/admin/courses"
          class="flex items-center gap-2.5 rounded-md px-3 py-2 text-sm text-gray-700 transition hover:bg-nav-500/10 hover:text-nav-700 dark:text-gray-200 dark:hover:bg-nav-500/10 dark:hover:text-nav-300"
          active-class="bg-nav-500/15 text-nav-700 dark:bg-nav-500/15 dark:text-nav-300"
        >
          <svg class="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" /></svg>
          دوره‌ها
        </NuxtLink>
        <NuxtLink
          to="/admin/exams"
          class="flex items-center gap-2.5 rounded-md px-3 py-2 text-sm text-gray-700 transition hover:bg-nav-500/10 hover:text-nav-700 dark:text-gray-200 dark:hover:bg-nav-500/10 dark:hover:text-nav-300"
          active-class="bg-nav-500/15 text-nav-700 dark:bg-nav-500/15 dark:text-nav-300"
        >
          <svg class="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" /></svg>
          آزمون‌ها
        </NuxtLink>
        <NuxtLink
          to="/admin/calendar"
          class="flex items-center gap-2.5 rounded-md px-3 py-2 text-sm text-gray-700 transition hover:bg-nav-500/10 hover:text-nav-700 dark:text-gray-200 dark:hover:bg-nav-500/10 dark:hover:text-nav-300"
          active-class="bg-nav-500/15 text-nav-700 dark:bg-nav-500/15 dark:text-nav-300"
        >
          <svg class="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
          تقویم دوره‌های آنلاین
        </NuxtLink>
        <NuxtLink
          to="/admin/messages"
          data-tour="nav-messages"
          class="flex items-center gap-2.5 rounded-md px-3 py-2 text-sm text-gray-700 transition hover:bg-nav-500/10 hover:text-nav-700 dark:text-gray-200 dark:hover:bg-nav-500/10 dark:hover:text-nav-300"
          active-class="bg-nav-500/15 text-nav-700 dark:bg-nav-500/15 dark:text-nav-300"
        >
          <svg class="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" /></svg>
          پیام‌ها
          <span v-if="unread" class="ms-auto flex h-5 min-w-5 items-center justify-center rounded-full bg-primary-600 px-1.5 text-[11px] font-bold text-white">{{ unread > 99 ? '۹۹+' : unread.toLocaleString('fa-IR') }}</span>
        </NuxtLink>
        <NuxtLink
          to="/admin/chat-report"
          data-tour="nav-chat-report"
          class="flex items-center gap-2.5 rounded-md px-3 py-2 text-sm text-gray-700 transition hover:bg-nav-500/10 hover:text-nav-700 dark:text-gray-200 dark:hover:bg-nav-500/10 dark:hover:text-nav-300"
          active-class="bg-nav-500/15 text-nav-700 dark:bg-nav-500/15 dark:text-nav-300"
        >
          <svg class="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
          گزارش گفت‌وگوها
        </NuxtLink>
        <NuxtLink
          to="/admin/board"
          data-tour="nav-board"
          class="flex items-center gap-2.5 rounded-md px-3 py-2 text-sm text-gray-700 transition hover:bg-nav-500/10 hover:text-nav-700 dark:text-gray-200 dark:hover:bg-nav-500/10 dark:hover:text-nav-300"
          active-class="bg-nav-500/15 text-nav-700 dark:bg-nav-500/15 dark:text-nav-300"
        >
          <svg class="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" /></svg>
          برنامه‌ی کارها
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
          to="/admin/settings"
          class="flex items-center gap-2.5 rounded-md px-3 py-2 text-sm text-gray-700 transition hover:bg-nav-500/10 hover:text-nav-700 dark:text-gray-200 dark:hover:bg-nav-500/10 dark:hover:text-nav-300"
          active-class="bg-nav-500/15 text-nav-700 dark:bg-nav-500/15 dark:text-nav-300"
        >
          <svg class="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
          تنظیمات سایت
        </NuxtLink>
        <NuxtLink
          v-if="authStore.isDeveloper"
          to="/admin/dev-log"
          class="flex items-center gap-2.5 rounded-md px-3 py-2 text-sm text-gray-700 transition hover:bg-nav-500/10 hover:text-nav-700 dark:text-gray-200 dark:hover:bg-nav-500/10 dark:hover:text-nav-300"
          active-class="bg-nav-500/15 text-nav-700 dark:bg-nav-500/15 dark:text-nav-300"
        >
          <svg class="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
          لاگ زنده
          <span v-if="openReports" class="ms-auto rounded-full bg-red-600 px-1.5 text-[10px] font-bold text-white">{{ openReports }}</span>
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
          type="button"
          class="flex items-center gap-2.5 rounded-md px-3 py-2 text-start text-sm text-gray-700 transition hover:bg-nav-500/10 hover:text-nav-700 dark:text-gray-200 dark:hover:bg-nav-500/10 dark:hover:text-nav-300"
          @click="showReport = true"
        >
          <svg class="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
          گزارش مشکل به پشتیبانی
        </button>
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
    <SupportReportDialog v-if="showReport" @close="showReport = false" />
  </div>
</template>
