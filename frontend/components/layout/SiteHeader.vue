<script setup lang="ts">
// A floating glass capsule rather than a full-width bar: it sits a little
// off the top edge, tightens up once the page scrolls, and carries a thin
// reading-progress line along its bottom edge. A pill slides under the
// desktop nav link being hovered (or the current one when nothing is).
const authStore = useAuthStore()
const { openLogin, openRegister } = useAuthModal()
const route = useRoute()

const navLinks = [
  { to: '/', label: 'خانه' },
  { to: '/courses', label: 'دوره‌ها' },
]

const userHome = computed(() => (authStore.isAdmin ? '/admin' : '/dashboard'))
const userHomeLabel = computed(() => (authStore.isAdmin ? 'پنل مدیریت' : 'داشبورد'))
const userInitial = computed(() => authStore.user?.first_name?.trim()?.[0] ?? '؟')

function isActive(to: string) {
  return to === '/' ? route.path === '/' : route.path.startsWith(to)
}

// --- Scroll: compact state + reading progress -------------------------
const scrolled = ref(false)
const progress = ref(0)
let ticking = false
function onScroll() {
  if (ticking) return
  ticking = true
  requestAnimationFrame(() => {
    const y = window.scrollY
    const max = document.documentElement.scrollHeight - window.innerHeight
    scrolled.value = y > 12
    progress.value = max > 0 ? Math.min(1, y / max) : 0
    ticking = false
  })
}

// --- Sliding pill under the desktop nav --------------------------------
const navEl = ref<HTMLElement | null>(null)
// NuxtLink is a component, so a template ref hands back its instance; keep its root <a>.
const linkEls: HTMLElement[] = []
function setLinkEl(el: unknown, i: number) {
  const node = (el as { $el?: HTMLElement } | null)?.$el
  if (node) linkEls[i] = node
}
const hovered = ref<number | null>(null)
const pill = ref({ left: 0, width: 0, visible: false })

function placePill() {
  const activeIdx = navLinks.findIndex((l) => isActive(l.to))
  const idx = hovered.value ?? (activeIdx >= 0 ? activeIdx : null)
  const node = idx === null ? undefined : linkEls[idx]
  if (!node || !navEl.value) {
    pill.value = { ...pill.value, visible: false }
    return
  }
  pill.value = { left: node.offsetLeft, width: node.offsetWidth, visible: true }
}
watch([hovered, () => route.path], () => nextTick(placePill))

// --- Mobile menu ------------------------------------------------------
const mobileMenuOpen = ref(false)
watch(() => route.fullPath, () => { mobileMenuOpen.value = false })

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') mobileMenuOpen.value = false
}

function onLoginClick() {
  mobileMenuOpen.value = false
  openLogin()
}

function onRegisterClick() {
  mobileMenuOpen.value = false
  openRegister()
}

