<script setup lang="ts">
definePageMeta({ layout: 'dashboard' })
useSeoMeta({ title: 'پیام‌ها' })
</script>

<template>
  <div>
    <h1 class="mb-4 text-xl font-bold text-gray-900 dark:text-white">پیام‌ها</h1>
    <ChatMessenger />
  </div>
</template>
