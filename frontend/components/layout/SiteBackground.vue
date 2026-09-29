<script setup lang="ts">
// Site-wide animated backdrop, chosen by the owner in «تنظیمات سایت».
// Mounted once in app.vue behind every layout. Layers drift on their own
// and, on devices with a mouse, lean slightly toward the pointer (parallax)
// so the whole page feels alive rather than printed.
const { background } = useSiteBackground()

// Owner colors, else the theme's primary/accent ramps.
const colorVars = computed(() => {
  const [c1, c2, c3] = background.value.colors
  return {
    '--bg-1': c1 || 'rgb(var(--c-primary-500))',
    '--bg-2': c2 || 'rgb(var(--c-accent-500))',
    '--bg-3': c3 || c1 || 'rgb(var(--c-primary-300))',
  }
})

// Deterministic "random" particles (same on server and client, no hydration mismatch).
const particles = (() => {
  let seed = 7
  const rand = () => ((seed = (seed * 16807) % 2147483647) / 2147483647)
  return Array.from({ length: 34 }, (_, i) => ({
    left: `${(rand() * 100).toFixed(2)}%`,
    size: `${(3 + rand() * 7).toFixed(1)}px`,
    duration: `${(14 + rand() * 18).toFixed(1)}s`,
    delay: `-${(rand() * 30).toFixed(1)}s`,
    drift: `${((rand() - 0.5) * 120).toFixed(0)}px`,
    color: `var(--bg-${(i % 3) + 1})`,
  }))
})()

const root = ref<HTMLElement | null>(null)
let frame = 0
function onPointerMove(e: PointerEvent) {
  if (!background.value.motion || frame) return
  frame = requestAnimationFrame(() => {
    frame = 0
    const x = (e.clientX / window.innerWidth) * 2 - 1
    const y = (e.clientY / window.innerHeight) * 2 - 1
    root.value?.style.setProperty('--px', x.toFixed(3))
    root.value?.style.setProperty('--py', y.toFixed(3))
  })
}

onMounted(() => {
  const finePointer = window.matchMedia('(pointer: fine)').matches
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  if (finePointer && !reduced) window.addEventListener('pointermove', onPointerMove, { passive: true })
})
onBeforeUnmount(() => {
  window.removeEventListener('pointermove', onPointerMove)
  if (frame) cancelAnimationFrame(frame)
})
</script>

<template>
  <div
    ref="root"
    aria-hidden="true"
    :class="['site-bg pointer-events-none fixed inset-0 -z-10 overflow-hidden', { 'is-still': !background.motion }]"
    :style="colorVars"
  >
    <!-- شفق -->
    <template v-if="background.style === 'aurora'">
      <div class="layer depth-1">
        <div class="blob aurora-a" style="top: -12%; right: -8%; width: 42rem; height: 42rem; background: var(--bg-1)" />
      </div>
      <div class="layer depth-2">
        <div class="blob aurora-b" style="top: 30%; left: -14%; width: 38rem; height: 38rem; background: var(--bg-2)" />
      </div>
      <div class="layer depth-3">
        <div class="blob aurora-c" style="bottom: -18%; right: 22%; width: 34rem; height: 34rem; background: var(--bg-3)" />
      </div>
      <div class="layer depth-2">
        <div class="blob aurora-a" style="top: 8%; left: 30%; width: 22rem; height: 22rem; background: var(--bg-2); animation-delay: -9s" />
      </div>
    </template>

    <!-- گرادیان روان -->
    <div
      v-else-if="background.style === 'gradient'"
      class="flowing-gradient absolute -inset-[10%]"
    />

    <!-- موج -->
    <template v-else-if="background.style === 'waves'">
      <div class="layer depth-1">
        <div class="blob aurora-b" style="top: -15%; left: 10%; width: 36rem; height: 36rem; background: var(--bg-1)" />
      </div>
      <div class="absolute inset-x-0 bottom-0 h-[45vh]">
        <svg v-for="(wave, i) in 3" :key="i" :class="['wave', `wave-${i + 1}`]" viewBox="0 0 2880 320" preserveAspectRatio="none">
          <path
            d="M0,160 C240,220 480,100 720,160 C960,220 1200,100 1440,160 C1680,220 1920,100 2160,160 C2400,220 2640,100 2880,160 L2880,320 L0,320 Z"
            :style="{ fill: `var(--bg-${i + 1})` }"
          />
        </svg>
      </div>
    </template>

    <!-- ذرات شناور -->
    <template v-else-if="background.style === 'particles'">
      <div class="layer depth-1">
        <div class="blob aurora-c" style="top: 20%; left: 25%; width: 40rem; height: 40rem; background: var(--bg-1); opacity: 0.18" />
      </div>
      <div class="layer depth-2">
        <span
          v-for="(p, i) in particles"
          :key="i"
          class="particle"
          :style="{
            left: p.left,
            width: p.size,
            height: p.size,
            background: p.color,
            animationDuration: p.duration,
            animationDelay: p.delay,
            '--drift': p.drift,
          }"
        />
      </div>
    </template>

    <!-- عکس دلخواه -->
    <template v-else-if="background.style === 'image' && background.image">
      <div class="layer depth-1 absolute -inset-[6%]">
        <div class="ken-burns absolute inset-0 bg-cover bg-center" :style="{ backgroundImage: `url(${background.image})` }" />
      </div>
      <div class="image-veil absolute inset-0" />
    </template>
  </div>
