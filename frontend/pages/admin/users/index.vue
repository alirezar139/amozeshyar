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

const roleLabels: Record<string, string> = { student: 'دانشجو', admin: 'ادمین' }
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

// ---------- password ----------
// The current password can't be shown (only its hash is stored); the admin
// sets a new one and sees it here once, to pass on to the user.
const pwUser = ref<any>(null)
const pwValue = ref('')
const pwVisible = ref(false)
const pwSaving = ref(false)
const pwError = ref('')
const pwDone = ref('')
const copied = ref(false)

function openPassword(user: any) {
  pwUser.value = user
  pwValue.value = ''
  pwVisible.value = false
  pwError.value = ''
  pwDone.value = ''
  copied.value = false
}

function randomPassword() {
  const alphabet = 'abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'
  const bytes = crypto.getRandomValues(new Uint32Array(12))
  pwValue.value = Array.from(bytes, (b) => alphabet[b % alphabet.length]).join('')
  pwVisible.value = true
}

async function savePassword() {
  pwSaving.value = true
  pwError.value = ''
  try {
    await request(`/auth/admin/users/${pwUser.value.id}/set-password/`, { method: 'POST', body: { password: pwValue.value } })
    pwDone.value = pwValue.value
  } catch (err: any) {
    const messages = err?.data?.password
    pwError.value = Array.isArray(messages) ? messages.join(' ') : getErrorMessage(err, 'تغییر رمز ناموفق بود.')
  } finally {
    pwSaving.value = false
  }
}

// ---------- courses (manual enrollment) ----------
const coursesUser = ref<any>(null)
const userCourses = ref<any[]>([])
const coursesError = ref('')
const togglingCourse = ref<number | null>(null)

async function openCourses(user: any) {
  coursesUser.value = user
  userCourses.value = []
  coursesError.value = ''
  try {
    userCourses.value = await request<any[]>(`/auth/admin/users/${user.id}/courses/`)
  } catch (err) {
    coursesError.value = getFirstErrorMessage(err, 'دوره‌ها بارگذاری نشد.')
  }
}

async function toggleCourse(course: any) {
  togglingCourse.value = course.id
  coursesError.value = ''
  try {
    userCourses.value = await request<any[]>(`/auth/admin/users/${coursesUser.value.id}/courses/`, {
      method: 'POST',
      body: { course: course.id, enrolled: !course.enrolled },
    })
  } catch (err) {
    coursesError.value = getFirstErrorMessage(err, 'تغییر ثبت‌نام ناموفق بود.')
  } finally {
    togglingCourse.value = null
  }
}

