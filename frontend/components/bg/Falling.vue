<script setup lang="ts">
// Natural things drifting across the site background: spring blossoms,
// autumn leaves, snow, rain and fireflies. Petals and leaves tumble in 3D
// (rotateX/Y) as they fall, which is what makes them read as real rather
// than sliding stickers. Durations scale with the inherited --dur.
const props = defineProps<{ kind: 'sakura' | 'leaves' | 'snow' | 'rain' | 'fireflies' }>()

function seeded(seed: number) {
  return () => ((seed = (seed * 16807) % 2147483647) / 2147483647)
}

const COUNTS = { sakura: 28, leaves: 18, snow: 70, rain: 90, fireflies: 26 }
const PALETTES = {
  sakura: ['#f9c5d5', '#f7a8c0', '#fde2ea', '#f48fb1'],
  leaves: ['#e8762c', '#d94f2b', '#f2a93b', '#b8452a', '#e6b847'],
  snow: ['#ffffff'],
  rain: ['#9ec5e8'],
  fireflies: ['#e8ff8a', '#fff3a0', '#c8ff7a'],
}

const items = computed(() => {
  const rand = seeded(props.kind.length * 97 + 13)
  const palette = PALETTES[props.kind]
  return Array.from({ length: COUNTS[props.kind] }, (_, i) => {
    const base = {
      left: `${(rand() * 100).toFixed(1)}%`,
      top: `${(rand() * 100).toFixed(1)}%`,
      delay: -(rand() * 40),
      color: palette[i % palette.length],
      drift: `${((rand() - 0.5) * 260).toFixed(0)}px`,
      spinX: `${Math.round(360 + rand() * 720)}deg`,
      spinY: `${Math.round(180 + rand() * 540)}deg`,
      spinZ: `${Math.round((rand() - 0.5) * 540)}deg`,
    }
    switch (props.kind) {
      case 'sakura': return { ...base, size: 10 + rand() * 12, duration: 16 + rand() * 14 }
      case 'leaves': return { ...base, size: 18 + rand() * 18, duration: 18 + rand() * 14 }
      case 'snow': return { ...base, size: 2 + rand() * 6, duration: 14 + rand() * 18 }
      case 'rain': return { ...base, size: 14 + rand() * 20, duration: 0.7 + rand() * 0.6, delay: -(rand() * 2) }
      default: return { ...base, size: 4 + rand() * 4, duration: 7 + rand() * 8 }
    }
  })
})
</script>

<template>
  <div :class="['falling absolute inset-0', `kind-${kind}`]">
    <div class="tint absolute inset-0" />
    <span
      v-for="(p, i) in items"
      :key="i"
      class="piece"
      :style="{
        left: p.left,
        top: kind === 'fireflies' ? p.top : undefined,
        width: `${p.size}px`,
        height: kind === 'rain' ? `${p.size}px` : `${p.size}px`,
        color: p.color,
        animationDuration: `calc(${p.duration}s * var(--dur))`,
        animationDelay: `calc(${p.delay}s * var(--dur))`,
        '--drift': p.drift,
        '--sx': p.spinX,
        '--sy': p.spinY,
        '--sz': p.spinZ,
      }"
    >
      <!-- blossom petal: notched teardrop -->
      <svg v-if="kind === 'sakura'" viewBox="0 0 20 20" class="h-full w-full">
        <path d="M10 1 C15 4 18 9 10 19 C2 9 5 4 10 1 Z M10 1 L8.8 4 L10 3.2 L11.2 4 Z" fill="currentColor" />
      </svg>
      <!-- maple-ish leaf -->
      <svg v-else-if="kind === 'leaves'" viewBox="0 0 24 24" class="h-full w-full">
        <path d="M12 2 L13.6 7 L17.5 5 L16.4 9.4 L21 10 L17.6 13 L19.5 16.5 L14.5 15.8 L12.6 21 L12 17.2 L11.4 21 L9.5 15.8 L4.5 16.5 L6.4 13 L3 10 L7.6 9.4 L6.5 5 L10.4 7 Z" fill="currentColor" />
        <path d="M12 7 V22" stroke="rgb(0 0 0 / 0.25)" stroke-width="0.8" />
      </svg>
    </span>
  </div>
</template>

<style scoped>
.falling {
  perspective: 800px;
}
.piece {
  position: absolute;
  top: -40px;
  display: block;
  animation-timing-function: linear;
  animation-iteration-count: infinite;
  will-change: transform;
}

