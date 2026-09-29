<script setup lang="ts">
import { SHADER_EFFECTS } from '~/utils/shaders'

// Site-wide animated backdrop, chosen by the owner in «تنظیمات سایت».
// Mounted once in app.vue behind every layout. Layers drift on their own
// and, on devices with a mouse, lean slightly toward the pointer (parallax)
// so the whole page feels alive rather than printed. Every duration is
// multiplied by --dur, which the owner's speed setting controls.
const { background } = useSiteBackground()

const SPEED: Record<string, number> = { slow: 2.2, normal: 1.4, fast: 0.85 }
const LANDSCAPES = ['mountains', 'clouds', 'ocean', 'forest', 'dunes']
const FALLING = ['sakura', 'leaves', 'snow', 'rain', 'fireflies']

// Owner colors, else the theme's primary/accent ramps.
const rootStyle = computed(() => {
  const [c1, c2, c3] = background.value.colors
  return {
    '--bg-1': c1 || 'rgb(var(--c-primary-500))',
    '--bg-2': c2 || 'rgb(var(--c-accent-500))',
    '--bg-3': c3 || c1 || 'rgb(var(--c-primary-300))',
    '--dur': String(SPEED[background.value.speed] ?? SPEED.slow),
  }
})

// Deterministic "random" layouts (same on server and client, no hydration mismatch).
function seeded(seed: number) {
  return () => ((seed = (seed * 16807) % 2147483647) / 2147483647)
}

const dandelions = (() => {
  const rand = seeded(7)
  return Array.from({ length: 22 }, (_, i) => ({
    left: `${(rand() * 100).toFixed(1)}%`,
    size: 18 + rand() * 26,
    duration: 26 + rand() * 22,
    delay: -(rand() * 48),
    drift: `${((rand() - 0.5) * 220).toFixed(0)}px`,
    spin: `${((rand() - 0.5) * 540).toFixed(0)}deg`,
    sway: 4 + rand() * 4,
    color: `var(--bg-${(i % 3) + 1})`,
  }))
})()
// The seed's radiating filaments (a half-circle fan), precomputed once.
const filaments = Array.from({ length: 13 }, (_, a) => {
  const angle = (Math.PI * a) / 12 + Math.PI
  return { x: +(20 + 17 * Math.cos(angle)).toFixed(2), y: +(20 + 17 * Math.sin(angle)).toFixed(2) }
})

const stars = (() => {
  const rand = seeded(11)
  return Array.from({ length: 70 }, (_, i) => ({
    top: `${(rand() * 100).toFixed(1)}%`,
    left: `${(rand() * 100).toFixed(1)}%`,
    size: 1.5 + rand() * 2.5,
    duration: 3 + rand() * 5,
    delay: -(rand() * 8),
    color: i % 5 === 0 ? 'var(--bg-2)' : i % 3 === 0 ? 'var(--bg-3)' : 'var(--bg-1)',
  }))
})()

const bokeh = (() => {
  const rand = seeded(23)
  return Array.from({ length: 16 }, (_, i) => ({
    top: `${(rand() * 100).toFixed(1)}%`,
    left: `${(rand() * 100).toFixed(1)}%`,
    size: 60 + rand() * 170,
    duration: 18 + rand() * 20,
    delay: -(rand() * 30),
    dx: `${((rand() - 0.5) * 16).toFixed(1)}vw`,
    dy: `${((rand() - 0.5) * 16).toFixed(1)}vh`,
    color: `var(--bg-${(i % 3) + 1})`,
  }))
})()

