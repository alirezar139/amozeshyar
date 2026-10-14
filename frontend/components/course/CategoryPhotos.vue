<script setup lang="ts">
// Photos for the homepage's category carousel: one wide banner per category,
// saved as soon as it's picked. Categories without a photo show a plain gradient.
const { request } = useApi()

interface Category { id: number; name: string; image: string | null; course_count: number }

const { data: categories } = await useAsyncData('admin-category-photos', async () => {
  const page = await request<{ results: Category[] }>('/categories/?page_size=100')
  return page.results
})

const busyId = ref<number | null>(null)
const errors = ref<Record<number, string>>({})

async function save(category: Category, body: FormData | Record<string, null>) {
  busyId.value = category.id
  errors.value = { ...errors.value, [category.id]: '' }
  try {
    const updated = await request<Category>(`/categories/${category.id}/`, { method: 'PATCH', body })
    category.image = updated.image
  } catch (err) {
    errors.value = { ...errors.value, [category.id]: getErrorMessage(err, 'ذخیره‌ی عکس انجام نشد.') }
  } finally {
    busyId.value = null
  }
}

function onSelect(category: Category, file: File) {
  const formData = new FormData()
  formData.append('image', file)
  save(category, formData)
}
</script>

<template>
  <section v-if="categories?.length" class="glass rounded-2xl p-6">
    <h2 class="font-semibold text-gray-900 dark:text-white">عکس دسته‌بندی‌ها</h2>
    <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
      در اسلایدر دسته‌بندی‌های صفحه‌ی اول، پشت نام هر دسته دیده می‌شود. قاب پهن است؛ وسط عکس دیده می‌شود.
      دسته‌ای که دوره‌ی منتشرشده ندارد در صفحه‌ی اول نمایش داده نمی‌شود.
    </p>
    <div class="mt-5 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
      <div v-for="category in categories" :key="category.id" class="min-w-0">
        <p class="mb-2 flex items-baseline justify-between gap-2 text-sm">
          <span class="truncate font-medium text-gray-900 dark:text-white">{{ category.name }}</span>
          <span class="shrink-0 text-xs text-gray-500 dark:text-gray-400">{{ category.course_count.toLocaleString('fa-IR') }} دوره</span>
        </p>
        <FormImagePicker
          :src="category.image"
          frame="aspect-[5/2]"
          :busy="busyId === category.id"
          @select="(file) => onSelect(category, file)"
          @remove="save(category, { image: null })"
        />
        <p v-if="errors[category.id]" class="mt-2 text-sm text-red-600">{{ errors[category.id] }}</p>
      </div>
    </div>
  </section>
</template>
