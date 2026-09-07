<script setup lang="ts">
definePageMeta({ layout: 'admin' })
const { request } = useApi()
const authStore = useAuthStore()

const search = ref('')

async function fetchUsers() {
  const qs = search.value ? `?search=${encodeURIComponent(search.value)}` : ''
  const page = await request<{ results: any[] }>(`/auth/admin/users/${qs}`)
  return page.results
}

const { data: users, pending, refresh } = await useAsyncData('admin-users', fetchUsers, { watch: [search] })

const roleLabels: Record<string, string> = { student: 'دانشجو', instructor: 'مدرس', admin: 'ادمین' }
const busyId = ref<number | null>(null)

async function updateUser(user: any, patch: Record<string, any>) {
  busyId.value = user.id
  try {
    await request(`/auth/admin/users/${user.id}/`, { method: 'PATCH', body: patch })
    await refresh()
  } catch (err) {
    console.error(err)
  } finally {
    busyId.value = null
  }
}
</script>

<template>
  <div>
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-xl font-bold text-gray-900 dark:text-white">مدیریت دسترسی کاربران</h1>
      <input
        v-model="search"
        type="search"
        data-tour="user-search"
        placeholder="جست‌وجو بر اساس ایمیل یا نام..."
        class="glass w-64 rounded-md px-3 py-2 text-sm text-gray-900 placeholder:text-gray-500 dark:text-white"
      />
    </div>

    <div v-if="pending" class="mt-6 text-gray-500">در حال بارگذاری...</div>
    <p v-else-if="users && users.length === 0" class="mt-6 text-gray-500">کاربری پیدا نشد.</p>

    <div v-else data-tour="user-table" class="glass mt-6 overflow-x-auto rounded-lg">
      <table class="w-full min-w-[640px] text-start text-sm">
        <thead>
          <tr class="border-b border-white/30 text-xs text-gray-500 dark:border-white/10 dark:text-gray-400">
            <th class="px-4 py-3 font-medium">کاربر</th>
            <th class="px-4 py-3 font-medium">نقش</th>
            <th class="px-4 py-3 font-medium">وضعیت</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="user in users"
            :key="user.id"
            class="border-b border-white/20 last:border-0 dark:border-white/5"
          >
            <td class="px-4 py-3">
              <p class="font-medium text-gray-900 dark:text-white">
                {{ user.first_name }} {{ user.last_name }}
                <span v-if="user.id === authStore.user?.id" class="ms-1 text-xs text-primary-600 dark:text-primary-400">(خودتان)</span>
              </p>
              <p class="text-xs text-gray-500 dark:text-gray-400">{{ user.email }}</p>
            </td>
            <td class="px-4 py-3">
              <select
                :value="user.role"
                :disabled="user.id === authStore.user?.id || busyId === user.id"
                class="glass rounded-md px-2 py-1.5 text-sm text-gray-900 disabled:opacity-50 dark:text-white"
                @change="updateUser(user, { role: ($event.target as HTMLSelectElement).value })"
              >
                <option v-for="(label, value) in roleLabels" :key="value" :value="value">{{ label }}</option>
              </select>
            </td>
            <td class="px-4 py-3">
              <button
                :disabled="user.id === authStore.user?.id || busyId === user.id"
                class="rounded-full px-3 py-1 text-xs font-semibold disabled:opacity-50"
                :class="user.is_active
                  ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300'
                  : 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300'"
                @click="updateUser(user, { is_active: !user.is_active })"
              >
                {{ user.is_active ? 'فعال' : 'غیرفعال' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
