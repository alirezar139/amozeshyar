<script setup lang="ts">
// A course's cover photo on its management page: saved as soon as it's picked,
// so there's no separate save button to forget. 16:9, like the course cards.
const props = defineProps<{ courseId: number; src: string | null }>()
const emit = defineEmits<{ changed: [src: string | null] }>()

const { request } = useApi()
const busy = ref(false)
const error = ref('')
const saved = ref(false)

async function save(body: FormData | Record<string, null>) {
  busy.value = true
  error.value = ''
  saved.value = false
  try {
    const updated = await request<{ cover_image: string | null }>(`/courses/manage/${props.courseId}/`, { method: 'PATCH', body })
    emit('changed', updated.cover_image)
    saved.value = true
  } catch (err) {
    error.value = getErrorMessage(err, 'ذخیره‌ی عکس انجام نشد.')
  } finally {
    busy.value = false
  }
}

function onSelect(file: File) {
  const formData = new FormData()
  formData.append('cover_image', file)
  save(formData)
}
</script>

<template>
  <section class="glass rounded-2xl p-6">
    <h2 class="font-semibold text-gray-900 dark:text-white">عکس دوره</h2>
    <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
      روی کارت دوره در صفحه‌ی اول و فهرست دوره‌ها، بالای صفحه‌ی دوره و هنگام اشتراک‌گذاری لینک دیده می‌شود. قاب افقی است (۱۶ به ۹).
    </p>
    <FormImagePicker
      class="mt-4 max-w-md"
      :src="props.src"
      :busy="busy"
      hint="پیشنهاد: ۱۲۸۰×۷۲۰"
      @select="onSelect"
      @remove="save({ cover_image: null })"
    />
    <p v-if="error" class="mt-2 text-sm text-red-600">{{ error }}</p>
    <p v-else-if="saved" class="mt-2 text-sm text-emerald-600">ذخیره شد.</p>
  </section>
</template>