onMounted(() => {
  onScroll()
  placePill()
  // Vazirmatn arriving late changes link widths; re-measure once it's in.
  document.fonts?.ready.then(placePill)
  window.addEventListener('scroll', onScroll, { passive: true })
  window.addEventListener('resize', placePill)
  window.addEventListener('keydown', onKeydown)
})
onBeforeUnmount(() => {
  window.removeEventListener('scroll', onScroll)
  window.removeEventListener('resize', placePill)
  window.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <header class="sticky top-0 z-40 px-3 pt-3 sm:px-4">
    <div
      :class="[
        'glass relative mx-auto max-w-7xl overflow-hidden rounded-2xl transition-all duration-300 ease-out',
        scrolled ? 'header-lifted' : '',
      ]"
    >
      <div
        :class="[
          'flex items-center justify-between gap-3 px-3 transition-[height] duration-300 ease-out sm:px-5',
          scrolled ? 'h-14' : 'h-16',
        ]"
      >
        <NuxtLink to="/" class="min-w-0 transition-transform duration-300 hover:scale-[1.02]">
          <LayoutSiteBrand />
        </NuxtLink>

        <!-- Desktop nav with the sliding pill -->
        <nav
          ref="navEl"
          class="relative hidden items-center rounded-full bg-gray-900/[0.04] p-1 md:flex dark:bg-white/[0.06]"
          @mouseleave="hovered = null"
        >
          <span
            aria-hidden="true"
            class="nav-pill absolute inset-y-1 rounded-full bg-white shadow-sm dark:bg-white/10"
            :style="{
              left: `${pill.left}px`,
              width: `${pill.width}px`,
              opacity: pill.visible ? 1 : 0,
            }"
          />
          <NuxtLink
            v-for="(link, i) in navLinks"
            :key="link.to"
            :ref="(el) => setLinkEl(el, i)"
            :to="link.to"
            :class="[
              'relative z-10 rounded-full px-4 py-1.5 text-sm font-medium transition-colors',
              isActive(link.to)
                ? 'text-nav-700 dark:text-nav-300'
                : 'text-gray-600 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white',
            ]"
            :aria-current="isActive(link.to) ? 'page' : undefined"
            @mouseenter="hovered = i"
            @focus="hovered = i"
            @blur="hovered = null"
          >
            {{ link.label }}
          </NuxtLink>
        </nav>

        <!-- Desktop actions -->
        <div class="hidden items-center gap-2 md:flex">
          <LayoutThemeToggle />
          <NuxtLink
            v-if="authStore.isAuthenticated"
            :to="userHome"
            class="group flex items-center gap-2 rounded-full bg-gray-900/[0.04] py-1 pe-4 ps-1 text-sm font-medium text-gray-800 transition hover:bg-gray-900/[0.08] dark:bg-white/[0.06] dark:text-gray-100 dark:hover:bg-white/10"
          >
            <span class="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-primary-500 to-accent-500 text-xs font-bold text-white transition-transform group-hover:rotate-[-8deg] group-hover:scale-110">
              {{ userInitial }}
            </span>
            {{ userHomeLabel }}
          </NuxtLink>
          <template v-else>
            <button
              type="button"
              data-tour="header-login"
              class="rounded-full px-4 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-900/[0.05] hover:text-gray-900 dark:text-gray-200 dark:hover:bg-white/10 dark:hover:text-white"
              @click="onLoginClick"
            >
              ورود
            </button>
            <button
              type="button"
              class="cta-shine relative overflow-hidden rounded-full bg-gradient-to-l from-accent-500 to-primary-600 px-5 py-2 text-sm font-semibold text-white shadow-md shadow-accent-500/25 transition hover:-translate-y-0.5 hover:shadow-lg hover:shadow-accent-500/30 active:translate-y-0"
              @click="onRegisterClick"
            >
              ثبت‌نام
            </button>
          </template>
        </div>

        <!-- Mobile actions -->
        <div class="flex items-center gap-2 md:hidden">
          <LayoutThemeToggle />
          <button
            type="button"
            class="glass flex h-9 w-9 items-center justify-center rounded-full"
            :aria-label="mobileMenuOpen ? 'بستن منو' : 'باز کردن منو'"
            :aria-expanded="mobileMenuOpen"
            aria-controls="mobile-menu"
            @click="mobileMenuOpen = !mobileMenuOpen"
          >
            <span class="burger" :class="{ open: mobileMenuOpen }" aria-hidden="true">
              <span /><span /><span />
            </span>
          </button>
        </div>
      </div>

      <!-- Mobile menu -->
      <div :class="['mobile-menu grid md:hidden', mobileMenuOpen ? 'is-open' : '']" :inert="!mobileMenuOpen">
        <div class="overflow-hidden">
          <nav id="mobile-menu" class="flex flex-col gap-1 border-t border-gray-900/5 px-3 pb-4 pt-3 dark:border-white/10">
            <NuxtLink
              v-for="(link, i) in navLinks"
              :key="link.to"
              :to="link.to"
              class="menu-item flex items-center justify-between rounded-xl px-4 py-3 text-sm font-medium"
              :class="isActive(link.to) ? 'bg-nav-500/10 text-nav-700 dark:text-nav-300' : 'text-gray-700 dark:text-gray-200'"
              :style="{ transitionDelay: mobileMenuOpen ? `${60 + i * 40}ms` : '0ms' }"
            >
              {{ link.label }}
              <svg class="h-4 w-4 opacity-40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" /></svg>
            </NuxtLink>

            <div
              class="menu-item mt-2 grid gap-2"
              :class="authStore.isAuthenticated ? 'grid-cols-1' : 'grid-cols-2'"
              :style="{ transitionDelay: mobileMenuOpen ? `${60 + navLinks.length * 40}ms` : '0ms' }"
            >
              <NuxtLink
                v-if="authStore.isAuthenticated"
                :to="userHome"
                class="flex items-center justify-center gap-2 rounded-xl bg-gradient-to-l from-accent-500 to-primary-600 px-4 py-3 text-sm font-semibold text-white"
              >
                <span class="flex h-6 w-6 items-center justify-center rounded-full bg-white/25 text-xs font-bold">{{ userInitial }}</span>
                {{ userHomeLabel }}
              </NuxtLink>
              <template v-else>
                <button
                  type="button"
                  class="rounded-xl bg-gray-900/[0.05] px-4 py-3 text-sm font-medium text-gray-800 dark:bg-white/10 dark:text-gray-100"
                  @click="onLoginClick"
                >
                  ورود
                </button>
                <button
                  type="button"
                  class="rounded-xl bg-gradient-to-l from-accent-500 to-primary-600 px-4 py-3 text-sm font-semibold text-white"
                  @click="onRegisterClick"
                >
                  ثبت‌نام
                </button>
              </template>
            </div>
          </nav>
        </div>
      </div>

      <!-- Reading progress -->
      <span
        aria-hidden="true"
        class="progress-line pointer-events-none absolute inset-x-0 bottom-0 h-[2px] bg-gradient-to-l from-accent-500 via-primary-500 to-header-500"
        :style="{ transform: `scaleX(${progress})` }"
      />
    </div>
  </header>
