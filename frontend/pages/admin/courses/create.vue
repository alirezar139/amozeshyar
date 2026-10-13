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

const newCategory = ref('')
const addingCategory = ref(false)
const showNewCategory = ref(false)

async function addCategory() {
  const name = newCategory.value.trim()
  if (!name) return
  error.value = ''
  addingCategory.value = true
  try {
    const created = await request<any>('/categories/', { method: 'POST', body: { name } })
    categories.value = [...(categories.value || []), created]
    form.category = created.id
    newCategory.value = ''
    showNewCategory.value = false
  } catch (err) {
    error.value = getErrorMessage(err, 'ساخت دسته‌بندی انجام نشد.')
  } finally {
    addingCategory.value = false
  }
}

async function onSubmit() {
  error.value = ''
  // The placeholder <option> has no empty value, so the browser's `required` can't catch this.
  if (!form.category) {
    error.value = 'دسته‌بندی دوره را انتخاب کنید.'
    return
  }
  loading.value = true
  try {
    await request('/courses/manage/', { method: 'POST', body: form })
    success.value = true
  } catch (err) {
    error.value = getErrorMessage(err, 'ثبت دوره انجام نشد.')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="max-w-2xl">
    <h1 class="text-xl font-bold text-gray-900 dark:text-white">دوره‌ی جدید</h1>
    <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
      دوره بلافاصله در سایت منتشر می‌شود؛ در صورت نیاز می‌توانید بعداً از فهرست دوره‌ها آن را به پیش‌نویس بازگردانید.
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
          <select v-model="form.category" class="glass mt-1 block w-full rounded-md px-3 py-2 text-sm text-gray-900 dark:text-white">
            <option :value="null" disabled>{{ categories?.length ? 'انتخاب دسته‌بندی' : 'هنوز دسته‌بندی‌ای ندارید' }}</option>
            <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
          <button
            v-if="!showNewCategory"
            type="button"
            class="mt-1 text-xs font-medium text-primary-600 hover:text-primary-500 dark:text-primary-400"
            @click="showNewCategory = true"
          >
            + دسته‌بندی جدید
          </button>
          <div v-else class="mt-2 flex gap-2">
            <input
              v-model="newCategory"
              placeholder="نام دسته‌بندی، مثلاً برنامه‌نویسی"
              class="glass block w-full rounded-md px-3 py-1.5 text-sm text-gray-900 dark:text-white"
              @keydown.enter.prevent="addCategory"
            >
            <button
              type="button"
              :disabled="addingCategory || !newCategory.trim()"
              class="shrink-0 rounded-md bg-primary-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-primary-500 disabled:opacity-50"
              @click="addCategory"
            >
              {{ addingCategory ? '...' : 'افزودن' }}
            </button>
          </div>
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
          بازگشت به فهرست
        </NuxtLink>
      </div>
    </form>
  </div>
</template>