/* ---- blossoms & leaves: fall while tumbling in 3D ---- */
.kind-sakura .piece,
.kind-leaves .piece {
  animation-name: tumble;
  opacity: 0.85;
}
.kind-leaves .piece { opacity: 0.8; filter: drop-shadow(0 2px 2px rgb(0 0 0 / 0.12)); }
@keyframes tumble {
  0% { transform: translate3d(0, 0, 0) rotateX(0) rotateY(0) rotateZ(0); }
  25% { transform: translate3d(calc(var(--drift) * 0.5), 28vh, 0) rotateX(calc(var(--sx) * 0.25)) rotateY(calc(var(--sy) * 0.25)) rotateZ(calc(var(--sz) * 0.25)); }
  50% { transform: translate3d(calc(var(--drift) * -0.2), 56vh, 0) rotateX(calc(var(--sx) * 0.5)) rotateY(calc(var(--sy) * 0.5)) rotateZ(calc(var(--sz) * 0.5)); }
  75% { transform: translate3d(calc(var(--drift) * 0.8), 84vh, 0) rotateX(calc(var(--sx) * 0.75)) rotateY(calc(var(--sy) * 0.75)) rotateZ(calc(var(--sz) * 0.75)); }
  100% { transform: translate3d(var(--drift), 112vh, 0) rotateX(var(--sx)) rotateY(var(--sy)) rotateZ(var(--sz)); }
}

/* ---- snow ---- */
.kind-snow .piece {
  border-radius: 9999px;
  background: currentColor;
  box-shadow: 0 0 6px rgb(255 255 255 / 0.9);
  animation-name: snowfall;
  opacity: 0.9;
}
.kind-snow .tint { background: linear-gradient(180deg, rgb(160 190 225 / 0.35), rgb(235 242 250 / 0.15)); }
html.dark .kind-snow .tint { background: linear-gradient(180deg, rgb(20 32 60 / 0.5), rgb(10 16 30 / 0.2)); }
@keyframes snowfall {
  0% { transform: translate3d(0, 0, 0); }
  50% { transform: translate3d(calc(var(--drift) * 0.4), 55vh, 0); }
  100% { transform: translate3d(calc(var(--drift) * -0.3), 112vh, 0); }
}

/* ---- rain ---- */
.kind-rain .piece {
  width: 1.5px !important;
  border-radius: 2px;
  background: linear-gradient(to bottom, transparent, currentColor);
  animation-name: rainfall;
  opacity: 0.45;
}
.kind-rain .tint { background: linear-gradient(180deg, rgb(90 110 140 / 0.35), rgb(150 170 190 / 0.15)); }
html.dark .kind-rain .tint { background: linear-gradient(180deg, rgb(10 16 28 / 0.55), rgb(20 28 45 / 0.25)); }
@keyframes rainfall {
  from { transform: translate3d(0, 0, 0) rotate(12deg); }
  to { transform: translate3d(-24vh, 115vh, 0) rotate(12deg); }
}

/* ---- fireflies ---- */
.kind-fireflies .piece {
  border-radius: 9999px;
  background: currentColor;
  box-shadow: 0 0 12px 4px currentColor;
  animation-name: glow-wander;
  animation-timing-function: ease-in-out;
  animation-direction: alternate;
}
.kind-fireflies .tint { background: radial-gradient(ellipse at 50% 100%, rgb(40 70 50 / 0.35), transparent 70%); }
html.dark .kind-fireflies .tint { background: radial-gradient(ellipse at 50% 100%, rgb(20 45 30 / 0.6), rgb(5 10 15 / 0.3)); }
@keyframes glow-wander {
  0% { transform: translate(0, 0); opacity: 0.1; }
  30% { opacity: 1; }
  60% { transform: translate(calc(var(--drift) * 0.3), -40px); opacity: 0.4; }
  100% { transform: translate(calc(var(--drift) * -0.2), 30px); opacity: 0.9; }
}

/* spring: a soft pink wash; autumn: warm */
.kind-sakura .tint { background: linear-gradient(180deg, rgb(253 226 234 / 0.35), transparent 70%); }
.kind-leaves .tint { background: linear-gradient(180deg, rgb(252 223 180 / 0.3), transparent 70%); }
html.dark .kind-sakura .tint,
html.dark .kind-leaves .tint { background: none; }
</style>
