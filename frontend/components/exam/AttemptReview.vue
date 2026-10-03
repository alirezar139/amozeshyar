<script setup lang="ts">
// A submitted attempt, question by question: the student's answer next to
// the answer key, a verdict badge, and the guidance for wrong answers. With
// `grading`, essay answers get a score + feedback form for the teacher.
const props = defineProps<{ attempt: any; grading?: boolean }>()
const emit = defineEmits<{ graded: [attempt: any] }>()

const { request } = useApi()

function verdict(q: any) {
  if (q.score === null || q.score === undefined) return { label: 'در انتظار تصحیح استاد', class: 'bg-amber-500/15 text-amber-700 dark:text-amber-300', icon: '⏳' }
  if (q.is_correct) return { label: 'پاسخ درست', class: 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300', icon: '✓' }
  if (Number(q.score) > 0) return { label: 'نمره‌ی بخشی', class: 'bg-sky-500/15 text-sky-700 dark:text-sky-300', icon: '◐' }
  const empty = !q.answer.selected_choices.length && !q.answer.text.trim() && !q.answer.files.length
  return empty
    ? { label: 'بی‌پاسخ', class: 'bg-gray-500/15 text-gray-600 dark:text-gray-300', icon: '–' }
    : { label: 'پاسخ نادرست', class: 'bg-red-500/15 text-red-700 dark:text-red-300', icon: '✕' }
}

function choiceState(q: any, choiceId: number) {
  const picked = q.answer.selected_choices.includes(choiceId)
  const correct = q.correct_choices.includes(choiceId)
  if (picked && correct) return 'border-emerald-500 bg-emerald-500/10'
  if (picked) return 'border-red-500 bg-red-500/10'
  if (correct) return 'border-emerald-500/60 border-dashed'
  return 'border-black/10 dark:border-white/10'
}

// ---------- teacher grading ----------
const forms = reactive<Record<number, { score: string; feedback: string; saving: boolean; error: string }>>({})
watch(() => props.attempt, (attempt) => {
  for (const q of attempt?.questions ?? []) {
    if (q.kind === 'essay' && q.answer_id) {
      forms[q.answer_id] = { score: q.score === null ? '' : String(Number(q.score)), feedback: q.teacher_feedback ?? '', saving: false, error: '' }
    }
  }
}, { immediate: true })

async function grade(q: any) {
  const form = forms[q.answer_id]
  form.saving = true
  form.error = ''
  try {
    const updated = await request<any>(`/exam-attempts/manage/${props.attempt.id}/grade/`, {
      method: 'POST',
      body: { answer: q.answer_id, score: form.score, feedback: form.feedback },
    })
    emit('graded', updated)
  } catch (err) {
    form.error = getFirstErrorMessage(err, 'ثبت نمره ناموفق بود.')
  } finally {
    form.saving = false
  }
}
</script>

<template>
  <div class="space-y-4">
    <article v-for="q in attempt.questions" :key="q.id" class="glass rounded-2xl p-4 sm:p-5">
      <header class="flex flex-wrap items-center gap-2">
        <span class="flex h-7 w-7 items-center justify-center rounded-lg bg-gray-800 text-xs font-bold text-white dark:bg-gray-200 dark:text-gray-900">{{ toPersianDigits(q.number) }}</span>
        <span :class="['rounded-full px-2.5 py-0.5 text-xs font-semibold', verdict(q).class]">{{ verdict(q).icon }} {{ verdict(q).label }}</span>
        <span class="ms-auto text-sm font-bold text-gray-700 dark:text-gray-200">
          {{ q.score === null ? '؟' : toPersianDigits(Number(q.score)) }} / {{ toPersianDigits(Number(q.points)) }}
        </span>
      </header>

      <p class="mt-3 whitespace-pre-line leading-7 text-gray-900 dark:text-white" dir="auto">{{ q.text }}</p>
      <ExamMediaGallery :items="q.media" class="mt-3" />

      <!-- choices -->
      <ul v-if="q.choices.length" class="mt-3 space-y-1.5">
        <li v-for="c in q.choices" :key="c.id" :class="['flex items-center gap-2 rounded-xl border-2 px-3 py-2 text-sm', choiceState(q, c.id)]">
          <span class="text-gray-900 dark:text-white" dir="auto">{{ c.text }}</span>
          <span v-if="q.answer.selected_choices.includes(c.id)" class="ms-auto text-[11px] text-gray-500">پاسخ {{ grading ? 'دانشجو' : 'شما' }}</span>
          <span v-if="q.correct_choices.includes(c.id)" :class="['text-[11px] font-semibold text-emerald-600', q.answer.selected_choices.includes(c.id) ? '' : 'ms-auto']">پاسخ درست</span>
        </li>
      </ul>

      <!-- text / file answers -->
      <div v-else class="mt-3 grid gap-3 md:grid-cols-2">
        <div class="rounded-xl bg-black/[0.03] p-3 dark:bg-white/5">
          <p class="mb-1 text-xs font-semibold text-gray-500">پاسخ {{ grading ? 'دانشجو' : 'شما' }}</p>
          <p v-if="q.answer.text" class="whitespace-pre-line text-sm text-gray-900 dark:text-white" dir="auto">{{ q.answer.text }}</p>
          <p v-else-if="!q.answer.files.length" class="text-sm text-gray-400">(بی‌پاسخ)</p>
          <ExamMediaGallery :items="q.answer.files" class="mt-2" />
        </div>
        <div v-if="q.answer_key || q.answer_media.length" class="rounded-xl bg-emerald-500/[0.07] p-3">
          <p class="mb-1 text-xs font-semibold text-emerald-700 dark:text-emerald-300">{{ q.kind === 'short_answer' ? 'پاسخ‌های قابل‌قبول' : 'پاسخ نمونه' }}</p>
          <p class="whitespace-pre-line text-sm text-gray-900 dark:text-white" dir="auto">{{ q.answer_key }}</p>
        </div>
      </div>
      <ExamMediaGallery v-if="q.answer_media.length" :items="q.answer_media" class="mt-3" />

      <!-- guidance -->
      <div v-if="(q.score !== null && !q.is_correct && q.explanation) || q.teacher_feedback" class="mt-3 rounded-xl border-s-4 border-amber-500 bg-amber-500/[0.08] p-3">
        <p class="text-xs font-bold text-amber-700 dark:text-amber-300">💡 راهنمایی</p>
        <p v-if="q.teacher_feedback" class="mt-1 whitespace-pre-line text-sm text-gray-800 dark:text-gray-100" dir="auto">{{ q.teacher_feedback }}</p>
        <p v-if="!q.is_correct && q.explanation" class="mt-1 whitespace-pre-line text-sm text-gray-800 dark:text-gray-100" dir="auto">{{ q.explanation }}</p>
      </div>
      <details v-else-if="q.explanation" class="mt-3 text-sm text-gray-600 dark:text-gray-400">
        <summary class="cursor-pointer text-xs font-semibold">توضیح سوال</summary>
        <p class="mt-1 whitespace-pre-line" dir="auto">{{ q.explanation }}</p>
      </details>

      <!-- teacher grading -->
      <form
        v-if="grading && q.kind === 'essay' && q.answer_id && forms[q.answer_id]"
        class="mt-4 flex flex-wrap items-end gap-3 rounded-xl bg-primary-500/[0.06] p-3"
        @submit.prevent="grade(q)"
      >
        <label class="text-sm text-gray-700 dark:text-gray-200">
          نمره (از {{ toPersianDigits(Number(q.points)) }})
          <input v-model="forms[q.answer_id].score" type="number" min="0" :max="Number(q.points)" step="0.25" required class="glass mt-1 block w-24 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white">
        </label>
        <label class="min-w-[14rem] flex-1 text-sm text-gray-700 dark:text-gray-200">
          بازخورد و راهنمایی برای دانشجو
          <input v-model="forms[q.answer_id].feedback" class="glass mt-1 block w-full rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white" placeholder="اختیاری">
        </label>
        <button type="submit" :disabled="forms[q.answer_id].saving" class="rounded-xl bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-700 disabled:opacity-50">
          {{ q.score === null ? 'ثبت نمره' : 'به‌روزرسانی' }}
        </button>
        <p v-if="forms[q.answer_id].error" class="w-full text-xs text-red-600">{{ forms[q.answer_id].error }}</p>
      </form>
    </article>
  </div>
</template>
