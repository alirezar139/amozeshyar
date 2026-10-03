<script setup lang="ts">
// One question of an exam in the teacher's builder: question text, an
// example (shown like a sample box), image/audio for the question, the
// answer key (choices / accepted answers / model answer) with its own
// image/audio, guidance for wrong answers, points and an optional timer.
export interface ExamMedia { id: number; kind: 'image' | 'audio'; url: string | null; name: string; role: 'prompt' | 'answer' }
export interface ExamChoice { id?: number; text: string; is_correct: boolean }
export interface ExamQuestion {
  id?: number
  exam: number
  kind: 'single_choice' | 'multiple_choice' | 'true_false' | 'short_answer' | 'essay'
  text: string
  example: string
  answer_key: string
  explanation: string
  points: string | number
  time_limit_seconds: number | null
  choices: ExamChoice[]
  media: ExamMedia[]
}

const props = defineProps<{ question: ExamQuestion; number: number; first?: boolean; last?: boolean }>()
const emit = defineEmits<{ saved: [q: ExamQuestion]; deleted: []; move: [direction: 'up' | 'down'] }>()

const { request } = useApi()
const { upload, uploadErrorMessage } = useUpload()

const KINDS = [
  { key: 'single_choice', label: 'تک‌گزینه‌ای' },
  { key: 'multiple_choice', label: 'چندگزینه‌ای (چند جواب درست)' },
  { key: 'true_false', label: 'درست / نادرست' },
  { key: 'short_answer', label: 'پاسخ کوتاه' },
  { key: 'essay', label: 'تشریحی / صوت / عکس' },
] as const

// A plain deep copy: structuredClone can't copy the reactive arrays nested in props.
const clone = <T,>(value: T): T => JSON.parse(JSON.stringify(value))
const draft = reactive<ExamQuestion>(clone(props.question))
const savedSnapshot = ref(JSON.stringify(props.question))
const dirty = computed(() => JSON.stringify(draft) !== savedSnapshot.value)
const saving = ref(false)
const error = ref('')
const isChoice = computed(() => ['single_choice', 'multiple_choice', 'true_false'].includes(draft.kind))

watch(() => draft.kind, (kind, old) => {
  if (kind === 'true_false') {
    const correctIsTrue = draft.choices[0]?.is_correct ?? true
    draft.choices = [{ text: 'درست', is_correct: correctIsTrue }, { text: 'نادرست', is_correct: !correctIsTrue }]
  } else if (old === 'true_false' || (isChoice.value && draft.choices.length < 2)) {
    draft.choices = [{ text: '', is_correct: true }, { text: '', is_correct: false }]
  }
  if (kind === 'single_choice' && draft.choices.filter((c) => c.is_correct).length > 1) {
    draft.choices.forEach((c, i) => (c.is_correct = i === draft.choices.findIndex((x) => x.is_correct)))
  }
})

function markCorrect(index: number) {
  if (draft.kind === 'multiple_choice') draft.choices[index].is_correct = !draft.choices[index].is_correct
  else draft.choices.forEach((c, i) => (c.is_correct = i === index))
}

// Timer edited as minutes + seconds, stored as seconds.
const timerMinutes = computed({
  get: () => (draft.time_limit_seconds ? Math.floor(draft.time_limit_seconds / 60) : ''),
  set: (v) => setTimer(Number(v) || 0, draft.time_limit_seconds ? draft.time_limit_seconds % 60 : 0),
})
const timerSeconds = computed({
  get: () => (draft.time_limit_seconds ? draft.time_limit_seconds % 60 : ''),
  set: (v) => setTimer(draft.time_limit_seconds ? Math.floor(draft.time_limit_seconds / 60) : 0, Number(v) || 0),
})
function setTimer(minutes: number, seconds: number) {
  const total = Math.max(0, minutes * 60 + Math.min(59, seconds))
  draft.time_limit_seconds = total || null
}

async function save() {
  saving.value = true
  error.value = ''
  try {
    const body = {
      exam: draft.exam,
      kind: draft.kind,
      text: draft.text,
      example: draft.example,
      answer_key: draft.answer_key,
      explanation: draft.explanation,
      points: draft.points,
      time_limit_seconds: draft.time_limit_seconds,
      choices: isChoice.value ? draft.choices : [],
    }
    const saved = draft.id
      ? await request<ExamQuestion>(`/exam-questions/${draft.id}/`, { method: 'PATCH', body })
      : await request<ExamQuestion>('/exam-questions/', { method: 'POST', body })
    Object.assign(draft, clone(saved))
    savedSnapshot.value = JSON.stringify(draft)
    emit('saved', saved)
  } catch (err) {
    error.value = getFirstErrorMessage(err, 'ذخیره‌ی سوال ناموفق بود.')
  } finally {
    saving.value = false
  }
}

async function remove() {
  if (draft.id && !confirm(`سوال ${props.number} حذف شود؟`)) return
  if (draft.id) await request(`/exam-questions/${draft.id}/`, { method: 'DELETE' })
  emit('deleted')
}

