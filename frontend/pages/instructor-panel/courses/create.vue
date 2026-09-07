<script setup lang="ts">
definePageMeta({ layout: 'instructor' })
const { request } = useApi()

const { data: categories } = await useAsyncData('categories', async () => {
  const page = await request<{ results: any[] }>('/categories/')
  return page.results
})

const form = reactive({
  title: '',
  subtitle: '',
  description: '',
  category: null as number | null,
  level: 'beginner',
  price: 0,
})
const submitting = ref(false)
const error = ref('')

async function onSubmit() {
  error.value = ''
  submitting.value = true
  try {
    await request('/courses/mine/', { method: 'POST', body: form })
    await navigateTo('/instructor-panel/courses')
  } catch {
    error.value = 'ثبت دوره ناموفق بود.'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="max-w-2xl">
    <h1 class="text-xl font-bold text-gray-900 dark:text-white">ساخت دوره‌ی جدید</h1>
    <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
      دوره‌ی شما پس از ثبت، در صف تایید ادمین قرار می‌گیرد و تا تایید نشود عمومی نخواهد شد.
    </p>

    <form data-tour="course-create-form" class="mt-6 space-y-4" @submit.prevent="onSubmit">
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">عنوان دوره</label>
        <input
          v-model="form.title"
          required
          class="glass mt-1 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white"
        >
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">زیرعنوان</label>
        <input
          v-model="form.subtitle"
          class="glass mt-1 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white"
        >
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">توضیحات</label>
        <textarea
          v-model="form.description"
          rows="5"
          class="glass mt-1 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white"
        />
      </div>
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">دسته‌بندی</label>
          <select
            v-model="form.category"
            required
            class="glass mt-1 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white"
          >
            <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">سطح</label>
          <select
            v-model="form.level"
            class="glass mt-1 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white"
          >
            <option value="beginner">مبتدی</option>
            <option value="intermediate">متوسط</option>
            <option value="advanced">پیشرفته</option>
          </select>
        </div>
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">قیمت (تومان)</label>
        <input
          v-model.number="form.price"
          type="number"
          min="0"
          class="glass mt-1 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white"
        >
      </div>
      <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
      <button
        type="submit"
        :disabled="submitting"
        class="rounded-md bg-primary-600 px-5 py-2 text-sm font-semibold text-white hover:bg-primary-500 disabled:opacity-50"
      >
        {{ submitting ? 'در حال ثبت...' : 'ثبت دوره' }}
      </button>
    </form>
  </div>
</template>
