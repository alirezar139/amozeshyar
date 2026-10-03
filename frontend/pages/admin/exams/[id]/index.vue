<script setup lang="ts">
// Build one exam: its settings (time, opening window, pass mark, result
// message) and its questions, each edited and saved on its own.
import type { ExamQuestion } from '~/components/exam/QuestionEditor.vue'

definePageMeta({ layout: 'admin', ssr: false })

const route = useRoute()
const { request } = useApi()
const examId = Number(route.params.id)

const { data: exam, pending, error: loadError } = await useAsyncData(`admin-exam-${examId}`, () =>
  request<any>(`/exams/manage/${examId}/`),
)
useSeoMeta({ title: () => exam.value?.title ?? 'آزمون' })

// Questions keep a stable client key so unsaved ones survive re-renders.
let nextKey = 0
const questions = ref<(ExamQuestion & { _key: number })[]>([])
watch(exam, (e) => {
  if (e) questions.value = e.questions.map((q: ExamQuestion) => ({ ...q, _key: nextKey++ }))
}, { immediate: true })

// ---------- settings ----------
const toLocalInput = (iso: string | null) => {
  if (!iso) return ''
  const d = new Date(iso)
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
}
const settings = reactive({
  title: '', description: '', duration_minutes: '' as number | '', available_from: '', available_until: '',
  pass_percent: 60, notify_by_message: true,
})
watch(exam, (e) => {
  if (!e) return
  Object.assign(settings, {
    title: e.title, description: e.description, duration_minutes: e.duration_minutes ?? '',
    available_from: toLocalInput(e.available_from), available_until: toLocalInput(e.available_until),
    pass_percent: e.pass_percent, notify_by_message: e.notify_by_message,
  })
}, { immediate: true })

const savingSettings = ref(false)
const settingsMessage = ref('')
const settingsError = ref('')
const error = ref('')

async function patchExam(body: Record<string, any>) {
  const updated = await request<any>(`/exams/manage/${examId}/`, { method: 'PATCH', body })
  Object.assign(exam.value, updated)
}

async function saveSettings() {
  settingsError.value = ''
  settingsMessage.value = ''
  if (settings.available_from && settings.available_until && settings.available_until <= settings.available_from) {
    settingsError.value = 'زمان بسته شدن باید بعد از زمان باز شدن آزمون باشد.'
    return
  }
  savingSettings.value = true
  try {
    await patchExam({
      title: settings.title,
      description: settings.description,
      duration_minutes: settings.duration_minutes || null,
      available_from: settings.available_from ? new Date(settings.available_from).toISOString() : null,
      available_until: settings.available_until ? new Date(settings.available_until).toISOString() : null,
      pass_percent: settings.pass_percent,
      notify_by_message: settings.notify_by_message,
    })
    settingsMessage.value = 'تنظیمات ذخیره شد.'
  } catch (err) {
    settingsError.value = getFirstErrorMessage(err, 'ذخیره‌ی تنظیمات ناموفق بود.')
  } finally {
    savingSettings.value = false
  }
}

async function toggleStatus() {
  error.value = ''
  try {
    await patchExam({ status: exam.value.status === 'published' ? 'draft' : 'published' })
  } catch (err) {
    error.value = getFirstErrorMessage(err, 'تغییر وضعیت ناموفق بود.')
  }
}

// ---------- questions ----------
function addQuestion(kind: ExamQuestion['kind']) {
  questions.value.push({
    _key: nextKey++, exam: examId, kind, text: '', example: '', answer_key: '', explanation: '', points: 1,
    time_limit_seconds: null, media: [],
    choices: kind === 'true_false'
      ? [{ text: 'درست', is_correct: true }, { text: 'نادرست', is_correct: false }]
      : [{ text: '', is_correct: true }, { text: '', is_correct: false }],
  })
}

function onSaved(index: number, saved: ExamQuestion) {
  questions.value[index] = { ...saved, _key: questions.value[index]._key }
}

async function move(index: number, direction: 'up' | 'down') {
  const question = questions.value[index]
  const reordered = await request<ExamQuestion[]>(`/exam-questions/${question.id}/move/`, { method: 'POST', body: { direction } })
  const keys = new Map(questions.value.filter((q) => q.id).map((q) => [q.id, q._key]))
  const unsaved = questions.value.filter((q) => !q.id)
  questions.value = [...reordered.map((q) => ({ ...q, _key: keys.get(q.id) ?? nextKey++ })), ...unsaved]
}

const savedCount = computed(() => questions.value.filter((q) => q.id).length)
const totalPoints = computed(() => questions.value.filter((q) => q.id).reduce((sum, q) => sum + Number(q.points || 0), 0))
const timedCount = computed(() => questions.value.filter((q) => q.time_limit_seconds).length)

const ADD_BUTTONS = [
  { kind: 'single_choice', label: 'تک‌گزینه‌ای' },
  { kind: 'multiple_choice', label: 'چندگزینه‌ای' },
  { kind: 'true_false', label: 'درست/نادرست' },
  { kind: 'short_answer', label: 'پاسخ کوتاه' },
  { kind: 'essay', label: 'تشریحی / صوت / عکس' },
] as const
</script>

