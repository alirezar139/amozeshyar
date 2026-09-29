<script setup lang="ts">
definePageMeta({ layout: 'admin' })
const { request } = useApi()

const { data: categories } = await useAsyncData('admin-create-course-categories', async () => {
  const page = await request<{ results: any[] }>('/categories/')
  return page.results
})

const form = reactive({
  category: null as number | null,
  title: '',
  subtitle: '',
  description: '',
  level: 'beginner',
  price: 0,
})
const error = ref('')
const success = ref(false)
const loading = ref(false)

async function onSubmit() {
  error.value = ''
  loading.value = true
  try {
    await request('/courses/manage/', { method: 'POST', body: form })
    success.value = true
  } catch (err) {
    error.value = getErrorMessage(err, 'ثبت دوره ناموفق بود.')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="max-w-2xl">
    <h1 class="text-xl font-bold text-gray-900 dark:text-white">دوره‌ی جدید</h1>
    <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
      دوره بلافاصله روی سایت منتشر می‌شود؛ بعداً از لیست دوره‌ها می‌توانید آن را به پیش‌نویس برگردانید.
    </p>

    <form data-tour="admin-course-create-form" class="glass mt-6 space-y-4 rounded-2xl p-6" @submit.prevent="onSubmit">
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">عنوان دوره</label>
        <input v-model="form.title" required class="glass mt-1 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white">
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">زیرعنوان</label>
        <input v-model="form.subtitle" class="glass mt-1 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white">
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">توضیحات</label>
        <textarea v-model="form.description" rows="4" class="glass mt-1 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white" />
      </div>
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">دسته‌بندی</label>
          <select v-model="form.category" required class="glass mt-1 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white">
            <option :value="null" disabled>انتخاب دسته‌بندی</option>
            <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">سطح</label>
          <select v-model="form.level" class="glass mt-1 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white">
            <option value="beginner">مبتدی</option>
            <option value="intermediate">متوسط</option>
            <option value="advanced">پیشرفته</option>
          </select>
        </div>
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">قیمت (تومان)</label>
        <input v-model.number="form.price" type="number" min="0" class="glass mt-1 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white">
      </div>
      <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
      <p v-if="success" class="text-sm text-emerald-600">دوره با موفقیت ثبت و منتشر شد.</p>
      <div class="flex gap-3">
        <button
          type="submit"
          :disabled="loading"
          class="rounded-md bg-primary-600 px-5 py-2 text-sm font-semibold text-white hover:bg-primary-500 disabled:opacity-50"
        >
          {{ loading ? 'در حال ثبت...' : 'ثبت دوره' }}
        </button>
        <NuxtLink to="/admin/courses" class="glass rounded-md px-5 py-2 text-sm text-gray-700 dark:text-gray-200">
          بازگشت به لیست
        </NuxtLink>
      </div>
    </form>
  </div>
</template>
