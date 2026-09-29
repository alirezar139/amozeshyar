<script setup lang="ts">
// Illustrated nature scenes for the site background: layered silhouettes
// that parallax with the pointer (--px/--py from LayoutSiteBackground),
// slow drifting clouds, and a day palette that turns to night in dark mode.
// Durations scale with the inherited --dur (the owner's speed setting).
defineProps<{ scene: 'mountains' | 'clouds' | 'ocean' | 'forest' | 'dunes' }>()

// A fluffy cloud as one path of overlapping arcs; reused at many scales.
const CLOUD = 'M25 60 a20 20 0 0 1 8-38 a26 26 0 0 1 48-8 a22 22 0 0 1 38 10 a18 18 0 0 1 6 36 Z'

const clouds = [
  { top: '8%', scale: 1.3, duration: 150, delay: -20, opacity: 0.9 },
  { top: '18%', scale: 0.8, duration: 110, delay: -70, opacity: 0.75 },
  { top: '4%', scale: 0.6, duration: 95, delay: -40, opacity: 0.6 },
  { top: '26%', scale: 1.05, duration: 170, delay: -120, opacity: 0.7 },
  { top: '13%', scale: 0.5, duration: 80, delay: -10, opacity: 0.55 },
]
const birds = [
  { top: '22%', size: 1, duration: 38, delay: -5 },
  { top: '26%', size: 0.75, duration: 42, delay: -8 },
  { top: '19%', size: 0.6, duration: 46, delay: -3 },
]
// Pine silhouette used by the forest scene.
function pine(x: number, base: number, h: number) {
  const w = h * 0.42
  return `M${x} ${base - h} L${x + w * 0.5} ${base - h * 0.62} L${x + w * 0.28} ${base - h * 0.62} L${x + w * 0.72} ${base - h * 0.3} L${x + w * 0.4} ${base - h * 0.3} L${x + w} ${base} L${x - w} ${base} L${x - w * 0.4} ${base - h * 0.3} L${x - w * 0.72} ${base - h * 0.3} L${x - w * 0.28} ${base - h * 0.62} L${x - w * 0.5} ${base - h * 0.62} Z`
}
function forestRow(seed: number, base: number, minH: number, maxH: number, gap: number) {
  let s = seed
  const rand = () => ((s = (s * 16807) % 2147483647) / 2147483647)
  const trees: string[] = []
  for (let x = -40; x < 1480; x += gap * (0.6 + rand() * 0.8)) trees.push(pine(x, base, minH + rand() * (maxH - minH)))
  return trees.join(' ') + ` M-60 ${base} H1500 V900 H-60 Z`
}
const forest = [forestRow(3, 620, 160, 260, 70), forestRow(9, 720, 200, 330, 90), forestRow(17, 840, 260, 420, 120)]
</script>

