<script setup lang="ts">
/**
 * Pick, replace or remove one photo. Shows it in the same frame and crop the
 * site uses for it (`frame` is a Tailwind aspect class), so what the
 * instructor sees here is what visitors get. Checks type and size before
 * anything is uploaded; the server checks again (common/validators.py).
 * Saving is the parent's job: listen for `select` and `remove`.
 */
const props = withDefaults(
  defineProps<{
    src: string | null
    frame?: string
    busy?: boolean
    pending?: boolean
    hint?: string
  }>(),
  { frame: 'aspect-video', busy: false, pending: false, hint: '' },
)
const emit = defineEmits<{ select: [file: File]; remove: [] }>()

const MAX_BYTES = 5 * 1024 * 1024
const ALLOWED = ['image/jpeg', 'image/png', 'image/webp']

const input = ref<HTMLInputElement | null>(null)
const dragging = ref(false)
const error = ref('')

function take(file: File | undefined) {
  error.value = ''
  if (!file) return
  if (!ALLOWED.includes(file.type)) {
    error.value = 'فقط عکس JPG، PNG یا WEBP قابل قبول است.'
    return
  }
  if (file.size > MAX_BYTES) {
    error.value = 'حجم عکس بیشتر از ۵ مگابایت است.'
    return
  }
  emit('select', file)
}

function onChange(e: Event) {
  const target = e.target as HTMLInputElement
  take(target.files?.[0])
  target.value = ''
}

function onDrop(e: DragEvent) {
  dragging.value = false
  take(e.dataTransfer?.files?.[0])
}
</script>

<template>
  <div>
    <input ref="input" type="file" accept="image/jpeg,image/png,image/webp" class="hidden" @change="onChange">

    <div v-if="props.src" class="flex flex-col gap-3">
      <div :class="['relative w-full overflow-hidden rounded-xl shadow-md ring-1 ring-black/5 dark:ring-white/10', props.frame]">
        <img :src="props.src" alt="" class="h-full w-full object-cover">
        <span v-if="props.pending" class="absolute inset-x-2 top-2 rounded-full bg-primary-600/95 px-2 py-0.5 text-center text-[11px] font-medium text-white">
          جدید، هنوز ذخیره نشده
        </span>
        <div v-if="props.busy" class="absolute inset-0 flex items-center justify-center bg-black/40 text-sm font-medium text-white">
          در حال ذخیره...
        </div>
      </div>
      <div class="flex flex-wrap gap-2">
        <button
          type="button"
          :disabled="props.busy"
          class="glass rounded-lg px-3 py-1.5 text-sm font-medium text-gray-800 disabled:opacity-50 dark:text-gray-100"
          @click="input?.click()"
        >
          تغییر عکس
        </button>
        <button
          type="button"
          :disabled="props.busy"
          class="rounded-lg px-3 py-1.5 text-sm font-medium text-red-600 hover:bg-red-500/10 disabled:opacity-50"
          @click="emit('remove')"
        >
          حذف
        </button>
      </div>
    </div>

    <button
      v-else
      type="button"
      :disabled="props.busy"
      :class="[
        'flex w-full flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed px-4 py-8 text-center transition disabled:opacity-50',
        dragging ? 'border-primary-500 bg-primary-500/10' : 'border-gray-300 hover:border-primary-400 hover:bg-primary-500/5 dark:border-white/15',
      ]"
      @click="input?.click()"
      @dragover.prevent="dragging = true"
      @dragleave.prevent="dragging = false"
      @drop.prevent="onDrop"
    >
      <svg class="h-9 w-9 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
      <span class="text-sm font-medium text-gray-700 dark:text-gray-200">عکس را اینجا بکشید یا کلیک کنید</span>
      <span class="text-xs text-gray-500 dark:text-gray-400">JPG، PNG یا WEBP، تا ۵ مگابایت{{ props.hint ? ` · ${props.hint}` : '' }}</span>
    </button>

    <p v-if="error" class="mt-2 text-sm text-red-600">{{ error }}</p>
  </div>
</template>
