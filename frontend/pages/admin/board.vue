<script setup lang="ts">
// The teacher's kanban board of their own work. Drag cards between (and
// within) columns on desktop; on touch devices, open a card and pick its
// column. Positions are fractional, so a move is a single PATCH.
definePageMeta({ layout: 'admin' })
useSeoMeta({ title: 'برنامه‌ی کارها' })

const { request } = useApi()
const { formatGregorianDate } = useJalali()

type Column = 'idea' | 'in_progress' | 'ready' | 'published'
interface Card {
  id: number
  title: string
  description: string
  column: Column
  position: number
  color: string
  due_date: string | null
  course: number | null
  course_title: string | null
}

const COLUMNS: { key: Column; label: string; dot: string; tint: string }[] = [
  { key: 'idea', label: 'ایده', dot: 'bg-violet-500', tint: 'from-violet-500/10' },
  { key: 'in_progress', label: 'در حال آماده‌سازی', dot: 'bg-amber-500', tint: 'from-amber-500/10' },
  { key: 'ready', label: 'آماده', dot: 'bg-sky-500', tint: 'from-sky-500/10' },
  { key: 'published', label: 'منتشرشده', dot: 'bg-emerald-500', tint: 'from-emerald-500/10' },
]
const COLORS: { key: string; class: string; label: string }[] = [
  { key: '', class: 'bg-gray-300 dark:bg-gray-600', label: 'بدون رنگ' },
  { key: 'red', class: 'bg-red-500', label: 'قرمز' },
  { key: 'amber', class: 'bg-amber-500', label: 'نارنجی' },
  { key: 'green', class: 'bg-emerald-500', label: 'سبز' },
  { key: 'blue', class: 'bg-sky-500', label: 'آبی' },
  { key: 'purple', class: 'bg-violet-500', label: 'بنفش' },
]
const colorClass = (key: string) => COLORS.find((c) => c.key === key)?.class ?? ''

const cardsAsync = useAsyncData('board-cards', () => request<Card[]>('/board/cards/'))
const coursesAsync = useAsyncData('board-courses', async () => (await request<{ results: any[] }>('/courses/manage/')).results)
await Promise.all([cardsAsync, coursesAsync])
const { data: cards, pending } = cardsAsync
const { data: courses } = coursesAsync

const error = ref('')
const byColumn = computed(() => {
  const groups: Record<Column, Card[]> = { idea: [], in_progress: [], ready: [], published: [] }
  for (const card of cards.value ?? []) groups[card.column]?.push(card)
  for (const list of Object.values(groups)) list.sort((a, b) => a.position - b.position || a.id - b.id)
  return groups
})

// ---------- quick add ----------
const addingTo = ref<Column | null>(null)
const newTitle = ref('')
async function quickAdd(column: Column) {
  const title = newTitle.value.trim()
  if (!title) {
    addingTo.value = null
    return
  }
  try {
    const card = await request<Card>('/board/cards/', { method: 'POST', body: { title, column } })
    cards.value = [...(cards.value ?? []), card]
    newTitle.value = ''
  } catch (err) {
    error.value = getErrorMessage(err, 'ساخت کارت ناموفق بود.')
  }
}

// ---------- drag & drop ----------
const dragId = ref<number | null>(null)
const dropColumn = ref<Column | null>(null)
const dropIndex = ref(0)

function onDragStart(card: Card, e: DragEvent) {
  dragId.value = card.id
  e.dataTransfer?.setData('text/plain', String(card.id))
  if (e.dataTransfer) e.dataTransfer.effectAllowed = 'move'
}
function onDragEnd() {
  dragId.value = null
  dropColumn.value = null
}
function onDragOver(column: Column, e: DragEvent) {
  if (dragId.value === null) return
  e.preventDefault()
  dropColumn.value = column
  // Insertion index from the pointer's height against each card's middle.
  const list = (e.currentTarget as HTMLElement).querySelectorAll<HTMLElement>('[data-card-id]')
  let index = 0
  for (const el of Array.from(list)) {
    if (Number(el.dataset.cardId) === dragId.value) continue
    const rect = el.getBoundingClientRect()
    if (e.clientY > rect.top + rect.height / 2) index++
  }
  dropIndex.value = index
}
function onDragLeave(column: Column, e: DragEvent) {
  const related = e.relatedTarget as Node | null
  if (!related || !(e.currentTarget as HTMLElement).contains(related)) {
    if (dropColumn.value === column) dropColumn.value = null
  }
}
async function onDrop(column: Column) {
  const id = dragId.value
  const index = dropIndex.value
  onDragEnd()
  if (id === null) return
  await moveCard(id, column, index)
}

