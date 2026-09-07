<script setup lang="ts">
const emit = defineEmits<{ passed: [passToken: string]; reset: [] }>()

const { request } = useApi()

const stage = ref<'puzzle' | 'number'>('puzzle')

// Stage 1: drag the gem into its socket.
const challenge = ref<any | null>(null)
const sliderX = ref(0)
const puzzleStatus = ref<'idle' | 'checking' | 'passed' | 'failed'>('idle')
const puzzleError = ref('')

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
    stage.value = 'number'
    await nextTick()
    numberInput.value?.focus()
  } catch {
    puzzleStatus.value = 'failed'
    setTimeout(loadChallenge, 900)
  }
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

onMounted(loadChallenge)

defineExpose({ reload: loadChallenge })
</script>

<template>
  <div>
    <p class="mb-2 text-xs font-medium text-gray-500 dark:text-gray-400">
      مرحله {{ stage === 'puzzle' ? '۱' : '۲' }} از ۲
    </p>

    <div v-if="stage === 'puzzle'">
      <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">قطعه‌ی الماس را به جای خودش بکشید</label>
      <div
        v-if="challenge"
        class="relative mt-1 overflow-hidden rounded-lg"
        :style="{ width: `${challenge.width}px`, height: `${challenge.height}px`, maxWidth: '100%' }"
      >
        <img :src="challenge.background" alt="" class="absolute inset-0 h-full w-full object-cover" draggable="false" />
        <img
          :src="challenge.piece"
          alt=""
          class="absolute transition-[filter] duration-200"
          :class="puzzleStatus === 'passed' ? 'drop-shadow-[0_0_8px_rgba(34,197,94,0.9)]' : 'drop-shadow-[0_0_6px_rgba(255,255,255,0.6)]'"
          draggable="false"
          :style="{
            top: `${challenge.piece_y}px`,
            left: `${sliderX}px`,
            width: `${challenge.piece_size}px`,
            height: `${challenge.piece_size}px`,
          }"
        />
        <p v-if="puzzleStatus === 'failed'" class="absolute inset-x-0 bottom-1 text-center text-xs font-medium text-red-300">
          جای درستی نبود — پازل جدید...
        </p>
      </div>
      <div v-else class="mt-1 flex h-[150px] items-center justify-center text-sm text-gray-400">
        {{ puzzleError || 'در حال بارگذاری...' }}
      </div>

      <input
        v-if="challenge"
        v-model.number="sliderX"
        type="range"
        min="0"
        :max="maxX"
        :disabled="puzzleStatus === 'checking' || puzzleStatus === 'passed'"
        class="mt-2 w-full"
        @change="confirmPuzzle"
      />
    </div>

    <div v-else-if="numberChallenge">
      <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">کد نمایش‌داده‌شده را وارد کنید</label>
      <div class="relative mt-1 overflow-hidden rounded-lg">
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
        class="glass mt-2 block w-full rounded-md px-3 py-2 text-center text-lg tracking-[0.3em] text-gray-900 dark:text-white"
        @input="onCodeInput"
      />
      <p v-if="numberStatus === 'failed'" class="mt-1 text-center text-xs font-medium text-red-500">
        کد درست نبود — از مرحله‌ی اول دوباره امتحان کنید...
      </p>
    </div>
  </div>
</template>