// ---------- media ----------
const uploadingRole = ref<'prompt' | 'answer' | null>(null)
const mediaOf = (role: 'prompt' | 'answer') => draft.media.filter((m) => m.role === role)

async function addMedia(role: 'prompt' | 'answer', file: File) {
  if (!draft.id) return
  uploadingRole.value = role
  error.value = ''
  try {
    const item = await upload<ExamMedia>('/exam-question-media/', { question: String(draft.id), role, file }).promise
    draft.media.push(item)
    savedSnapshot.value = JSON.stringify({ ...JSON.parse(savedSnapshot.value), media: draft.media })
  } catch (err) {
    error.value = uploadErrorMessage(err, 'آپلود فایل ناموفق بود.')
  } finally {
    uploadingRole.value = null
  }
}

async function removeMedia(id: number) {
  await request(`/exam-question-media/${id}/`, { method: 'DELETE' })
  draft.media = draft.media.filter((m) => m.id !== id)
  savedSnapshot.value = JSON.stringify({ ...JSON.parse(savedSnapshot.value), media: draft.media })
}

const FIELD = 'glass w-full rounded-xl px-3 py-2 text-sm text-gray-900 outline-none focus:ring-2 focus:ring-primary-500/40 dark:text-white'
const BOX = 'rounded-xl border border-black/5 bg-white/30 p-3 dark:border-white/10 dark:bg-white/[0.03]'
</script>