async function copyPassword() {
  await navigator.clipboard.writeText(pwDone.value)
  copied.value = true
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
            <th class="px-4 py-3 font-medium">رمز عبور</th>
            <th class="px-4 py-3 font-medium">دوره‌ها</th>
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
            <td class="px-4 py-3">
              <button
                type="button"
                class="rounded-md px-3 py-1 text-xs font-semibold text-primary-700 ring-1 ring-primary-500/30 hover:bg-primary-500/10 dark:text-primary-300"
                @click="openPassword(user)"
              >
                🔑 تغییر رمز
              </button>
            </td>
            <td class="px-4 py-3">
              <button
                v-if="user.role === 'student'"
                type="button"
                class="rounded-md px-3 py-1 text-xs font-semibold text-primary-700 ring-1 ring-primary-500/30 hover:bg-primary-500/10 dark:text-primary-300"
                @click="openCourses(user)"
              >
                📚 دوره‌ها
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <Teleport to="body">
      <div v-if="coursesUser" class="fixed inset-0 z-[70] flex items-center justify-center bg-black/40 p-4 backdrop-blur-sm" @click.self="coursesUser = null">
        <div class="glass w-full max-w-md rounded-2xl p-6">
          <h2 class="text-lg font-bold text-gray-900 dark:text-white">ثبت‌نام در دوره‌ها</h2>
          <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">{{ coursesUser.first_name }} {{ coursesUser.last_name }} · <span dir="ltr">{{ coursesUser.email }}</span></p>
          <p class="mt-3 rounded-lg bg-black/[0.04] px-3 py-2 text-xs leading-5 text-gray-600 dark:bg-white/5 dark:text-gray-300">
            دانشجوی ثبت‌نام‌شده بدون پرداخت به ویدیوها، فایل‌ها، آزمون‌ها و گروه آن دوره دسترسی پیدا می‌کند (مثلاً برای پرداخت حضوری).
          </p>
          <ul class="mt-4 max-h-80 space-y-1.5 overflow-y-auto">
            <li v-for="c in userCourses" :key="c.id">
              <button
                type="button"
                :disabled="togglingCourse === c.id"
                :class="[
                  'flex w-full items-center gap-3 rounded-xl border-2 px-3 py-2.5 text-start text-sm transition disabled:opacity-50',
                  c.enrolled ? 'border-emerald-500 bg-emerald-500/10' : 'border-black/10 hover:border-primary-300 dark:border-white/10',
                ]"
                @click="toggleCourse(c)"
              >
                <span :class="['flex h-5 w-5 shrink-0 items-center justify-center rounded-md border-2 text-xs text-white', c.enrolled ? 'border-emerald-500 bg-emerald-500' : 'border-gray-300 dark:border-gray-600']">{{ c.enrolled ? '✓' : '' }}</span>
                <span class="flex-1 text-gray-900 dark:text-white">{{ c.title }}</span>
                <span v-if="c.status !== 'published'" class="text-[11px] text-gray-500">پیش‌نویس</span>
              </button>
            </li>
          </ul>
          <p v-if="coursesError" class="mt-2 text-sm text-red-600">{{ coursesError }}</p>
          <button type="button" class="mt-5 w-full rounded-xl bg-primary-600 py-2 text-sm font-semibold text-white hover:bg-primary-700" @click="coursesUser = null">بستن</button>
        </div>
      </div>

      <div v-if="pwUser" class="fixed inset-0 z-[70] flex items-center justify-center bg-black/40 p-4 backdrop-blur-sm" @click.self="pwUser = null">
        <div class="glass w-full max-w-md rounded-2xl p-6">
          <h2 class="text-lg font-bold text-gray-900 dark:text-white">تغییر رمز عبور</h2>
          <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">{{ pwUser.first_name }} {{ pwUser.last_name }} · <span dir="ltr">{{ pwUser.email }}</span></p>

          <template v-if="!pwDone">
            <p class="mt-3 rounded-lg bg-black/[0.04] px-3 py-2 text-xs leading-5 text-gray-600 dark:bg-white/5 dark:text-gray-300">
              رمز فعلی قابل نمایش نیست، چون رمزها رمزنگاری‌شده (یک‌طرفه) ذخیره می‌شوند. یک رمز جدید بگذارید؛ کاربر از بقیه‌ی دستگاه‌ها خارج می‌شود.
            </p>
            <form class="mt-4" @submit.prevent="savePassword">
              <FormPasswordInput
                v-model="pwValue"
                v-model:visible="pwVisible"
                required
                minlength="10"
                autocomplete="new-password"
                placeholder="رمز جدید (حداقل ۱۰ کاراکتر)"
              />
              <button type="button" class="mt-2 text-xs font-semibold text-primary-600 hover:underline dark:text-primary-400" @click="randomPassword">🎲 ساخت رمز تصادفی</button>
              <p v-if="pwError" class="mt-2 text-sm text-red-600">{{ pwError }}</p>
              <div class="mt-5 flex gap-3">
                <button type="button" class="flex-1 rounded-xl border border-black/10 py-2 text-sm text-gray-700 dark:border-white/10 dark:text-gray-200" @click="pwUser = null">انصراف</button>
                <button type="submit" :disabled="pwSaving" class="flex-1 rounded-xl bg-primary-600 py-2 text-sm font-semibold text-white hover:bg-primary-700 disabled:opacity-50">
                  {{ pwSaving ? 'در حال ذخیره…' : 'ذخیره‌ی رمز' }}
                </button>
              </div>
            </form>
          </template>

          <template v-else>
            <p class="mt-4 text-sm font-semibold text-emerald-600">✓ رمز جدید ذخیره شد. آن را به کاربر بدهید:</p>
            <div class="mt-2 flex items-center gap-2 rounded-xl bg-black/[0.04] p-3 dark:bg-white/5">
              <code class="flex-1 select-all break-all text-base font-bold text-gray-900 dark:text-white" dir="ltr">{{ pwDone }}</code>
              <button type="button" class="shrink-0 rounded-lg bg-primary-600 px-3 py-1.5 text-xs font-semibold text-white" @click="copyPassword">{{ copied ? 'کپی شد ✓' : 'کپی' }}</button>
            </div>
            <p class="mt-2 text-xs text-gray-500">بعد از بستن این پنجره، رمز دیگر نمایش داده نمی‌شود.</p>
            <button type="button" class="mt-5 w-full rounded-xl bg-primary-600 py-2 text-sm font-semibold text-white hover:bg-primary-700" @click="pwUser = null">بستن</button>
          </template>
        </div>
      </div>
    </Teleport>
  </div>
</template>