<template>
  <div class="mx-auto max-w-5xl">
    <NuxtLink to="/admin/exams" class="text-sm text-primary-600 hover:underline dark:text-primary-400">→ آزمون‌ها</NuxtLink>

    <div v-if="pending && !exam" class="mt-6 text-gray-500">در حال بارگذاری...</div>
    <div v-else-if="loadError || !exam" class="glass mt-6 rounded-2xl p-8 text-center text-gray-600 dark:text-gray-300">این آزمون پیدا نشد.</div>

    <template v-else>
      <div class="mt-3 flex flex-wrap items-center justify-between gap-3">
        <div>
          <p class="text-xs text-primary-700 dark:text-primary-300">{{ exam.course_title }}</p>
          <h1 class="text-2xl font-extrabold text-gray-900 dark:text-white">{{ exam.title }}</h1>
          <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
            {{ toPersianDigits(savedCount) }} سوال · {{ toPersianDigits(totalPoints) }} نمره
            <template v-if="timedCount"> · {{ toPersianDigits(timedCount) }} سوال زمان‌دار</template>
          </p>
        </div>
        <div class="flex items-center gap-2">
          <NuxtLink :to="`/admin/exams/${examId}/results`" class="rounded-xl border border-black/10 px-4 py-2 text-sm font-semibold text-gray-700 hover:border-primary-400 dark:border-white/10 dark:text-gray-200">نتایج</NuxtLink>
          <button
            type="button"
            :disabled="exam.status !== 'published' && !savedCount"
            :title="exam.status !== 'published' && !savedCount ? 'اول حداقل یک سوال اضافه و ذخیره کنید' : undefined"
            :class="[
              'rounded-xl px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-40',
              exam.status === 'published' ? 'bg-gray-500 hover:bg-gray-600' : 'bg-emerald-600 hover:bg-emerald-700',
            ]"
            @click="toggleStatus"
          >
            {{ exam.status === 'published' ? 'لغو انتشار' : 'انتشار آزمون' }}
          </button>
        </div>
      </div>
      <p v-if="error" class="mt-3 text-sm text-red-600">{{ error }}</p>

      <!-- settings -->
      <form class="glass mt-6 rounded-2xl p-5" @submit.prevent="saveSettings">
        <h2 class="font-bold text-gray-900 dark:text-white">تنظیمات آزمون</h2>
        <div class="mt-4 grid gap-4 sm:grid-cols-2">
          <label class="text-sm text-gray-700 dark:text-gray-200 sm:col-span-2">
            عنوان
            <input v-model="settings.title" required class="glass mt-1 block w-full rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white">
          </label>
          <label class="text-sm text-gray-700 dark:text-gray-200 sm:col-span-2">
            توضیحات و قوانین آزمون <span class="text-xs text-gray-500">(قبل از شروع به دانشجو نشان داده می‌شود)</span>
            <textarea v-model="settings.description" rows="3" class="glass mt-1 block w-full rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white" />
          </label>
          <label class="text-sm text-gray-700 dark:text-gray-200">
            زمان کل آزمون (دقیقه) <span class="text-xs text-gray-500">خالی = بدون محدودیت</span>
            <input v-model="settings.duration_minutes" type="number" min="1" class="glass mt-1 block w-full rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white">
          </label>
          <label class="text-sm text-gray-700 dark:text-gray-200">
            حد قبولی (درصد)
            <input v-model.number="settings.pass_percent" type="number" min="0" max="100" class="glass mt-1 block w-full rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white">
          </label>
          <label class="text-sm text-gray-700 dark:text-gray-200">
            باز شدن آزمون <span class="text-xs text-gray-500">(اختیاری)</span>
            <input v-model="settings.available_from" type="datetime-local" class="glass mt-1 block w-full rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white">
          </label>
          <label class="text-sm text-gray-700 dark:text-gray-200">
            بسته شدن آزمون <span class="text-xs text-gray-500">(بعد از آن، آزمون‌های در حال برگزاری هم بسته می‌شوند)</span>
            <input v-model="settings.available_until" type="datetime-local" class="glass mt-1 block w-full rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white">
          </label>
          <label class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-200 sm:col-span-2">
            <input v-model="settings.notify_by_message" type="checkbox" class="h-4 w-4 rounded">
            بعد از تصحیح، «دستیار آزمون» نمره و نکته‌های مرور را در پیام‌رسان برای دانشجو بفرستد
          </label>
        </div>
        <div class="mt-4 flex items-center justify-end gap-3">
          <span v-if="settingsError" class="text-sm text-red-600">{{ settingsError }}</span>
          <span v-else-if="settingsMessage" class="text-sm text-emerald-600">{{ settingsMessage }}</span>
          <button type="submit" :disabled="savingSettings" class="rounded-xl bg-primary-600 px-5 py-2 text-sm font-semibold text-white hover:bg-primary-700 disabled:opacity-50">
            {{ savingSettings ? 'در حال ذخیره…' : 'ذخیره‌ی تنظیمات' }}
          </button>
        </div>
      </form>

      <!-- questions -->
      <div class="mt-8 space-y-5">
        <ExamQuestionEditor
          v-for="(q, i) in questions"
          :key="q._key"
          :question="q"
          :number="i + 1"
          :first="i === 0"
          :last="i === questions.length - 1"
          @saved="(saved) => onSaved(i, saved)"
          @deleted="questions.splice(i, 1)"
          @move="(d) => move(i, d)"
        />
      </div>

      <div class="glass mt-5 rounded-2xl border-2 border-dashed border-black/10 p-5 text-center dark:border-white/10">
        <p class="text-sm font-semibold text-gray-700 dark:text-gray-200">افزودن سوال</p>
        <div class="mt-3 flex flex-wrap justify-center gap-2">
          <button
            v-for="b in ADD_BUTTONS"
            :key="b.kind"
            type="button"
            class="rounded-xl border border-black/10 bg-white/50 px-4 py-2 text-sm text-gray-700 transition hover:border-primary-400 hover:text-primary-700 dark:border-white/10 dark:bg-white/5 dark:text-gray-200"
            @click="addQuestion(b.kind)"
          >
            + {{ b.label }}
          </button>
        </div>
      </div>
    </template>
  </div>
</template>
