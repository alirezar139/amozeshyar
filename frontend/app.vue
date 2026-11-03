<script setup lang="ts">
const isDev = import.meta.dev
const authStore = useAuthStore()
const { siteName } = useSite()
// The name under the icon when added to an iPhone's home screen.
useHead({ meta: [{ name: 'apple-mobile-web-app-title', content: siteName }] })
</script>

<template>
  <div>
    <NuxtRouteAnnouncer />
    <LayoutSiteBackground />
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
    <AuthModal />
    <PwaIosInstallHint />
    <GuideButton />
    <GuidePanel />
    <GuideTourOverlay />
    <DevLiveLogPanel v-if="isDev || authStore.isDeveloper" />
  </div>
</template>
