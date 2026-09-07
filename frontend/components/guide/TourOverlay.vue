<script setup lang="ts">
const { isTouring, stepIndex, stepsForRoute, isAutoPlaying, next, prev, endTour, toggleAutoPlay } = useGuide()
const { enabled: speechEnabled, supported: speechSupported, isLoading: speechLoading, loadProgress: speechProgress, speak, stop: stopSpeech, toggle: toggleSpeech } = useSpeech()

// How long to linger on a step before auto-advancing. Scaled to how much
// there is to read/hear (at the slowed-down 0.8x speech rate) instead of a
// flat duration — a one-line step and a five-line step shouldn't get the
// same amount of time.
const MIN_STEP_MS = 14000
const MS_PER_CHAR = 140

const rect = ref<DOMRect | null>(null)
const currentStep = computed(() => stepsForRoute.value[stepIndex.value])
const currentDurationMs = computed(() => {
  const step = currentStep.value
  if (!step) return MIN_STEP_MS
  return Math.max(MIN_STEP_MS, (step.title.length + step.text.length) * MS_PER_CHAR)
})
let targetEl: Element | null = null

function measure() {
  if (!targetEl) return
  rect.value = targetEl.getBoundingClientRect()
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
  // Instant scroll, not smooth: there's no fixed duration to wait out for
  // a smooth-scroll animation, and re-measuring on every scroll tick to
  // track it just made the highlight box chase a moving target and
  // re-trigger its transition dozens of times a second. Jump straight
  // there and measure once (plus one rAF later in case the browser
  // defers layout a frame).
  el.scrollIntoView({ block: 'center', behavior: 'auto' })
  measure()
  requestAnimationFrame(measure)
}

// Auto-advance: the tour narrates itself by default. Keyed on stepIndex
// so both an automatic and a manual (prev/next click) step change reset
// the countdown the same way — no special-casing which kind of change
// it was.
let autoTimer: ReturnType<typeof setTimeout> | null = null
function clearAutoTimer() {
  if (autoTimer) clearTimeout(autoTimer)
  autoTimer = null
}
function scheduleAuto() {
  clearAutoTimer()
  if (!isAutoPlaying.value || !isTouring.value) return
  autoTimer = setTimeout(next, currentDurationMs.value)
}

function narrateCurrentStep() {
  const step = currentStep.value
  if (!step) return
  speak(`${step.title}. ${step.text}`)
}

// The bottom panel (title/text/controls) is a *fixed* element, not
// positioned relative to the highlighted part — after three rounds of
// bugs in a dynamically-positioned tooltip (jitter, off-screen clamps,
// a CSS specificity fight), the actual explanatory text is now
// completely decoupled from that measurement logic and can never fail
// to show just because a position calculation went wrong. Only the
// spotlight box around the target element still needs `rect`.
watch([stepIndex, isTouring], () => {
  if (isTouring.value) {
    locateTarget()
    narrateCurrentStep()
  } else {
    stopSpeech()
  }
})
watch([stepIndex, isTouring, isAutoPlaying], scheduleAuto)

