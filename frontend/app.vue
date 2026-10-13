<script setup lang="ts">
const isDev = import.meta.dev
const authStore = useAuthStore()
</script>

<template>
  <div>
    <NuxtRouteAnnouncer />
    <LayoutSiteBackground />
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
    <AuthModal />
    <GuideButton />
    <GuidePanel />
    <GuideTourOverlay />
    <DevLiveLogPanel v-if="isDev || authStore.isDeveloper" />
  </div>
</template>
