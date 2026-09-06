<script setup lang="ts">
const authStore = useAuthStore()
const { open: openLoginModal } = useLoginModal()
const mobileMenuOpen = ref(false)

function toggleMenu() {
  mobileMenuOpen.value = !mobileMenuOpen.value
}

function onLoginClick() {
  mobileMenuOpen.value = false
  openLoginModal()
}
</script>

<template>
  <header class="glass sticky top-0 z-40">
    <div class="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
      <NuxtLink to="/" class="flex items-center gap-2 text-xl font-bold text-primary-700 dark:text-primary-400">
        <span class="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-600 text-sm font-extrabold text-white">آ</span>
        آموزش‌یار
      </NuxtLink>

      <nav class="hidden items-center gap-6 md:flex">
        <NuxtLink to="/courses" class="text-sm font-medium text-gray-700 hover:text-primary-600 dark:text-gray-200">
          دوره‌ها
        </NuxtLink>
        <NuxtLink to="/instructors" class="text-sm font-medium text-gray-700 hover:text-primary-600 dark:text-gray-200">
          مدرس‌ها
        </NuxtLink>
      </nav>

      <div class="hidden items-center gap-3 md:flex">
        <template v-if="authStore.isAuthenticated">
          <NuxtLink
            :to="authStore.isAdmin ? '/admin' : authStore.isInstructor ? '/instructor-panel/courses' : '/dashboard'"
            class="text-sm font-medium text-gray-700 hover:text-primary-600 dark:text-gray-200"
          >
            {{ authStore.isAdmin ? 'پنل ادمین' : authStore.isInstructor ? 'پنل مدرس' : 'داشبورد' }}
          </NuxtLink>
        </template>
        <template v-else>
          <button
            type="button"
            class="text-sm font-medium text-gray-700 hover:text-primary-600 dark:text-gray-200"
            @click="onLoginClick"
          >
            ورود
          </button>
          <NuxtLink
            to="/auth/register"
            class="rounded-md bg-accent-500 px-4 py-2 text-sm font-medium text-white hover:bg-accent-400"
          >
            ثبت‌نام
          </NuxtLink>
        </template>
      </div>

      <button class="md:hidden" aria-label="Toggle menu" @click="toggleMenu">
        <span class="block h-0.5 w-6 bg-gray-800 dark:bg-gray-100" />
        <span class="mt-1.5 block h-0.5 w-6 bg-gray-800 dark:bg-gray-100" />
        <span class="mt-1.5 block h-0.5 w-6 bg-gray-800 dark:bg-gray-100" />
      </button>
    </div>

    <div v-if="mobileMenuOpen" class="border-t border-gray-200 px-4 py-4 md:hidden dark:border-gray-800">
      <nav class="flex flex-col gap-4">
        <NuxtLink to="/courses" @click="mobileMenuOpen = false">دوره‌ها</NuxtLink>
        <NuxtLink to="/instructors" @click="mobileMenuOpen = false">مدرس‌ها</NuxtLink>
        <NuxtLink
          v-if="authStore.isAuthenticated"
          :to="authStore.isAdmin ? '/admin' : authStore.isInstructor ? '/instructor-panel/courses' : '/dashboard'"
          @click="mobileMenuOpen = false"
        >
          {{ authStore.isAdmin ? 'پنل ادمین' : authStore.isInstructor ? 'پنل مدرس' : 'داشبورد' }}
        </NuxtLink>
        <template v-else>
          <button type="button" class="text-start" @click="onLoginClick">ورود</button>
          <NuxtLink to="/auth/register" @click="mobileMenuOpen = false">ثبت‌نام</NuxtLink>
        </template>
      </nav>
    </div>
  </header>
</template>
