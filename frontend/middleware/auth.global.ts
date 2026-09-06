export default defineNuxtRouteMiddleware((to) => {
  const authStore = useAuthStore()
  const protectedPrefixes = ['/dashboard', '/instructor-panel', '/admin', '/profile']

  if (protectedPrefixes.some((p) => to.path.startsWith(p)) && !authStore.isAuthenticated) {
    return navigateTo('/auth/login')
  }

  if (to.path.startsWith('/admin') && authStore.user?.role !== 'admin') {
    return navigateTo('/dashboard')
  }
})