onMounted(() => {
  if (isTouring.value) {
    locateTarget()
    scheduleAuto()
    narrateCurrentStep()
  }
  window.addEventListener('resize', measure)
})
onUnmounted(() => {
  clearAutoTimer()
  stopSpeech()
  window.removeEventListener('resize', measure)
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

      <!-- Always fixed to the bottom of the viewport — same spot every
           step, on every page, regardless of where the highlighted part
           happens to be. -->
      <div class="glass absolute inset-x-4 bottom-4 mx-auto max-w-md overflow-hidden rounded-xl p-4 sm:inset-x-auto sm:left-1/2 sm:-translate-x-1/2">
        <div class="absolute inset-x-0 top-0 h-1 bg-black/10 dark:bg-white/10">
          <div
            :key="stepIndex"
            class="h-full bg-accent-500"
            :class="isAutoPlaying ? 'animate-tour-progress' : ''"
            :style="isAutoPlaying ? { animationDuration: `${currentDurationMs}ms` } : { width: '100%' }"
          />
        </div>

        <div class="flex items-center justify-between pt-1">
          <p class="text-xs font-medium text-primary-600 dark:text-primary-400">
            مرحله {{ stepIndex + 1 }} از {{ stepsForRoute.length }}
          </p>
          <div class="flex items-center gap-2">
            <button
              v-if="speechSupported"
              type="button"
              :aria-label="speechEnabled ? 'قطع صدای راهنما' : 'فعال کردن صدای راهنما'"
              class="text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-white"
              @click="toggleSpeech(); speechEnabled && narrateCurrentStep()"
            >
              <svg v-if="speechEnabled" class="h-4 w-4" fill="currentColor" viewBox="0 0 20 20"><path d="M9.383 3.076A1 1 0 0110 4v12a1 1 0 01-1.707.707L4.586 13H2a1 1 0 01-1-1V8a1 1 0 011-1h2.586l3.707-3.707a1 1 0 011.09-.217zM14.657 2.929a1 1 0 011.414 0A9.972 9.972 0 0119 10a9.972 9.972 0 01-2.929 7.071 1 1 0 11-1.414-1.414A7.971 7.971 0 0017 10c0-2.21-.894-4.208-2.343-5.657a1 1 0 010-1.414zm-2.829 2.828a1 1 0 011.415 0A5.983 5.983 0 0115 10a5.983 5.983 0 01-1.757 4.243 1 1 0 11-1.415-1.415A3.987 3.987 0 0013 10a3.987 3.987 0 00-1.172-2.828 1 1 0 010-1.415z" /></svg>
              <svg v-else class="h-4 w-4" fill="currentColor" viewBox="0 0 20 20"><path d="M9.383 3.076A1 1 0 0110 4v12a1 1 0 01-1.707.707L4.586 13H2a1 1 0 01-1-1V8a1 1 0 011-1h2.586l3.707-3.707a1 1 0 011.09-.217zM12.293 7.293a1 1 0 011.414 0L15 8.586l1.293-1.293a1 1 0 111.414 1.414L16.414 10l1.293 1.293a1 1 0 01-1.414 1.414L15 11.414l-1.293 1.293a1 1 0 01-1.414-1.414L13.586 10l-1.293-1.293a1 1 0 010-1.414z" /></svg>
            </button>
            <button
              type="button"
              :aria-label="isAutoPlaying ? 'توقف پخش خودکار' : 'ادامه‌ی پخش خودکار'"
              class="text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-white"
              @click="toggleAutoPlay"
            >
              <svg v-if="isAutoPlaying" class="h-4 w-4" fill="currentColor" viewBox="0 0 20 20"><path d="M5 4h3v12H5V4zm7 0h3v12h-3V4z" /></svg>
              <svg v-else class="h-4 w-4" fill="currentColor" viewBox="0 0 20 20"><path d="M6 4l10 6-10 6V4z" /></svg>
            </button>
          </div>
        </div>
        <h3 class="mt-1 font-semibold text-gray-900 dark:text-white">{{ currentStep.title }}</h3>
        <p class="mt-1 text-sm text-gray-600 dark:text-gray-300">{{ currentStep.text }}</p>
        <p v-if="speechEnabled && speechLoading" class="mt-1 flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
          <svg class="h-3.5 w-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" /><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" /></svg>
          <span v-if="speechProgress > 0 && speechProgress < 100">در حال آماده‌سازی صدای فارسی — فقط بار اول ({{ speechProgress }}٪)...</span>
          <span v-else>در حال آماده‌سازی صدای فارسی...</span>
        </p>
        <div class="mt-3 flex items-center justify-between">
          <button type="button" class="text-xs font-medium text-red-600 hover:underline dark:text-red-400" @click="endTour">
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

<style scoped>
@keyframes tour-progress {
  from { width: 0%; }
  to { width: 100%; }
}
.animate-tour-progress {
  animation-name: tour-progress;
  animation-timing-function: linear;
  animation-fill-mode: forwards;
}
@media (prefers-reduced-motion: reduce) {
  .animate-tour-progress { animation: none; width: 100%; }
}
</style>
