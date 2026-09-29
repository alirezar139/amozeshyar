<script setup lang="ts">
// Live WebGL background (see utils/shaders.ts). Rendered at a reduced
// resolution and scaled up — these are soft, low-frequency images, so it
// looks identical at a fraction of the GPU cost. Pauses while the tab is
// hidden, draws a single still frame when motion is off, follows dark mode,
// and falls back to a CSS gradient if WebGL is unavailable.
import { createShaderRenderer, parseColor, type ShaderEffect, type ShaderRenderer } from '~/utils/shaders'

const props = defineProps<{ effect: ShaderEffect; colors: string[]; motion: boolean; speed: number }>()

const canvas = ref<HTMLCanvasElement | null>(null)
const failed = ref(false)
let renderer: ShaderRenderer | null = null
let frame = 0
let last = 0
let clock = 20 // start mid-animation, not at a symmetric t=0
let dark = false
let mouse: [number, number] = [0.5, 0.5]
let themeObserver: MutationObserver | null = null

const RESOLUTION = 0.5

function palette(): [number, number, number][] {
  const css = getComputedStyle(document.documentElement)
  const fallback = [css.getPropertyValue('--c-primary-500'), css.getPropertyValue('--c-accent-500'), css.getPropertyValue('--c-primary-300')]
  return [0, 1, 2].map((i) => parseColor(props.colors[i] || (i === 2 && props.colors[0]) || fallback[i])) as [number, number, number][]
}

function resize() {
  renderer?.resize(window.innerWidth * RESOLUTION, window.innerHeight * RESOLUTION)
  if (!props.motion) draw()
}

function draw() {
  renderer?.render(clock, { colors: palette(), dark, mouse })
}

function loop(now: number) {
  frame = requestAnimationFrame(loop)
  if (document.visibilityState !== 'visible') return
  const dt = last ? Math.min(0.1, (now - last) / 1000) : 0
  last = now
  // --dur (slow 2.2 … fast 0.85) → animation time runs slower for "slow".
  clock += dt / props.speed
  draw()
}

function start() {
  cancelAnimationFrame(frame)
  last = 0
  if (props.motion) frame = requestAnimationFrame(loop)
  else draw()
}

function onPointer(e: PointerEvent) {
  mouse = [e.clientX / window.innerWidth, 1 - e.clientY / window.innerHeight]
}

onMounted(() => {
  if (!canvas.value) return
  renderer = createShaderRenderer(canvas.value)
  if (!renderer || !renderer.setEffect(props.effect)) {
    failed.value = true
    return
  }
  dark = document.documentElement.classList.contains('dark')
  themeObserver = new MutationObserver(() => {
    dark = document.documentElement.classList.contains('dark')
    if (!props.motion) draw()
  })
  themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['class', 'style'] })
  window.addEventListener('resize', resize)
  window.addEventListener('pointermove', onPointer, { passive: true })
  resize()
  start()
})

watch(() => props.effect, (effect) => {
  if (renderer && !renderer.setEffect(effect)) failed.value = true
  if (!props.motion) draw()
})
watch(() => [props.motion, props.colors.join()], start)

onBeforeUnmount(() => {
  cancelAnimationFrame(frame)
  themeObserver?.disconnect()
  window.removeEventListener('resize', resize)
  window.removeEventListener('pointermove', onPointer)
  renderer?.destroy()
})
</script>

<template>
  <div class="absolute inset-0">
    <canvas v-show="!failed" ref="canvas" class="shader-canvas h-full w-full" />
    <div v-if="failed" class="fallback absolute inset-0" />
  </div>
</template>

<style scoped>
.shader-canvas {
  display: block;
  opacity: 0.85;
  animation: shader-in 1.2s ease both;
}
html.dark .shader-canvas {
  opacity: 0.9;
}
@keyframes shader-in {
  from { opacity: 0; }
}
.fallback {
  background: linear-gradient(120deg, var(--bg-1), var(--bg-2), var(--bg-3));
  opacity: 0.3;
}
</style>
