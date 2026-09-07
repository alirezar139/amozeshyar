<script setup lang="ts">
const emit = defineEmits<{ passed: [passToken: string]; reset: [] }>()

const { request } = useApi()

const challenge = ref<any | null>(null)
const sliderX = ref(0)
const status = ref<'idle' | 'checking' | 'passed' | 'failed'>('idle')
const error = ref('')

async function loadChallenge() {
  status.value = 'idle'
  error.value = ''
  sliderX.value = 0
  try {
    challenge.value = await request<any>('/auth/captcha/challenge/')
  } catch {
    error.value = 'بارگذاری پازل ناموفق بود.'
  }
}

async function confirm() {
  if (!challenge.value) return
  status.value = 'checking'
  try {
    const res = await request<{ pass_token: string }>('/auth/captcha/verify/', {
      method: 'POST',
      body: { token: challenge.value.token, x: sliderX.value },
    })
    status.value = 'passed'
    emit('passed', res.pass_token)
  } catch {
    status.value = 'failed'
    emit('reset')
    setTimeout(loadChallenge, 900)
  }
}

const maxX = computed(() => (challenge.value ? challenge.value.width - challenge.value.piece_size : 0))

onMounted(loadChallenge)

defineExpose({ reload: loadChallenge })
</script>

<template>
  <div>
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
        :class="status === 'passed' ? 'drop-shadow-[0_0_8px_rgba(34,197,94,0.9)]' : 'drop-shadow-[0_0_6px_rgba(255,255,255,0.6)]'"
        draggable="false"
        :style="{
          top: `${challenge.piece_y}px`,
          left: `${sliderX}px`,
          width: `${challenge.piece_size}px`,
          height: `${challenge.piece_size}px`,
        }"
      />
      <p v-if="status === 'failed'" class="absolute inset-x-0 bottom-1 text-center text-xs font-medium text-red-300">
        جای درستی نبود — پازل جدید...
      </p>
    </div>
    <div v-else class="mt-1 flex h-[150px] items-center justify-center text-sm text-gray-400">
      {{ error || 'در حال بارگذاری...' }}
    </div>

    <input
      v-if="challenge"
      v-model.number="sliderX"
      type="range"
      min="0"
      :max="maxX"
      :disabled="status === 'checking' || status === 'passed'"
      class="mt-2 w-full"
      @change="confirm"
    />
    <p v-if="status === 'passed'" class="mt-1 text-sm text-emerald-600">✓ تایید شد</p>
  </div>
</template>
