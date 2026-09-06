<script setup lang="ts">
definePageMeta({ layout: 'dashboard' })
const authStore = useAuthStore()
</script>

<template>
  <div>
    <h1 class="text-xl font-bold text-gray-900 dark:text-white">
      خوش آمدید{{ authStore.user ? '، ' + authStore.user.first_name : '' }}
    </h1>
    <p class="mt-2 text-gray-600 dark:text-gray-400">از منوی کناری دوره‌ها و سفارش‌های خود را مدیریت کنید.</p>
  </div>
</template>