<template>
  <article class="glass rounded-2xl p-4 sm:p-5">
    <header class="flex flex-wrap items-center gap-2">
      <span class="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-600 text-sm font-bold text-white">{{ toPersianDigits(number) }}</span>
      <select v-model="draft.kind" class="glass rounded-lg px-3 py-1.5 text-sm text-gray-900 dark:text-white">
        <option v-for="k in KINDS" :key="k.key" :value="k.key">{{ k.label }}</option>
      </select>
      <span v-if="dirty" class="rounded-md bg-amber-500/15 px-2 py-0.5 text-[11px] text-amber-700 dark:text-amber-300">ذخیره نشده</span>
      <div class="ms-auto flex items-center gap-1">
        <button type="button" class="rounded-lg p-1.5 text-gray-500 hover:bg-black/5 disabled:opacity-30 dark:hover:bg-white/10" :disabled="first || !draft.id" title="بالا" @click="emit('move', 'up')">▲</button>
        <button type="button" class="rounded-lg p-1.5 text-gray-500 hover:bg-black/5 disabled:opacity-30 dark:hover:bg-white/10" :disabled="last || !draft.id" title="پایین" @click="emit('move', 'down')">▼</button>
        <button type="button" class="rounded-lg px-2 py-1 text-xs text-red-600 hover:bg-red-500/10" @click="remove">حذف</button>
      </div>
    </header>

    <div class="mt-4 grid gap-4 lg:grid-cols-2">
      <!-- box 1: question -->
      <section :class="BOX">
        <h3 class="mb-2 text-sm font-bold text-gray-800 dark:text-gray-100">صورت سوال</h3>
        <textarea v-model="draft.text" rows="4" :class="FIELD" placeholder="متن سوال را بنویسید…" dir="auto" />
      </section>

      <!-- box 2: example -->
      <section :class="BOX">
        <h3 class="mb-2 text-sm font-bold text-gray-800 dark:text-gray-100">مثال <span class="font-normal text-gray-500">(اختیاری)</span></h3>
        <textarea v-model="draft.example" rows="4" :class="[FIELD, 'font-mono']" placeholder="یک نمونه‌ی حل‌شده یا نمونه‌ی ورودی/خروجی…" dir="auto" />
      </section>

      <!-- box 3: question media -->
      <section :class="BOX">
        <h3 class="mb-2 text-sm font-bold text-gray-800 dark:text-gray-100">عکس و صوت سوال</h3>
        <template v-if="draft.id">
          <ExamMediaGallery :items="mediaOf('prompt')" removable class="mb-3" @remove="removeMedia" />
          <ExamMediaPicker :busy="uploadingRole === 'prompt'" @pick="(f) => addMedia('prompt', f)" />
        </template>
        <p v-else class="text-xs text-gray-500">برای افزودن عکس یا صوت، اول سوال را ذخیره کنید.</p>
      </section>

      <!-- box 4: answer key -->
      <section :class="BOX">
        <h3 class="mb-2 text-sm font-bold text-gray-800 dark:text-gray-100">پاسخ‌نامه</h3>
        <div v-if="isChoice" class="space-y-2">
          <p class="text-xs text-gray-500">
            {{ draft.kind === 'multiple_choice' ? 'روی همه‌ی گزینه‌های درست تیک بزنید.' : 'گزینه‌ی درست را انتخاب کنید.' }}
          </p>
          <div v-for="(choice, i) in draft.choices" :key="i" class="flex items-center gap-2">
            <button
              type="button"
              :class="[
                'flex h-7 w-7 shrink-0 items-center justify-center border-2 text-xs font-bold transition',
                draft.kind === 'multiple_choice' ? 'rounded-md' : 'rounded-full',
                choice.is_correct ? 'border-emerald-500 bg-emerald-500 text-white' : 'border-gray-300 text-transparent hover:border-emerald-400 dark:border-gray-600',
              ]"
              :aria-label="choice.is_correct ? 'گزینه‌ی درست' : 'علامت‌گذاری به‌عنوان درست'"
              @click="markCorrect(i)"
            >
              ✓
            </button>
            <input v-model="choice.text" :readonly="draft.kind === 'true_false'" :class="FIELD" :placeholder="`گزینه‌ی ${toPersianDigits(i + 1)}`" dir="auto">
            <button
              v-if="draft.kind !== 'true_false' && draft.choices.length > 2"
              type="button"
              class="shrink-0 rounded-lg px-2 text-gray-400 hover:text-red-600"
              aria-label="حذف گزینه"
              @click="draft.choices.splice(i, 1)"
            >
              ✕
            </button>
          </div>
          <button
            v-if="draft.kind !== 'true_false' && draft.choices.length < 8"
            type="button"
            class="text-xs font-semibold text-primary-600 hover:underline dark:text-primary-400"
            @click="draft.choices.push({ text: '', is_correct: false })"
          >
            + گزینه‌ی جدید
          </button>
        </div>
        <div v-else-if="draft.kind === 'short_answer'">
          <textarea v-model="draft.answer_key" rows="3" :class="FIELD" placeholder="هر پاسخ قابل‌قبول در یک خط" dir="auto" />
          <p class="mt-1 text-xs text-gray-500">پاسخ دانشجو با هر یک از این خط‌ها مقایسه می‌شود (ی/ي، ک/ك، اعداد فارسی و فاصله‌ها یکسان در نظر گرفته می‌شوند).</p>
        </div>
        <div v-else>
          <textarea v-model="draft.answer_key" rows="3" :class="FIELD" placeholder="پاسخ نمونه (بعد از تصحیح به دانشجو نشان داده می‌شود)" dir="auto" />
          <p class="mt-1 text-xs text-gray-500">دانشجو می‌تواند متن بنویسد، عکس بفرستد یا صدایش را ضبط کند؛ این سوال را شما تصحیح می‌کنید.</p>
        </div>
      </section>

      <!-- box 5: answer media -->
      <section :class="BOX">
        <h3 class="mb-2 text-sm font-bold text-gray-800 dark:text-gray-100">عکس و صوت پاسخ‌نامه <span class="font-normal text-gray-500">(بعد از آزمون)</span></h3>
        <template v-if="draft.id">
          <ExamMediaGallery :items="mediaOf('answer')" removable class="mb-3" @remove="removeMedia" />
          <ExamMediaPicker :busy="uploadingRole === 'answer'" @pick="(f) => addMedia('answer', f)" />
        </template>
        <p v-else class="text-xs text-gray-500">برای افزودن عکس یا صوت، اول سوال را ذخیره کنید.</p>
      </section>

      <!-- box 6: guidance -->
      <section :class="BOX">
        <h3 class="mb-2 text-sm font-bold text-gray-800 dark:text-gray-100">راهنمایی برای پاسخ نادرست</h3>
        <textarea v-model="draft.explanation" rows="3" :class="FIELD" placeholder="اگر دانشجو اشتباه کرد، چه نکته‌ای را مرور کند؟" dir="auto" />
      </section>
    </div>

    <footer class="mt-4 flex flex-wrap items-end gap-4">
      <label class="text-sm text-gray-700 dark:text-gray-200">
        نمره
        <input v-model="draft.points" type="number" min="0.25" step="0.25" class="glass mt-1 block w-24 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white">
      </label>
      <div class="text-sm text-gray-700 dark:text-gray-200">
        زمان این سوال <span class="text-xs text-gray-500">(خالی = بدون محدودیت)</span>
        <div class="mt-1 flex items-center gap-1.5">
          <input v-model="timerMinutes" type="number" min="0" class="glass w-20 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white" placeholder="دقیقه">
          <span class="text-gray-400">:</span>
          <input v-model="timerSeconds" type="number" min="0" max="59" class="glass w-20 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white" placeholder="ثانیه">
        </div>
      </div>
      <div class="ms-auto flex items-center gap-3">
        <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
        <button
          type="button"
          class="rounded-xl bg-primary-600 px-5 py-2 text-sm font-semibold text-white transition hover:bg-primary-700 disabled:opacity-50"
          :disabled="saving || !draft.text.trim() || (!dirty && !!draft.id)"
          @click="save"
        >
          {{ saving ? 'در حال ذخیره…' : draft.id ? 'ذخیره‌ی تغییرات' : 'ذخیره‌ی سوال' }}
        </button>
      </div>
    </footer>
  </article>
</template>