const shapes = (() => {
  const rand = seeded(41)
  const kinds = ['circle', 'square', 'triangle', 'plus', 'ring'] as const
  return Array.from({ length: 16 }, (_, i) => ({
    kind: kinds[i % kinds.length],
    top: `${(rand() * 100).toFixed(1)}%`,
    left: `${(rand() * 100).toFixed(1)}%`,
    size: 22 + rand() * 46,
    duration: 22 + rand() * 20,
    delay: -(rand() * 40),
    dy: `${(-(20 + rand() * 40)).toFixed(0)}px`,
    spin: `${(rand() > 0.5 ? 1 : -1) * (90 + Math.round(rand() * 180))}deg`,
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
  if (window.matchMedia('(pointer: fine)').matches) window.addEventListener('pointermove', onPointerMove, { passive: true })
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
    :style="rootStyle"
  >
    <!-- زنده (WebGL) -->
    <BackgroundShader
      v-if="(SHADER_EFFECTS as string[]).includes(background.style)"
      :effect="(background.style as any)"
      :colors="background.colors"
      :motion="background.motion"
      :speed="SPEED[background.speed] ?? SPEED.slow"
    />

    <!-- شفق -->
    <template v-else-if="background.style === 'aurora'">
      <div class="layer depth-1">
        <div class="blob aurora-a" style="top: -12%; right: -8%; width: 42rem; height: 42rem; --c: var(--bg-1)" />
      </div>
      <div class="layer depth-2">
        <div class="blob aurora-b" style="top: 30%; left: -14%; width: 38rem; height: 38rem; --c: var(--bg-2)" />
      </div>
      <div class="layer depth-3">
        <div class="blob aurora-c" style="bottom: -18%; right: 22%; width: 34rem; height: 34rem; --c: var(--bg-3)" />
      </div>
      <div class="layer depth-2">
        <div class="blob aurora-a" style="top: 8%; left: 30%; width: 22rem; height: 22rem; --c: var(--bg-2); animation-delay: calc(-9s * var(--dur))" />
      </div>
    </template>

    <!-- گرادیان روان -->
    <div v-else-if="background.style === 'gradient'" class="flowing-gradient absolute -inset-[10%]" />

    <!-- موج -->
    <template v-else-if="background.style === 'waves'">
      <div class="layer depth-1">
        <div class="blob aurora-b" style="top: -15%; left: 10%; width: 36rem; height: 36rem; --c: var(--bg-1)" />
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

    <!-- قاصدک -->
    <template v-else-if="background.style === 'particles'">
      <div class="layer depth-1">
        <div class="blob aurora-c" style="top: 20%; left: 25%; width: 40rem; height: 40rem; --c: var(--bg-1); opacity: 0.25" />
      </div>
      <div class="layer depth-2">
        <span
          v-for="(d, i) in dandelions"
          :key="i"
          class="seed"
          :style="{
            left: d.left,
            width: `${d.size}px`,
            height: `${d.size * 1.6}px`,
            color: d.color,
            animationDuration: `calc(${d.duration}s * var(--dur))`,
            animationDelay: `calc(${d.delay}s * var(--dur))`,
            '--drift': d.drift,
            '--spin': d.spin,
          }"
        >
          <svg viewBox="0 0 40 64" class="seed-sway h-full w-full" :style="{ animationDuration: `calc(${d.sway}s * var(--dur))` }">
            <!-- pappus: fine radiating filaments with tiny tips -->
            <g stroke="currentColor" stroke-width="0.7" stroke-linecap="round" opacity="0.85">
              <line v-for="(f, a) in filaments" :key="a" x1="20" y1="20" :x2="f.x" :y2="f.y" />
            </g>
            <g fill="currentColor" opacity="0.9">
              <circle v-for="(f, a) in filaments" :key="a" :cx="f.x" :cy="f.y" r="0.9" />
            </g>
            <!-- stalk and seed -->
            <line x1="20" y1="20" x2="20" y2="54" stroke="currentColor" stroke-width="0.9" />
            <ellipse cx="20" cy="57" rx="2" ry="5" fill="currentColor" />
          </svg>
        </span>
      </div>
    </template>

    <!-- آسمان پرستاره -->
    <template v-else-if="background.style === 'stars'">
      <div class="layer depth-1">
        <div class="blob aurora-a" style="top: -20%; left: -10%; width: 44rem; height: 44rem; --c: var(--bg-1); opacity: 0.25" />
        <div class="blob aurora-b" style="bottom: -25%; right: -10%; width: 40rem; height: 40rem; --c: var(--bg-2); opacity: 0.2" />
      </div>
      <div class="layer depth-3">
        <div class="star-field absolute inset-0">
          <span
            v-for="(s, i) in stars"
            :key="i"
            class="star"
            :style="{
              top: s.top,
              left: s.left,
              width: `${s.size}px`,
              height: `${s.size}px`,
              background: s.color,
              color: s.color,
              animationDuration: `calc(${s.duration}s * var(--dur))`,
              animationDelay: `calc(${s.delay}s * var(--dur))`,
            }"
          />
        </div>
      </div>
      <span class="shooting-star" />
    </template>

    <!-- بوکه -->
    <template v-else-if="background.style === 'bokeh'">
      <div class="layer depth-2">
        <span
          v-for="(b, i) in bokeh"
          :key="i"
          class="bokeh"
          :style="{
            top: b.top,
            left: b.left,
            width: `${b.size}px`,
            height: `${b.size}px`,
            '--c': b.color,
            '--dx': b.dx,
            '--dy': b.dy,
            animationDuration: `calc(${b.duration}s * var(--dur))`,
            animationDelay: `calc(${b.delay}s * var(--dur))`,
          }"
        />
      </div>
    </template>

    <!-- اشکال هندسی -->
    <template v-else-if="background.style === 'shapes'">
      <div class="layer depth-2">
        <span
          v-for="(s, i) in shapes"
          :key="i"
          class="shape"
          :style="{
            top: s.top,
            left: s.left,
            width: `${s.size}px`,
            height: `${s.size}px`,
            color: s.color,
            '--dy': s.dy,
            '--spin': s.spin,
            animationDuration: `calc(${s.duration}s * var(--dur))`,
            animationDelay: `calc(${s.delay}s * var(--dur))`,
          }"
        >
          <svg viewBox="0 0 40 40" class="h-full w-full" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linejoin="round">
            <circle v-if="s.kind === 'circle'" cx="20" cy="20" r="16" fill="currentColor" fill-opacity="0.12" />
            <rect v-else-if="s.kind === 'square'" x="6" y="6" width="28" height="28" rx="6" fill="currentColor" fill-opacity="0.12" />
            <path v-else-if="s.kind === 'triangle'" d="M20 5 L35 33 L5 33 Z" fill="currentColor" fill-opacity="0.12" />
            <path v-else-if="s.kind === 'plus'" d="M20 6 V34 M6 20 H34" stroke-linecap="round" stroke-width="4" />
            <circle v-else cx="20" cy="20" r="14" stroke-width="4" />
          </svg>
        </span>
      </div>
    </template>

    <!-- نوارهای نور -->
    <template v-else-if="background.style === 'ribbons'">
      <div class="layer depth-1">
        <div class="blob aurora-c" style="top: 10%; right: 10%; width: 36rem; height: 36rem; --c: var(--bg-2); opacity: 0.2" />
      </div>
      <div class="layer depth-2">
        <svg v-for="(r, i) in 3" :key="i" :class="['ribbon', `ribbon-${i + 1}`]" viewBox="0 0 2880 400" preserveAspectRatio="none" fill="none">
          <defs>
            <linearGradient :id="`ribbon-grad-${i}`" x1="0" x2="1">
              <stop offset="0" stop-color="currentColor" stop-opacity="0" />
              <stop offset="0.5" stop-color="currentColor" stop-opacity="0.9" />
              <stop offset="1" stop-color="currentColor" stop-opacity="0" />
            </linearGradient>
          </defs>
          <path
            d="M0,200 C360,60 720,340 1080,200 C1440,60 1800,340 2160,200 C2520,60 2880,340 3240,200"
            :stroke="`url(#ribbon-grad-${i})`"
            :stroke-width="[70, 40, 22][i]"
            stroke-linecap="round"
            :style="{ color: `var(--bg-${i + 1})` }"
          />
        </svg>
      </div>
    </template>

    <!-- شبکه -->
    <template v-else-if="background.style === 'grid'">
      <div class="layer depth-1">
        <div class="blob aurora-a" style="top: -10%; left: 20%; width: 40rem; height: 40rem; --c: var(--bg-1); opacity: 0.3" />
      </div>
      <div class="grid-floor" />
      <div class="grid-horizon" />
    </template>

    <!-- طبیعت: منظره‌ها و ریزش‌ها -->
    <BackgroundLandscape v-else-if="LANDSCAPES.includes(background.style)" :scene="(background.style as any)" />
    <BackgroundFalling v-else-if="FALLING.includes(background.style)" :kind="(background.style as any)" />

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
  --dur: 2.2;
}

