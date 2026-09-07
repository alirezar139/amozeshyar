<script setup lang="ts">
const { isTouring, stepIndex, stepsForRoute, next, prev, endTour } = useGuide()

const rect = ref<DOMRect | null>(null)
const tooltipStyle = ref<Record<string, string>>({})
const currentStep = computed(() => stepsForRoute.value[stepIndex.value])

let targetEl: Element | null = null

function measure() {
  if (!targetEl) return
  rect.value = targetEl.getBoundingClientRect()
  positionTooltip()
}

function locateTarget() {
  const step = currentStep.value
  if (!step) return
  const el = document.querySelector(step.selector)
  targetEl = el
  if (!el) {
    rect.value = null
    return
  }
  // Measure immediately (covers the common case where the element is
  // already in view, no scroll needed) and then keep measuring on every
  // scroll tick — smooth-scroll animations don't resolve on a fixed
  // timer, so a one-shot delayed measurement can catch the element
  // mid-flight and draw the box at the wrong spot.
  measure()
  el.scrollIntoView({ block: 'center', behavior: 'smooth' })
}

function positionTooltip() {
  if (!rect.value) return
  const spaceBelow = window.innerHeight - rect.value.bottom
  const top = spaceBelow > 180 ? rect.value.bottom + 14 : Math.max(14, rect.value.top - 174)
  tooltipStyle.value = {
    top: `${top}px`,
    left: `${Math.min(Math.max(rect.value.left, 16), window.innerWidth - 336)}px`,
  }
}

watch([stepIndex, isTouring], () => {
  if (isTouring.value) locateTarget()
})
onMounted(() => {
  if (isTouring.value) locateTarget()
  window.addEventListener('resize', measure)
  window.addEventListener('scroll', measure, { passive: true, capture: true })
})
onUnmounted(() => {
  window.removeEventListener('resize', measure)
  window.removeEventListener('scroll', measure, true)
})
</script>

<template>
  <Teleport to="body">
    <div v-if="isTouring && currentStep" class="fixed inset-0 z-[100]">
      <!-- Spotlight: the highlight box's own giant box-shadow dims everything
           else, so no separate backdrop element or clip-path is needed. -->
      <div
        v-if="rect"
        class="pointer-events-none absolute rounded-lg ring-2 ring-accent-500 transition-all duration-300"
        :style="{
          top: `${rect.top - 6}px`,
          left: `${rect.left - 6}px`,
          width: `${rect.width + 12}px`,
          height: `${rect.height + 12}px`,
          boxShadow: '0 0 0 9999px rgb(0 0 0 / 0.6)',
        }"
      />
      <div v-else class="absolute inset-0 bg-black/60" />

      <div class="glass absolute w-80 max-w-[90vw] rounded-xl p-4" :style="tooltipStyle">
        <p class="text-xs font-medium text-primary-600 dark:text-primary-400">
          مرحله {{ stepIndex + 1 }} از {{ stepsForRoute.length }}
        </p>
        <h3 class="mt-1 font-semibold text-gray-900 dark:text-white">{{ currentStep.title }}</h3>
        <p class="mt-1 text-sm text-gray-600 dark:text-gray-300">{{ currentStep.text }}</p>
        <div class="mt-3 flex items-center justify-between">
          <button type="button" class="text-xs text-gray-500 hover:underline dark:text-gray-400" @click="endTour">
            پایان تور
          </button>
          <div class="flex gap-2">
            <button
              v-if="stepIndex > 0"
              type="button"
              class="glass rounded-md px-3 py-1.5 text-xs text-gray-700 dark:text-gray-200"
              @click="prev"
            >
              قبلی
            </button>
            <button
              type="button"
              class="rounded-md bg-primary-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-primary-500"
              @click="next"
            >
              {{ stepIndex === stepsForRoute.length - 1 ? 'پایان' : 'بعدی' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