async function moveCard(id: number, column: Column, index: number) {
  const card = cards.value?.find((c) => c.id === id)
  if (!card) return
  const siblings = byColumn.value[column].filter((c) => c.id !== id)
  const before = siblings[index - 1]?.position
  const after = siblings[index]?.position
  const position =
    before === undefined && after === undefined ? 1024
    : before === undefined ? after! - 1024
    : after === undefined ? before + 1024
    : (before + after) / 2
  if (card.column === column && card.position === position) return
  const previous = { column: card.column, position: card.position }
  Object.assign(card, { column, position })
  try {
    await request(`/board/cards/${id}/`, { method: 'PATCH', body: { column, position } })
  } catch (err) {
    Object.assign(card, previous)
    error.value = getErrorMessage(err, 'جابه‌جایی ذخیره نشد.')
  }
}

// ---------- edit modal ----------
const editing = ref<Card | null>(null)
const draft = reactive({ title: '', description: '', color: '', due_date: '' as string, course: null as number | null, column: 'idea' as Column })
const saving = ref(false)

function openCard(card: Card) {
  editing.value = card
  Object.assign(draft, {
    title: card.title,
    description: card.description,
    color: card.color,
    due_date: card.due_date ?? '',
    course: card.course,
    column: card.column,
  })
}
async function saveCard() {
  if (!editing.value || !draft.title.trim()) return
  saving.value = true
  try {
    const card = editing.value
    const movedColumn = draft.column !== card.column
    const updated = await request<Card>(`/board/cards/${card.id}/`, {
      method: 'PATCH',
      body: { ...draft, title: draft.title.trim(), due_date: draft.due_date || null },
    })
    Object.assign(card, updated)
    if (movedColumn) await moveCard(card.id, draft.column, byColumn.value[draft.column].length)
    editing.value = null
  } catch (err) {
    error.value = getErrorMessage(err, 'ذخیره نشد.')
  } finally {
    saving.value = false
  }
}
async function deleteCard() {
  if (!editing.value || !confirm(`کارت «${editing.value.title}» حذف شود؟`)) return
  const id = editing.value.id
  await request(`/board/cards/${id}/`, { method: 'DELETE' })
  cards.value = (cards.value ?? []).filter((c) => c.id !== id)
  editing.value = null
}

function dueState(date: string | null) {
  if (!date) return ''
  const today = new Date().toISOString().slice(0, 10)
  return date < today ? 'overdue' : date === today ? 'today' : 'later'
}
</script>