/* Parallax: deeper layers move more; a long ease keeps it floaty. */
.layer {
  position: absolute;
  inset: 0;
  transition: transform 2.4s cubic-bezier(0.22, 1, 0.36, 1);
}
.depth-1 { transform: translate3d(calc(var(--px) * -12px), calc(var(--py) * -8px), 0); }
.depth-2 { transform: translate3d(calc(var(--px) * -24px), calc(var(--py) * -16px), 0); }
.depth-3 { transform: translate3d(calc(var(--px) * -38px), calc(var(--py) * -26px), 0); }

/* A radial gradient instead of filter: blur() — same soft glow, but a
   blur over elements this large and always moving kept the GPU busy
   repainting and made scrolling janky on modest machines. */
.blob {
  position: absolute;
  border-radius: 9999px;
  background: radial-gradient(closest-side, var(--c), transparent);
  opacity: 0.5;
  will-change: transform;
}
html.dark .blob {
  opacity: 0.32;
}
.aurora-a { animation: aurora-a calc(22s * var(--dur)) ease-in-out infinite; }
.aurora-b { animation: aurora-b calc(28s * var(--dur)) ease-in-out infinite; }
.aurora-c { animation: aurora-c calc(25s * var(--dur)) ease-in-out infinite; }
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
  animation: flow calc(24s * var(--dur)) ease-in-out infinite;
  transform: translate3d(calc(var(--px) * -24px), calc(var(--py) * -18px), 0);
  transition: transform 2.4s cubic-bezier(0.22, 1, 0.36, 1);
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
.wave-1 { opacity: 0.16; animation-duration: calc(26s * var(--dur)); height: 100%; }
.wave-2 { opacity: 0.14; animation-duration: calc(19s * var(--dur)); animation-direction: reverse; height: 80%; }
.wave-3 { opacity: 0.12; animation-duration: calc(14s * var(--dur)); height: 60%; }
html.dark .wave { filter: brightness(0.8); }
@keyframes wave-move {
  from { transform: translateX(0); }
  to { transform: translateX(-50%); }
}

