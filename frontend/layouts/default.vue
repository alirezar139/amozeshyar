<template>
  <div class="flex min-h-screen flex-col">
    <LayoutSiteHeader />
    <main class="flex-1">
      <slot />
    </main>
    <LayoutSiteFooter />
  </div>
</template>