<template>
  <div>
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-xl font-bold text-gray-900 dark:text-white">برنامه‌ی کارها</h1>
        <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">کارهای آماده‌سازی دوره‌ها را با کشیدن کارت‌ها میان ستون‌ها مدیریت کنید.</p>
      </div>
    </div>
    <p v-if="error" class="mt-3 text-sm text-red-600">{{ error }}</p>

    <div v-if="pending && !cards" class="mt-6 text-gray-500">در حال بارگذاری...</div>
    <div v-else data-tour="board-columns" class="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
      <section
        v-for="col in COLUMNS"
        :key="col.key"
        :class="[
          'flex min-h-[16rem] flex-col rounded-2xl bg-gradient-to-b to-transparent p-3 ring-1 transition',
          col.tint,
          dropColumn === col.key ? 'ring-2 ring-primary-500' : 'ring-black/5 dark:ring-white/10',
        ]"
        @dragover="onDragOver(col.key, $event)"
        @dragleave="onDragLeave(col.key, $event)"
        @drop.prevent="onDrop(col.key)"
      >
        <header class="mb-3 flex items-center gap-2 px-1">
          <span :class="['h-2.5 w-2.5 rounded-full', col.dot]" />
          <h2 class="font-bold text-gray-800 dark:text-gray-100">{{ col.label }}</h2>
          <span class="rounded-full bg-black/5 px-2 text-xs text-gray-600 dark:bg-white/10 dark:text-gray-300">
            {{ byColumn[col.key].length.toLocaleString('fa-IR') }}
          </span>
        </header>

        <div class="flex flex-1 flex-col gap-2.5">
          <template v-for="(card, i) in byColumn[col.key]" :key="card.id">
            <div v-if="dropColumn === col.key && dropIndex === i && dragId !== card.id" class="h-1 rounded-full bg-primary-500" />
            <article
              :data-card-id="card.id"
              data-tour="board-card"
              draggable="true"
              :class="[
                'glass group relative cursor-grab overflow-hidden rounded-xl p-3 ps-4 transition hover:-translate-y-0.5 hover:shadow-lg active:cursor-grabbing',
                dragId === card.id ? 'opacity-40' : '',
              ]"
              @dragstart="onDragStart(card, $event)"
              @dragend="onDragEnd"
              @click="openCard(card)"
            >
              <span v-if="card.color" :class="['absolute inset-y-0 start-0 w-1.5', colorClass(card.color)]" />
              <p class="font-semibold leading-6 text-gray-900 dark:text-white">{{ card.title }}</p>
              <p v-if="card.description" class="mt-1 line-clamp-2 text-xs leading-5 text-gray-600 dark:text-gray-400">{{ card.description }}</p>
              <div v-if="card.course_title || card.due_date" class="mt-2 flex flex-wrap gap-1.5">
                <span v-if="card.course_title" class="rounded-md bg-primary-500/10 px-2 py-0.5 text-[11px] text-primary-700 dark:text-primary-300">{{ card.course_title }}</span>
                <span
                  v-if="card.due_date"
                  :class="[
                    'rounded-md px-2 py-0.5 text-[11px]',
                    dueState(card.due_date) === 'overdue' ? 'bg-red-500/15 text-red-700 dark:text-red-300'
                    : dueState(card.due_date) === 'today' ? 'bg-amber-500/15 text-amber-700 dark:text-amber-300'
                    : 'bg-black/5 text-gray-600 dark:bg-white/10 dark:text-gray-300',
                  ]"
                >
                  ⏰ {{ formatGregorianDate(new Date(card.due_date)) }}
                </span>
              </div>
            </article>
          </template>
          <div v-if="dropColumn === col.key && dropIndex >= byColumn[col.key].filter((c) => c.id !== dragId).length" class="h-1 rounded-full bg-primary-500" />

          <!-- quick add -->
          <form v-if="addingTo === col.key" class="mt-1" @submit.prevent="quickAdd(col.key)">
            <input
              v-model="newTitle"
              autofocus
              placeholder="عنوان کار… (Enter)"
              class="glass w-full rounded-xl px-3 py-2 text-sm text-gray-900 outline-none focus:ring-2 focus:ring-primary-500/40 dark:text-white"
              @blur="quickAdd(col.key)"
              @keydown.esc="addingTo = null; newTitle = ''"
            >
          </form>
          <button
            v-else
            type="button"
            data-tour="board-add"
            class="mt-1 rounded-xl border-2 border-dashed border-black/10 py-2 text-sm text-gray-500 transition hover:border-primary-400 hover:text-primary-600 dark:border-white/10 dark:text-gray-400"
            @click="addingTo = col.key; newTitle = ''"
          >
            + افزودن کار
          </button>
        </div>
      </section>
    </div>

    <!-- edit modal -->
    <Teleport to="body">
      <div v-if="editing" class="fixed inset-0 z-[70] flex items-center justify-center bg-black/40 p-4 backdrop-blur-sm" @click.self="editing = null">
        <form class="glass w-full max-w-lg space-y-4 rounded-2xl p-6" @submit.prevent="saveCard">
          <input
            v-model="draft.title"
            required
            class="w-full bg-transparent text-lg font-bold text-gray-900 outline-none dark:text-white"
          >
          <textarea
            v-model="draft.description"
            rows="4"
            placeholder="توضیحات…"
            class="glass w-full resize-y rounded-xl px-3 py-2 text-sm text-gray-900 outline-none focus:ring-2 focus:ring-primary-500/40 dark:text-white"
          />
          <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <label class="text-sm text-gray-700 dark:text-gray-200">
              ستون
              <select v-model="draft.column" class="glass mt-1 block w-full rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white">
                <option v-for="col in COLUMNS" :key="col.key" :value="col.key">{{ col.label }}</option>
              </select>
            </label>
            <label class="text-sm text-gray-700 dark:text-gray-200">
              مهلت
              <input v-model="draft.due_date" type="date" class="glass mt-1 block w-full rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white">
            </label>
            <label class="text-sm text-gray-700 dark:text-gray-200 sm:col-span-2">
              دوره‌ی مرتبط
              <select v-model="draft.course" class="glass mt-1 block w-full rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white">
                <option :value="null">— هیچ —</option>
                <option v-for="c in courses" :key="c.id" :value="c.id">{{ c.title }}</option>
              </select>
            </label>
          </div>
          <div>
            <p class="text-sm text-gray-700 dark:text-gray-200">رنگ</p>
            <div class="mt-1.5 flex gap-2">
              <button
                v-for="c in COLORS"
                :key="c.key"
                type="button"
                :title="c.label"
                :class="['h-7 w-7 rounded-full transition', c.class, draft.color === c.key ? 'ring-2 ring-primary-500 ring-offset-2 ring-offset-transparent' : 'hover:scale-110']"
                @click="draft.color = c.key"
              />
            </div>
          </div>
          <div class="flex items-center justify-between gap-3 pt-2">
            <button type="button" class="rounded-lg px-3 py-2 text-sm text-red-600 hover:bg-red-500/10" @click="deleteCard">حذف</button>
            <div class="flex gap-2">
              <button type="button" class="glass rounded-xl px-4 py-2 text-sm text-gray-700 dark:text-gray-200" @click="editing = null">انصراف</button>
              <button type="submit" :disabled="saving" class="rounded-xl bg-primary-600 px-5 py-2 text-sm font-semibold text-white hover:bg-primary-500 disabled:opacity-50">
                {{ saving ? 'در حال ذخیره...' : 'ذخیره' }}
              </button>
            </div>
          </div>
        </form>
      </div>
    </Teleport>
  </div>
</template>