<template>
  <div :class="['landscape absolute inset-0', `scene-${scene}`]">
    <!-- sky -->
    <div class="sky absolute inset-0" />

    <!-- sun / moon -->
    <div v-if="scene !== 'clouds'" class="layer depth-1">
      <div class="celestial" />
    </div>
    <!-- night stars -->
    <div class="night-only layer depth-1">
      <span v-for="i in 40" :key="i" class="tiny-star" :style="{ top: `${(i * 37) % 55}%`, left: `${(i * 61) % 100}%`, animationDelay: `${-(i % 7)}s` }" />
    </div>

    <!-- clouds (all daytime scenes) -->
    <div class="layer depth-2">
      <svg
        v-for="(c, i) in clouds.slice(0, scene === 'clouds' ? 5 : 3)"
        :key="i"
        class="cloud"
        viewBox="0 0 140 70"
        :style="{
          top: c.top,
          width: `${160 * c.scale}px`,
          opacity: c.opacity,
          animationDuration: `calc(${c.duration}s * var(--dur))`,
          animationDelay: `calc(${c.delay}s * var(--dur))`,
        }"
      >
        <path :d="CLOUD" fill="currentColor" />
      </svg>
    </div>

    <!-- birds -->
    <div v-if="scene === 'clouds' || scene === 'ocean' || scene === 'mountains'" class="day-only layer depth-2">
      <svg
        v-for="(b, i) in birds"
        :key="i"
        class="bird"
        viewBox="0 0 30 12"
        :style="{ top: b.top, width: `${26 * b.size}px`, animationDuration: `calc(${b.duration}s * var(--dur))`, animationDelay: `calc(${b.delay}s * var(--dur))` }"
      >
        <path class="wing" d="M1 6 Q8 0 15 6 Q22 0 29 6" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
      </svg>
    </div>

    <!-- ============ mountains ============ -->
    <template v-if="scene === 'mountains'">
      <svg class="ridge depth-2 layer" viewBox="0 0 1440 900" preserveAspectRatio="xMidYMax slice">
        <path class="ridge-1" d="M0 560 L140 420 L260 500 L420 330 L560 470 L700 360 L860 480 L1000 340 L1160 470 L1300 380 L1440 460 V900 H0 Z" />
      </svg>
      <svg class="ridge depth-3 layer" viewBox="0 0 1440 900" preserveAspectRatio="xMidYMax slice">
        <path class="ridge-2" d="M0 650 L180 520 L340 610 L520 470 L700 600 L880 500 L1060 620 L1240 510 L1440 600 V900 H0 Z" />
        <path class="snowcap" d="M520 470 L560 505 L540 500 L520 520 L500 500 L480 505 Z M880 500 L915 530 L895 527 L880 545 L862 527 L845 530 Z" />
      </svg>
      <div class="mist absolute inset-x-0 bottom-[18%] h-40" />
      <svg class="ridge layer depth-3 fg" viewBox="0 0 1440 900" preserveAspectRatio="xMidYMax slice">
        <path class="ridge-3" d="M0 760 Q200 690 380 740 T760 730 T1140 750 T1440 720 V900 H0 Z" />
      </svg>
    </template>

    <!-- ============ ocean ============ -->
    <template v-else-if="scene === 'ocean'">
      <div class="sea absolute inset-x-0 bottom-0 h-[42%]">
        <div class="sun-path" />
        <svg v-for="i in 4" :key="i" :class="['swell', `swell-${i}`]" viewBox="0 0 2880 120" preserveAspectRatio="none">
          <path d="M0 60 C240 30 480 90 720 60 C960 30 1200 90 1440 60 C1680 30 1920 90 2160 60 C2400 30 2640 90 2880 60 V120 H0 Z" />
        </svg>
      </div>
    </template>

    <!-- ============ forest ============ -->
    <template v-else-if="scene === 'forest'">
      <svg v-for="(row, i) in forest" :key="i" :class="['ridge layer', `depth-${i + 1}`]" viewBox="0 0 1440 900" preserveAspectRatio="xMidYMax slice">
        <path :class="`pines-${i + 1}`" :d="row" />
      </svg>
      <div class="fog fog-1" />
      <div class="fog fog-2" />
      <div class="night-only absolute inset-0">
        <span v-for="i in 14" :key="i" class="firefly" :style="{ top: `${55 + ((i * 23) % 35)}%`, left: `${(i * 71) % 100}%`, animationDelay: `${-(i * 1.7)}s` }" />
      </div>
    </template>

    <!-- ============ dunes ============ -->
    <template v-else-if="scene === 'dunes'">
      <div class="heat absolute inset-x-0 bottom-[30%] h-24" />
      <svg class="ridge layer depth-1" viewBox="0 0 1440 900" preserveAspectRatio="xMidYMax slice">
        <path class="dune-1" d="M0 600 C220 520 420 560 640 600 C860 640 1080 520 1440 560 V900 H0 Z" />
      </svg>
      <svg class="ridge layer depth-2" viewBox="0 0 1440 900" preserveAspectRatio="xMidYMax slice">
        <path class="dune-2" d="M0 700 C300 620 520 700 760 690 C1000 680 1180 610 1440 660 V900 H0 Z" />
      </svg>
      <svg class="ridge layer depth-3" viewBox="0 0 1440 900" preserveAspectRatio="xMidYMax slice">
        <path class="dune-3" d="M0 800 C260 740 600 790 900 770 C1160 752 1300 760 1440 780 V900 H0 Z" />
      </svg>
    </template>
  </div>
</template>

<style scoped>
.landscape {
  opacity: 0.62;
}
html.dark .landscape {
  opacity: 0.55;
}
.day-only { display: block; }
.night-only { display: none; }
html.dark .landscape .day-only { display: none; }
html.dark .landscape .night-only { display: block; }

