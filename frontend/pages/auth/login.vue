<script setup lang="ts">
// There's only one auth experience now — the glass modal (triggered from
// the header/footer, or here). A full-page form would just duplicate it,
// so this route's only job is to redirect home and pop the modal open —
// it exists so a direct link or a middleware redirect to /auth/login still
// gets the user to a login prompt.
const authStore = useAuthStore()
const { openLogin } = useAuthModal()

if (authStore.isAuthenticated) {
  await navigateTo(getRoleHome(authStore.user?.role), { replace: true })
} else {
  openLogin()
  await navigateTo('/', { replace: true })
}
</script>

<template>
  <div />
</template>
