<script setup lang="ts">
const emit = defineEmits<{ passed: [passToken: string]; reset: [] }>()

const { request } = useApi()

const stage = ref<'puzzle' | 'number'>('puzzle')

// Stage 1: drag the gem into its socket.
const challenge = ref<any | null>(null)
const sliderX = ref(0)
const puzzleStatus = ref<'idle' | 'checking' | 'passed' | 'failed'>('idle')
const puzzleError = ref('')
const dragging = ref(false)
const trackRef = ref<HTMLDivElement | null>(null)

// Stage 2: type the distorted code shown after stage 1 passes.
const numberChallenge = ref<{ token: string; image: string; length: number } | null>(null)
const code = ref('')
const numberStatus = ref<'idle' | 'checking' | 'failed'>('idle')
const numberInput = ref<HTMLInputElement | null>(null)

async function loadChallenge() {
  stage.value = 'puzzle'
  puzzleStatus.value = 'idle'
  puzzleError.value = ''
  sliderX.value = 0
  dragging.value = false
  numberChallenge.value = null
  code.value = ''
  numberStatus.value = 'idle'
  emit('reset')
  try {
    challenge.value = await request<any>('/auth/captcha/challenge/')
  } catch {
    puzzleError.value = 'بارگذاری پازل ناموفق بود.'
  }
}

async function confirmPuzzle() {
  if (!challenge.value) return
  puzzleStatus.value = 'checking'
  try {
    numberChallenge.value = await request<{ token: string; image: string; length: number }>(
      '/auth/captcha/verify/',
      { method: 'POST', body: { token: challenge.value.token, x: sliderX.value } }
    )
    puzzleStatus.value = 'passed'
    // Let the success glow actually be seen for a beat before switching
    // stages — an instant swap made the "پازل درست شد" moment invisible.
    setTimeout(async () => {
      stage.value = 'number'
      await nextTick()
      numberInput.value?.focus()
    }, 450)
  } catch {
    puzzleStatus.value = 'failed'
    setTimeout(loadChallenge, 900)
  }
}

// Real pointer-drag instead of a plain <input type="range"> — dragging
// the piece directly is the tactile, "obviously interactive" motion this
// kind of puzzle is supposed to have.
function onPointerDown(event: PointerEvent) {
  if (puzzleStatus.value !== 'idle' || !challenge.value) return
  dragging.value = true
  ;(event.target as HTMLElement).setPointerCapture(event.pointerId)
  updateFromPointer(event)
}
function onPointerMove(event: PointerEvent) {
  if (!dragging.value) return
  updateFromPointer(event)
}
function onPointerUp() {
  if (!dragging.value) return
  dragging.value = false
  confirmPuzzle()
}
function updateFromPointer(event: PointerEvent) {
  if (!trackRef.value || !challenge.value) return
  const rect = trackRef.value.getBoundingClientRect()
  const raw = event.clientX - rect.left - challenge.value.piece_size / 2
  sliderX.value = Math.min(maxX.value, Math.max(0, raw))
}

function onCodeInput() {
  code.value = code.value.replace(/[^0-9]/g, '')
  if (numberChallenge.value && code.value.length === numberChallenge.value.length) confirmNumber()
}

async function confirmNumber() {
  if (!numberChallenge.value || code.value.length !== numberChallenge.value.length) return
  numberStatus.value = 'checking'
  try {
    const res = await request<{ pass_token: string }>('/auth/captcha/verify-number/', {
      method: 'POST',
      body: { token: numberChallenge.value.token, code: code.value },
    })
    numberStatus.value = 'idle'
    emit('passed', res.pass_token)
  } catch {
    numberStatus.value = 'failed'
    // Stage 2 is one-shot too, and it's tied to a specific stage-1 pass —
    // a wrong code restarts the whole thing rather than just retrying
    // stage 2, same "no free retries" posture as stage 1.
    setTimeout(loadChallenge, 900)
  }
}

const maxX = computed(() => (challenge.value ? challenge.value.width - challenge.value.piece_size : 0))
const progressRatio = computed(() => (maxX.value ? sliderX.value / maxX.value : 0))

onMounted(loadChallenge)

defineExpose({ reload: loadChallenge })
</script>