/* ---- skies ---- */
.sky { background: linear-gradient(180deg, #7cc4f5 0%, #bfe3fb 55%, #f4f1ea 100%); }
.scene-dunes .sky { background: linear-gradient(180deg, #f5a45b 0%, #fbd38a 45%, #fdecc8 100%); }
.scene-ocean .sky { background: linear-gradient(180deg, #74b9f0 0%, #b9dcf7 50%, #fde9cf 58%); }
.scene-forest .sky { background: linear-gradient(180deg, #a8d8c8 0%, #d9eee4 60%, #eef5ef 100%); }
html.dark .landscape .sky { background: linear-gradient(180deg, #050a1f 0%, #0f1c3d 55%, #1b2a4a 100%); }
html.dark .scene-dunes .sky { background: linear-gradient(180deg, #120b24 0%, #2c1a3d 55%, #4a2d44 100%); }

/* ---- sun / moon ---- */
.celestial {
  position: absolute;
  top: 12%;
  right: 16%;
  width: 110px;
  height: 110px;
  border-radius: 9999px;
  background: radial-gradient(circle, #fff7d6 0%, #ffd66b 45%, rgb(255 214 107 / 0) 72%);
  box-shadow: 0 0 120px 40px rgb(255 214 107 / 0.35);
  animation: sun-breathe calc(12s * var(--dur)) ease-in-out infinite alternate;
}
.scene-dunes .celestial { top: 30%; width: 150px; height: 150px; background: radial-gradient(circle, #fff1c9 0%, #ff9f4a 50%, rgb(255 120 60 / 0) 72%); }
.scene-ocean .celestial { top: 38%; right: 30%; }
html.dark .landscape .celestial {
  width: 80px;
  height: 80px;
  background: radial-gradient(circle at 38% 38%, #ffffff 0%, #dfe6f5 55%, rgb(223 230 245 / 0) 72%);
  box-shadow: 0 0 80px 20px rgb(200 215 255 / 0.18);
}
@keyframes sun-breathe {
  from { transform: scale(1); }
  to { transform: scale(1.06); }
}

.tiny-star {
  position: absolute;
  width: 2px;
  height: 2px;
  border-radius: 9999px;
  background: white;
  animation: twinkle calc(4s * var(--dur)) ease-in-out infinite;
}
@keyframes twinkle {
  0%, 100% { opacity: 0.2; }
  50% { opacity: 1; }
}

/* ---- parallax (inherits --px/--py from the background root) ---- */
.layer { position: absolute; inset: 0; transition: transform 2.4s cubic-bezier(0.22, 1, 0.36, 1); }
.depth-1 { transform: translate3d(calc(var(--px) * -8px), calc(var(--py) * -5px), 0); }
.depth-2 { transform: translate3d(calc(var(--px) * -18px), calc(var(--py) * -10px), 0); }
.depth-3 { transform: translate3d(calc(var(--px) * -32px), calc(var(--py) * -16px), 0); }

/* ---- clouds & birds ---- */
.cloud {
  position: absolute;
  left: 0;
  color: white;
  filter: drop-shadow(0 6px 10px rgb(80 120 160 / 0.15));
  animation: drift-across linear infinite;
}
html.dark .landscape .cloud { color: #2a3657; filter: none; }
@keyframes drift-across {
  from { transform: translateX(-30vw); }
  to { transform: translateX(130vw); }
}
.bird {
  position: absolute;
  left: 0;
  color: #34425a;
  animation: fly-across linear infinite;
}
.wing { animation: flap 0.9s ease-in-out infinite alternate; transform-origin: 50% 50%; }
@keyframes fly-across {
  from { transform: translate(110vw, 0); }
  to { transform: translate(-20vw, -6vh); }
}
@keyframes flap {
  from { transform: scaleY(1); }
  to { transform: scaleY(0.35); }
}

/* ---- silhouettes ---- */
.ridge { width: 100%; height: 100%; }
.ridge-1 { fill: #8fb3cf; }
.ridge-2 { fill: #5f86a8; }
.ridge-3 { fill: #3e6284; }
.snowcap { fill: #f3f7fb; }
html.dark .landscape .ridge-1 { fill: #1f2d4f; }
html.dark .landscape .ridge-2 { fill: #17223d; }
html.dark .landscape .ridge-3 { fill: #0f172b; }
html.dark .landscape .snowcap { fill: #9fb0d0; }
.mist {
  background: linear-gradient(to top, rgb(255 255 255 / 0.55), transparent);
  animation: mist-breathe calc(14s * var(--dur)) ease-in-out infinite alternate;
}
html.dark .landscape .mist { background: linear-gradient(to top, rgb(120 140 190 / 0.18), transparent); }
@keyframes mist-breathe {
  from { opacity: 0.5; transform: translateX(-2%); }
  to { opacity: 1; transform: translateX(2%); }
}

.pines-1 { fill: #7fae9a; }
.pines-2 { fill: #4f8a72; }
.pines-3 { fill: #2f5f4c; }
html.dark .landscape .pines-1 { fill: #1b2f37; }
html.dark .landscape .pines-2 { fill: #132229; }
html.dark .landscape .pines-3 { fill: #0b161b; }
.fog {
  position: absolute;
  left: -20%;
  width: 140%;
  height: 22%;
  border-radius: 50%;
  background: radial-gradient(ellipse at center, rgb(255 255 255 / 0.6), transparent 70%);
  animation: fog-drift linear infinite alternate;
}
.fog-1 { bottom: 26%; animation-duration: calc(40s * var(--dur)); }
.fog-2 { bottom: 12%; animation-duration: calc(55s * var(--dur)); animation-direction: alternate-reverse; }
html.dark .landscape .fog { background: radial-gradient(ellipse at center, rgb(140 160 200 / 0.14), transparent 70%); }
@keyframes fog-drift {
  from { transform: translateX(-8%); }
  to { transform: translateX(8%); }
}
.firefly {
  position: absolute;
  width: 5px;
  height: 5px;
  border-radius: 9999px;
  background: #e8ff8a;
  box-shadow: 0 0 10px 3px rgb(232 255 138 / 0.6);
  animation: firefly-wander calc(9s * var(--dur)) ease-in-out infinite alternate;
}
@keyframes firefly-wander {
  0% { transform: translate(0, 0); opacity: 0.2; }
  50% { opacity: 1; }
  100% { transform: translate(40px, -30px); opacity: 0.3; }
}

/* ---- ocean ---- */
.sea { background: linear-gradient(180deg, #4d9bd6 0%, #2d6fa6 100%); overflow: hidden; }
html.dark .landscape .sea { background: linear-gradient(180deg, #13244a 0%, #0a1430 100%); }
.sun-path {
  position: absolute;
  top: 0;
  right: 28%;
  width: 140px;
  height: 100%;
  background: linear-gradient(to bottom, rgb(255 236 170 / 0.8), rgb(255 236 170 / 0));
  filter: blur(6px);
  animation: glitter calc(3s * var(--dur)) ease-in-out infinite alternate;
}
html.dark .landscape .sun-path { background: linear-gradient(to bottom, rgb(220 230 255 / 0.4), rgb(220 230 255 / 0)); }
@keyframes glitter {
  from { opacity: 0.6; transform: scaleX(0.9); }
  to { opacity: 1; transform: scaleX(1.1); }
}
.swell {
  position: absolute;
  left: 0;
  width: 200%;
  height: 40px;
  animation: swell-move linear infinite;
}
.swell path { fill: rgb(255 255 255 / 0.12); }
.swell-1 { top: 10%; animation-duration: calc(22s * var(--dur)); }
.swell-2 { top: 32%; animation-duration: calc(17s * var(--dur)); animation-direction: reverse; }
.swell-3 { top: 55%; animation-duration: calc(13s * var(--dur)); }
.swell-4 { top: 78%; animation-duration: calc(10s * var(--dur)); animation-direction: reverse; }
@keyframes swell-move {
  from { transform: translateX(0); }
  to { transform: translateX(-50%); }
}

/* ---- dunes ---- */
.dune-1 { fill: #f1b870; }
.dune-2 { fill: #e39a52; }
.dune-3 { fill: #c97a3a; }
html.dark .landscape .dune-1 { fill: #3d2a45; }
html.dark .landscape .dune-2 { fill: #2e2038; }
html.dark .landscape .dune-3 { fill: #20162a; }
.heat {
  background: linear-gradient(to top, rgb(255 210 150 / 0.4), transparent);
  animation: heat calc(5s * var(--dur)) ease-in-out infinite alternate;
}
@keyframes heat {
  from { transform: skewX(-1deg); opacity: 0.5; }
  to { transform: skewX(1deg); opacity: 0.9; }
}
</style>