</template>

<style scoped>
.site-bg {
  --px: 0;
  --py: 0;
}

/* Parallax: deeper layers move less. */
.layer {
  position: absolute;
  inset: 0;
  transition: transform 1.2s cubic-bezier(0.22, 1, 0.36, 1);
}
.depth-1 { transform: translate3d(calc(var(--px) * -14px), calc(var(--py) * -10px), 0); }
.depth-2 { transform: translate3d(calc(var(--px) * -28px), calc(var(--py) * -20px), 0); }
.depth-3 { transform: translate3d(calc(var(--px) * -44px), calc(var(--py) * -30px), 0); }

.blob {
  position: absolute;
  border-radius: 9999px;
  filter: blur(80px);
  opacity: 0.35;
}
html.dark .blob {
  opacity: 0.22;
}
.aurora-a { animation: aurora-a 22s ease-in-out infinite; }
.aurora-b { animation: aurora-b 28s ease-in-out infinite; }
.aurora-c { animation: aurora-c 25s ease-in-out infinite; }
@keyframes aurora-a {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(-12vw, 10vh) scale(1.15); }
  66% { transform: translate(6vw, 18vh) scale(0.9); }
}
@keyframes aurora-b {
  0%, 100% { transform: translate(0, 0) scale(1); }
  40% { transform: translate(16vw, -8vh) scale(1.2); }
  70% { transform: translate(8vw, 12vh) scale(0.95); }
}
@keyframes aurora-c {
  0%, 100% { transform: translate(0, 0) scale(1.05); }
  50% { transform: translate(-14vw, -14vh) scale(0.85); }
}

.flowing-gradient {
  background: linear-gradient(120deg, var(--bg-1), var(--bg-2), var(--bg-3), var(--bg-1));
  background-size: 300% 300%;
  opacity: 0.28;
  animation: flow 24s ease-in-out infinite;
  transform: translate3d(calc(var(--px) * -24px), calc(var(--py) * -18px), 0);
  transition: transform 1.2s cubic-bezier(0.22, 1, 0.36, 1);
}
html.dark .flowing-gradient {
  opacity: 0.2;
}
@keyframes flow {
  0%, 100% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
}

.wave {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 200%;
  height: 100%;
  animation: wave-move linear infinite;
}
.wave-1 { opacity: 0.16; animation-duration: 26s; height: 100%; }
.wave-2 { opacity: 0.14; animation-duration: 19s; animation-direction: reverse; height: 80%; }
.wave-3 { opacity: 0.12; animation-duration: 14s; height: 60%; }
html.dark .wave { filter: brightness(0.8); }
@keyframes wave-move {
  from { transform: translateX(0); }
  to { transform: translateX(-50%); }
}

.particle {
  position: absolute;
  bottom: -20px;
  border-radius: 9999px;
  opacity: 0;
  box-shadow: 0 0 12px currentColor;
  animation-name: rise;
  animation-timing-function: linear;
  animation-iteration-count: infinite;
}
@keyframes rise {
  0% { transform: translate3d(0, 0, 0); opacity: 0; }
  10% { opacity: 0.7; }
  90% { opacity: 0.5; }
  100% { transform: translate3d(var(--drift), -110vh, 0); opacity: 0; }
}

.ken-burns {
  animation: ken-burns 40s ease-in-out infinite alternate;
}
@keyframes ken-burns {
  from { transform: scale(1.05) translate(0, 0); }
  to { transform: scale(1.18) translate(-2%, -3%); }
}
.image-veil {
  background: rgb(243 244 246 / 0.72);
}
html.dark .image-veil {
  background: rgb(10 12 15 / 0.72);
}

.is-still *,
.is-still .flowing-gradient {
  animation-play-state: paused !important;
}

@media (prefers-reduced-motion: reduce) {
  .site-bg *,
  .flowing-gradient {
    animation-play-state: paused !important;
  }
}
</style>
