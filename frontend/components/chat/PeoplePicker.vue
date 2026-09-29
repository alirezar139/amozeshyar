<script setup lang="ts">
// Searchable list of people from /conversations/classmates/ (all students
// for the teacher, classmates for a student). Single pick, or multi-select
// with checkmarks when `multiple`.
const props = defineProps<{ multiple?: boolean; exclude?: number[] }>()
const model = defineModel<number[]>({ default: () => [] })
const emit = defineEmits<{ pick: [person: any] }>()

const { request } = useApi()
const query = ref('')
const people = ref<any[]>([])
const allowed = ref(true)
const loading = ref(true)
let timer: ReturnType<typeof setTimeout> | null = null

async function load() {
  loading.value = true
  try {
    const data = await request<{ allowed: boolean; people: any[] }>(`/conversations/classmates/?search=${encodeURIComponent(query.value.trim())}`)
    allowed.value = data.allowed
    people.value = data.people.filter((p) => !props.exclude?.includes(p.id))
  } finally {
    loading.value = false
  }
}
watch(query, () => {
  if (timer) clearTimeout(timer)
  timer = setTimeout(load, 250)
})
onMounted(load)

function toggle(person: any) {
  if (!props.multiple) {
    emit('pick', person)
    return
  }
  model.value = model.value.includes(person.id) ? model.value.filter((id) => id !== person.id) : [...model.value, person.id]
}
</script>

<template>
  <div>
    <label class="relative block">
      <svg class="pointer-events-none absolute start-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-4.35-4.35M17 11a6 6 0 11-12 0 6 6 0 0112 0z" /></svg>
      <input
        v-model="query"
        placeholder="جست‌وجوی نام یا ایمیل…"
        class="w-full rounded-full bg-black/[0.05] py-2 pe-3 ps-9 text-sm text-gray-900 outline-none focus:ring-2 focus:ring-primary-500/40 dark:bg-white/[0.07] dark:text-white"
      >
    </label>
    <p v-if="!allowed" class="px-2 py-8 text-center text-sm text-gray-500 dark:text-gray-400">
      گفت‌وگوی دانشجویان با یکدیگر در این سایت غیرفعال است.
    </p>
    <div v-else class="mt-2 max-h-80 space-y-0.5 overflow-y-auto">
      <p v-if="!loading && !people.length" class="px-2 py-8 text-center text-sm text-gray-500 dark:text-gray-400">
        {{ query ? 'کسی با این مشخصات یافت نشد.' : 'هنوز هم‌کلاسی‌ای ندارید.' }}
      </p>
      <button
        v-for="p in people"
        :key="p.id"
        type="button"
        :class="[
          'flex w-full items-center gap-3 rounded-xl px-2.5 py-2 text-start transition',
          model.includes(p.id) ? 'bg-primary-500/10' : 'hover:bg-black/[0.04] dark:hover:bg-white/5',
        ]"
        @click="toggle(p)"
      >
        <ChatAvatar :src="p.avatar" :name="p.name" />
        <span class="min-w-0 flex-1">
          <span class="block truncate text-sm font-semibold text-gray-900 dark:text-white">{{ p.name }}</span>
          <span class="block truncate text-[11px] text-gray-500" dir="ltr">{{ p.email }}</span>
        </span>
        <span
          v-if="multiple"
          :class="[
            'flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 transition',
            model.includes(p.id) ? 'border-primary-600 bg-primary-600 text-white' : 'border-gray-300 dark:border-white/20',
          ]"
        >
          <svg v-if="model.includes(p.id)" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3.5"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" /></svg>
        </span>
      </button>
    </div>
  </div>
</template>