</template>

<style scoped>
.header-lifted {
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 0.65),
    0 4px 10px -2px rgb(15 23 42 / 0.1),
    0 22px 48px -18px rgb(15 23 42 / 0.35);
}
html.dark .header-lifted {
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 0.07),
    0 4px 10px -2px rgb(0 0 0 / 0.5),
    0 22px 48px -18px rgb(0 0 0 / 0.75);
}

.nav-pill {
  transition:
    left 0.35s cubic-bezier(0.22, 1, 0.36, 1),
    width 0.35s cubic-bezier(0.22, 1, 0.36, 1),
    opacity 0.2s ease;
}

/* RTL: the bar fills from the right, where reading starts. */
.progress-line {
  transform-origin: right;
  transition: transform 0.1s linear;
}

/* A highlight that sweeps across the register button on hover. */
.cta-shine::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(110deg, transparent 30%, rgb(255 255 255 / 0.45) 50%, transparent 70%);
  transform: translateX(-120%);
  transition: transform 0.7s ease;
}
.cta-shine:hover::after {
  transform: translateX(120%);
}

/* Hamburger that folds into an X. */
.burger {
  position: relative;
  display: block;
  width: 18px;
  height: 12px;
}
.burger span {
  position: absolute;
  inset-inline: 0;
  height: 2px;
  border-radius: 2px;
  background: currentColor;
  transition: transform 0.3s cubic-bezier(0.22, 1, 0.36, 1), opacity 0.2s ease, top 0.3s cubic-bezier(0.22, 1, 0.36, 1);
}
.burger span:nth-child(1) { top: 0; }
.burger span:nth-child(2) { top: 5px; }
.burger span:nth-child(3) { top: 10px; }
.burger.open span:nth-child(1) { top: 5px; transform: rotate(45deg); }
.burger.open span:nth-child(2) { opacity: 0; transform: scaleX(0.3); }
.burger.open span:nth-child(3) { top: 5px; transform: rotate(-45deg); }

/* Height animates via the 0fr → 1fr grid-row trick, no JS measuring. */
.mobile-menu {
  grid-template-rows: 0fr;
  transition: grid-template-rows 0.35s cubic-bezier(0.22, 1, 0.36, 1);
}
.mobile-menu.is-open {
  grid-template-rows: 1fr;
}
.menu-item {
  opacity: 0;
  transform: translateY(-6px);
  transition: opacity 0.25s ease, transform 0.3s cubic-bezier(0.22, 1, 0.36, 1);
}
.mobile-menu.is-open .menu-item {
  opacity: 1;
  transform: none;
}

@media (prefers-reduced-motion: reduce) {
  .nav-pill,
  .progress-line,
  .cta-shine::after,
  .burger span,
  .mobile-menu,
  .menu-item {
    transition: none !important;
  }
}
</style>
