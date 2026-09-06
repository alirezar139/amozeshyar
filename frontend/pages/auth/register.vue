<script setup lang="ts">
const authStore = useAuthStore()
const { openRegister } = useAuthModal()

if (authStore.isAuthenticated) {
  await navigateTo(getRoleHome(authStore.user?.role), { replace: true })
} else {
  openRegister()
  await navigateTo('/', { replace: true })
}
</script>

<template>
  <div />
</template>