<template>
  <div>
    <!-- Two-step progress: a filled pill per stage, the current one lit
         with the animated gradient, done ones solid green. -->
    <div class="mb-3 flex items-center gap-2">
      <span
        class="h-1.5 flex-1 rounded-full transition-colors duration-500"
        :class="stage === 'puzzle' ? 'captcha-glow-bar' : 'bg-emerald-500'"
      />
      <span
        class="h-1.5 flex-1 rounded-full transition-colors duration-500"
        :class="stage === 'number' ? 'captcha-glow-bar' : 'bg-gray-300 dark:bg-white/10'"
      />
    </div>
    <p class="mb-2 text-xs font-medium text-gray-500 dark:text-gray-400">
      مرحله {{ stage === 'puzzle' ? '۱' : '۲' }} از ۲
    </p>

    <div v-if="stage === 'puzzle'">
      <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">قطعه‌ی الماس را بکشید و به جای خودش بگذارید</label>

      <div
        v-if="challenge"
        ref="trackRef"
        class="captcha-frame relative mt-2 select-none overflow-hidden rounded-xl"
        :class="{ 'captcha-shake': puzzleStatus === 'failed' }"
        :style="{ width: `${challenge.width}px`, height: `${challenge.height}px`, maxWidth: '100%' }"
      >
        <img :src="challenge.background" alt="" class="absolute inset-0 h-full w-full object-cover" draggable="false" />

        <img
          :src="challenge.piece"
          alt=""
          class="captcha-piece absolute touch-none transition-[filter,transform] duration-200 ease-out"
          :class="[
            puzzleStatus === 'passed' ? 'drop-shadow-[0_0_14px_rgba(52,211,153,0.95)] scale-110' : 'drop-shadow-[0_0_8px_rgba(255,255,255,0.75)]',
            !dragging && puzzleStatus === 'idle' ? 'captcha-invite' : '',
            dragging ? 'cursor-grabbing scale-105' : 'cursor-grab',
          ]"
          :style="{
            top: `${challenge.piece_y}px`,
            left: `${sliderX}px`,
            width: `${challenge.piece_size}px`,
            height: `${challenge.piece_size}px`,
          }"
          @pointerdown="onPointerDown"
          @pointermove="onPointerMove"
          @pointerup="onPointerUp"
          @pointercancel="onPointerUp"
        />

        <!-- Success checkmark badge, pops in once verified -->
        <Transition name="pop">
          <div v-if="puzzleStatus === 'passed'" class="absolute inset-0 flex items-center justify-center bg-emerald-500/10">
            <span class="flex h-11 w-11 items-center justify-center rounded-full bg-emerald-500 text-white shadow-lg shadow-emerald-500/50">
              <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" /></svg>
            </span>
          </div>
        </Transition>

        <p v-if="puzzleStatus === 'failed'" class="absolute inset-x-0 bottom-1 text-center text-xs font-medium text-red-300">
          جای درستی نبود — پازل جدید...
        </p>
      </div>

      <!-- Doubles as the accessible control: dragging the piece directly
           is the fun/primary interaction, but a keyboard-only user (or
           anyone whose pointer drag didn't register) can still arrow-key
           this range through the exact same sliderX value. Custom CSS
           below repaints it as the gradient progress fill instead of a
           default OS slider, so the two feel like one control. -->
      <input
        v-if="challenge"
        v-model.number="sliderX"
        type="range"
        min="0"
        :max="maxX"
        :disabled="puzzleStatus !== 'idle'"
        class="captcha-range mt-3 w-full"
        :style="{ '--captcha-progress': `${Math.round(progressRatio * 100)}%` }"
        aria-label="جای‌گذاری قطعه‌ی الماس"
        @change="confirmPuzzle"
      />

      <div v-else class="captcha-shimmer mt-2 flex h-[150px] items-center justify-center rounded-xl text-sm text-gray-400">
        {{ puzzleError || 'در حال بارگذاری...' }}
      </div>
    </div>

    <Transition name="pop">
      <div v-if="stage === 'number' && numberChallenge">
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">کد نمایش‌داده‌شده را وارد کنید</label>
        <div class="captcha-frame relative mt-2 overflow-hidden rounded-xl">
          <img :src="numberChallenge.image" alt="کد امنیتی" class="w-full" draggable="false" />
        </div>
        <input
          ref="numberInput"
          v-model="code"
          type="text"
          inputmode="numeric"
          autocomplete="off"
          :maxlength="numberChallenge.length"
          :disabled="numberStatus === 'checking'"
          placeholder="کد را اینجا وارد کنید"
          class="captcha-input mt-3 block w-full rounded-md px-3 py-2 text-center text-lg tracking-[0.3em] text-gray-900 dark:text-white"
          :class="{ 'captcha-shake': numberStatus === 'failed' }"
          @input="onCodeInput"
        />
        <p v-if="numberStatus === 'failed'" class="mt-1 text-center text-xs font-medium text-red-500">
          کد درست نبود — از مرحله‌ی اول دوباره امتحان کنید...
        </p>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
/* Repaints the native range input as a gradient-filled bar with a
   round handle, so it reads as the same control as the on-piece drag
   rather than a leftover default OS slider — it's kept (not removed in
   favor of pure pointer-drag) specifically so keyboard-only users can
   still complete this stage via arrow keys. */
.captcha-range {
  -webkit-appearance: none;
  appearance: none;
  height: 8px;
  border-radius: 9999px;
  background: linear-gradient(
    90deg,
    rgb(var(--c-primary-500)) 0%,
    rgb(var(--c-accent-500)) var(--captcha-progress, 0%),
    rgb(229 231 235) var(--captcha-progress, 0%)
  );
}
html.dark .captcha-range {
  background: linear-gradient(
    90deg,
    rgb(var(--c-primary-500)) 0%,
    rgb(var(--c-accent-500)) var(--captcha-progress, 0%),
    rgb(255 255 255 / 0.1) var(--captcha-progress, 0%)
  );
}
.captcha-range::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 9999px;
  background: white;
  border: 3px solid rgb(var(--c-accent-500));
  box-shadow: 0 1px 4px rgb(0 0 0 / 0.35);
  cursor: pointer;
}
.captcha-range::-moz-range-thumb {
  width: 18px;
  height: 18px;
  border-radius: 9999px;
  background: white;
  border: 3px solid rgb(var(--c-accent-500));
  box-shadow: 0 1px 4px rgb(0 0 0 / 0.35);
  cursor: pointer;
}
.captcha-range:disabled::-webkit-slider-thumb {
  opacity: 0.6;
  cursor: default;
}
.captcha-range::-moz-range-track {
  background: transparent;
}

