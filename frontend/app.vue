<script setup lang="ts">
const isDev = import.meta.dev
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
    <DevLiveLogPanel v-if="isDev" />
  </div>
</template>