/* ---- dandelion seeds ---- */
.seed {
  position: absolute;
  bottom: -80px;
  opacity: 0;
  animation-name: seed-rise;
  animation-timing-function: linear;
  animation-iteration-count: infinite;
}
.seed-sway {
  animation: seed-sway ease-in-out infinite alternate;
  transform-origin: 50% 90%;
}
@keyframes seed-rise {
  0% { transform: translate3d(0, 0, 0) rotate(0deg); opacity: 0; }
  8% { opacity: 0.75; }
  85% { opacity: 0.6; }
  100% { transform: translate3d(var(--drift), -115vh, 0) rotate(var(--spin)); opacity: 0; }
}
@keyframes seed-sway {
  from { transform: rotate(-14deg) translateX(-6px); }
  to { transform: rotate(14deg) translateX(6px); }
}

/* ---- stars ---- */
.star {
  position: absolute;
  border-radius: 9999px;
  box-shadow: 0 0 6px currentColor;
  animation: twinkle ease-in-out infinite;
}
@keyframes twinkle {
  0%, 100% { opacity: 0.15; transform: scale(0.7); }
  50% { opacity: 0.9; transform: scale(1.2); }
}
.star-field {
  animation: star-drift calc(120s * var(--dur)) linear infinite alternate;
}
@keyframes star-drift {
  from { transform: translate(0, 0); }
  to { transform: translate(-3vw, 2vh); }
}
.shooting-star {
  position: absolute;
  top: 12%;
  left: 70%;
  width: 140px;
  height: 2px;
  border-radius: 9999px;
  background: linear-gradient(90deg, var(--bg-1), transparent);
  opacity: 0;
  animation: shoot calc(14s * var(--dur)) ease-in infinite;
}
@keyframes shoot {
  0%, 88% { opacity: 0; transform: translate(0, 0) rotate(-25deg); }
  90% { opacity: 0.9; }
  100% { opacity: 0; transform: translate(-40vw, 20vh) rotate(-25deg); }
}