/* A slowly cycling, colorful gradient — used for the progress pills and
   the fill bar under the puzzle, so the captcha reads as lively rather
   than a static gray control. */
.captcha-glow-bar {
  background: linear-gradient(90deg, rgb(var(--c-primary-500)), rgb(var(--c-accent-500)), rgb(var(--c-primary-500)));
  background-size: 200% 100%;
  animation: captcha-gradient-shift 3s linear infinite;
}

/* A soft animated ring around the whole puzzle frame, again cycling
   through the account's own primary/accent colors. */
.captcha-frame {
  box-shadow: 0 0 0 2px rgb(var(--c-primary-500) / 0.5);
  animation: captcha-frame-glow 2.4s ease-in-out infinite;
}

@keyframes captcha-gradient-shift {
  to { background-position: -200% 0; }
}
@keyframes captcha-frame-glow {
  0%, 100% { box-shadow: 0 0 0 2px rgb(var(--c-primary-500) / 0.45), 0 0 16px -4px rgb(var(--c-primary-500) / 0.5); }
  50% { box-shadow: 0 0 0 2px rgb(var(--c-accent-500) / 0.45), 0 0 16px -4px rgb(var(--c-accent-500) / 0.5); }
}

/* Gentle side-to-side nudge on the untouched piece, inviting the drag —
   stops the instant the user actually grabs it (see :class binding). */
.captcha-invite {
  animation: captcha-invite 1.8s ease-in-out infinite;
}
@keyframes captcha-invite {
  0%, 100% { transform: translateX(0); }
  50% { transform: translateX(6px); }
}

.captcha-shake {
  animation: captcha-shake 0.4s ease-in-out;
}
@keyframes captcha-shake {
  0%, 100% { transform: translateX(0); }
  20% { transform: translateX(-8px); }
  40% { transform: translateX(7px); }
  60% { transform: translateX(-5px); }
  80% { transform: translateX(3px); }
}

.captcha-shimmer {
  background: linear-gradient(
    100deg,
    rgb(var(--c-primary-500) / 0.08) 30%,
    rgb(var(--c-accent-500) / 0.18) 50%,
    rgb(var(--c-primary-500) / 0.08) 70%
  );
  background-size: 300% 100%;
  animation: captcha-gradient-shift 1.6s linear infinite;
}

.captcha-input {
  background-color: rgb(255 255 255 / 0.6);
  border: 1px solid rgb(var(--c-primary-500) / 0.35);
  transition: box-shadow 0.2s ease, border-color 0.2s ease;
}
html.dark .captcha-input {
  background-color: rgb(31 35 41 / 0.55);
}
.captcha-input:focus {
  outline: none;
  border-color: rgb(var(--c-accent-500) / 0.7);
  box-shadow: 0 0 0 3px rgb(var(--c-primary-500) / 0.2), 0 0 0 6px rgb(var(--c-accent-500) / 0.12);
}

.pop-enter-active {
  transition: opacity 0.25s ease, transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.pop-enter-from {
  opacity: 0;
  transform: scale(0.9);
}
.pop-leave-active {
  transition: opacity 0.15s ease;
}
.pop-leave-to {
  opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
  .captcha-glow-bar, .captcha-frame, .captcha-invite, .captcha-shake, .captcha-shimmer {
    animation: none;
  }
}
</style>