/* ---- bokeh ---- */
.bokeh {
  position: absolute;
  border-radius: 9999px;
  background: radial-gradient(circle at 35% 35%, color-mix(in srgb, var(--c) 55%, white), var(--c) 45%, transparent 72%);
  box-shadow: inset 0 0 0 2px color-mix(in srgb, var(--c) 40%, transparent);
  opacity: 0.22;
  animation: bokeh-float ease-in-out infinite alternate;
}
html.dark .bokeh {
  opacity: 0.16;
}
@keyframes bokeh-float {
  0% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(var(--dx), var(--dy)) scale(1.12); opacity: 0.3; }
  100% { transform: translate(calc(var(--dx) * -0.6), calc(var(--dy) * 0.8)) scale(0.92); }
}

/* ---- floating shapes ---- */
.shape {
  position: absolute;
  opacity: 0.28;
  animation: shape-float ease-in-out infinite alternate;
}
html.dark .shape {
  opacity: 0.22;
}
@keyframes shape-float {
  from { transform: translateY(0) rotate(0deg); }
  to { transform: translateY(var(--dy)) rotate(var(--spin)); }
}

/* ---- light ribbons ---- */
.ribbon {
  position: absolute;
  left: 0;
  width: 200%;
  height: 40vh;
  animation: wave-move linear infinite;
}
.ribbon-1 { top: 18%; opacity: 0.18; animation-duration: calc(40s * var(--dur)); }
.ribbon-2 { top: 42%; opacity: 0.22; animation-duration: calc(30s * var(--dur)); animation-direction: reverse; }
.ribbon-3 { top: 60%; opacity: 0.26; animation-duration: calc(22s * var(--dur)); }

/* ---- moving grid ---- */
.grid-floor {
  position: absolute;
  left: -50%;
  right: -50%;
  bottom: -10%;
  height: 70%;
  background-image:
    linear-gradient(to right, color-mix(in srgb, var(--bg-1) 55%, transparent) 1px, transparent 1px),
    linear-gradient(to bottom, color-mix(in srgb, var(--bg-1) 55%, transparent) 1px, transparent 1px);
  background-size: 64px 64px;
  transform: perspective(500px) rotateX(62deg);
  transform-origin: 50% 100%;
  mask-image: linear-gradient(to top, black 30%, transparent 95%);
  opacity: 0.35;
  animation: grid-scroll calc(6s * var(--dur)) linear infinite;
}
html.dark .grid-floor {
  opacity: 0.28;
}
@keyframes grid-scroll {
  from { background-position: 0 0; }
  to { background-position: 0 64px; }
}
.grid-horizon {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 58%;
  height: 120px;
  background: radial-gradient(ellipse at center, color-mix(in srgb, var(--bg-2) 45%, transparent), transparent 70%);
  opacity: 0.5;
  animation: horizon-glow calc(10s * var(--dur)) ease-in-out infinite alternate;
}
@keyframes horizon-glow {
  from { opacity: 0.3; }
  to { opacity: 0.6; }
}

.ken-burns {
  animation: ken-burns calc(40s * var(--dur)) ease-in-out infinite alternate;
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
</style>
