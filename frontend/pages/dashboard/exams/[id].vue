<script setup lang="ts">
// Taking an exam, Quera-style: a sticky bar with the countdown and the time
// the exam ends, a question list showing each question's state, and the
// current question with its example box and answer area. Answers save as
// you go. When time runs out the page submits on its own (the server also
// refuses anything late); afterwards it shows the result sheet.
definePageMeta({ layout: 'dashboard', ssr: false })

const route = useRoute()
const { request } = useApi()
const { upload, uploadErrorMessage } = useUpload()
const { sync, remaining } = useExamClock()
const { formatGregorianDate } = useJalali()
const examId = Number(route.params.id)

const { data: exam, error: loadError } = await useAsyncData(`exam-${examId}`, () => request<any>(`/exams/${examId}/`))
useSeoMeta({ title: () => exam.value?.title ?? 'آزمون' })

const attempt = ref<any>(null)
const loadingAttempt = ref(false)
const pageError = ref('')

function setAttempt(data: any) {
  attempt.value = data
  sync(data.server_now)
}

async function loadAttempt(id: number) {
  loadingAttempt.value = true
  try {
    setAttempt(await request<any>(`/exam-attempts/${id}/`))
  } finally {
    loadingAttempt.value = false
  }
}
if (exam.value?.my_attempt) await loadAttempt(exam.value.my_attempt.id)

const starting = ref(false)
async function start() {
  starting.value = true
  pageError.value = ''
  try {
    setAttempt(await request<any>(`/exams/${examId}/start/`, { method: 'POST' }))
    current.value = 0
  } catch (err) {
    pageError.value = getFirstErrorMessage(err, 'شروع آزمون ناموفق بود.')
  } finally {
    starting.value = false
  }
}

const inProgress = computed(() => attempt.value?.status === 'in_progress')
const questions = computed<any[]>(() => attempt.value?.questions ?? [])
const current = ref(0)
const question = computed(() => questions.value[current.value])

// ---------- clocks ----------
const overallMs = computed(() => (inProgress.value ? remaining(attempt.value.deadline) : null))
const questionMs = (q: any) => (q?.deadline ? remaining(q.deadline) : null)
const serverLocked = reactive(new Set<number>())
const isLocked = (q: any) => serverLocked.has(q.id) || questionMs(q) === 0
const needsGate = (q: any) => q.time_limit_seconds && !q.answer.opened_at

const notice = ref<{ text: string; tone: 'warn' | 'info' } | null>(null)
let noticeTimer: ReturnType<typeof setTimeout> | null = null
function flash(text: string, tone: 'warn' | 'info' = 'info', ms = 5000) {
  notice.value = { text, tone }
  if (noticeTimer) clearTimeout(noticeTimer)
  noticeTimer = setTimeout(() => (notice.value = null), ms)
}

const warned = new Set<number>()
watch(overallMs, (ms) => {
  if (ms === null || !inProgress.value) return
  for (const mark of [5 * 60_000, 60_000]) {
    if (ms <= mark && ms > mark - 5000 && !warned.has(mark)) {
      warned.add(mark)
      flash(mark === 60_000 ? 'فقط یک دقیقه از آزمون باقی مانده است!' : '۵ دقیقه تا پایان آزمون باقی مانده است.', 'warn')
    }
  }
  if (ms === 0) submit(true)
})

// A timed question ran out while open: lock it and move on.
watch(() => questionMs(question.value), (ms, old) => {
  if (ms === 0 && old && inProgress.value) {
    flash(`زمان سوال ${toPersianDigits(question.value.number)} تمام شد.`, 'warn')
    const next = questions.value.findIndex((q, i) => i > current.value && !isLocked(q))
    if (next !== -1) setTimeout(() => (current.value = next), 1200)
  }
})

const opening = ref(false)
async function openQuestion(q: any) {
  opening.value = true
  try {
    const opened = await request<any>(`/exam-attempts/${attempt.value.id}/open/`, { method: 'POST', body: { question: q.id } })
    q.answer.opened_at = opened.opened_at
    q.deadline = opened.deadline
  } catch (err) {
    handleSaveError(q, err)
  } finally {
    opening.value = false
  }
}

// ---------- saving ----------
const saveState = reactive<Record<number, 'saving' | 'saved' | 'error'>>({})
const pendingSaves = new Map<number, Promise<void>>()
const textTimers = new Map<number, ReturnType<typeof setTimeout>>()

function handleSaveError(q: any, err: any) {
  const code = err?.data?.code
  if (code === 'question_closed') {
    serverLocked.add(q.id)
    flash(`زمان سوال ${toPersianDigits(q.number)} تمام شده و پاسخ جدید ثبت نشد.`, 'warn')
  } else if (code === 'attempt_closed') {
    loadAttempt(attempt.value.id)
  } else {
    saveState[q.id] = 'error'
    flash(getFirstErrorMessage(err, 'ذخیره‌ی پاسخ ناموفق بود؛ دوباره تلاش کنید.'), 'warn')
  }
}

function send(q: any, body: Record<string, any>) {
  saveState[q.id] = 'saving'
  const job = request(`/exam-attempts/${attempt.value.id}/answer/`, { method: 'POST', body: { question: q.id, ...body } })
    .then(() => { saveState[q.id] = 'saved' })
    .catch((err) => handleSaveError(q, err))
    .finally(() => pendingSaves.delete(q.id))
  pendingSaves.set(q.id, job)
  return job
}

function pick(q: any, choiceId: number) {
  if (isLocked(q)) return
  const selected: number[] = q.answer.selected_choices
  q.answer.selected_choices = q.kind === 'multiple_choice'
    ? (selected.includes(choiceId) ? selected.filter((id) => id !== choiceId) : [...selected, choiceId])
    : [choiceId]
  send(q, { choices: q.answer.selected_choices })
}

function typed(q: any) {
  saveState[q.id] = 'saving'
  clearTimeout(textTimers.get(q.id))
  textTimers.set(q.id, setTimeout(() => {
    textTimers.delete(q.id)
    send(q, { text: q.answer.text })
  }, 700))
}

async function flushSaves() {
  for (const [id, timer] of textTimers) {
    clearTimeout(timer)
    textTimers.delete(id)
    const q = questions.value.find((x) => x.id === id)
    if (q) send(q, { text: q.answer.text })
  }
  await Promise.allSettled([...pendingSaves.values()])
}

const uploadingFor = ref<number | null>(null)
async function addFile(q: any, file: File, duration: number | null) {
  uploadingFor.value = q.id
  try {
    const fields: Record<string, string | Blob> = { question: String(q.id), file }
    if (duration) fields.duration_seconds = String(duration)
    const item = await upload<any>(`/exam-attempts/${attempt.value.id}/files/`, fields).promise
    q.answer.files.push(item)
    saveState[q.id] = 'saved'
  } catch (err: any) {
    if (err?.data?.code) handleSaveError(q, err)
    else flash(uploadErrorMessage(err, 'آپلود فایل ناموفق بود.'), 'warn')
  } finally {
    uploadingFor.value = null
  }
}

async function removeFile(q: any, fileId: number) {
  try {
    await request(`/exam-attempts/${attempt.value.id}/files/${fileId}/`, { method: 'DELETE' })
    q.answer.files = q.answer.files.filter((f: any) => f.id !== fileId)
  } catch (err) {
    handleSaveError(q, err)
  }
}

const isAnswered = (q: any) => q.answer.selected_choices.length > 0 || q.answer.text.trim() !== '' || q.answer.files.length > 0
const unansweredCount = computed(() => questions.value.filter((q) => !isAnswered(q)).length)

// ---------- submit ----------
const confirmOpen = ref(false)
const submitting = ref(false)
async function submit(auto = false) {
  if (submitting.value || !inProgress.value) return
  submitting.value = true
  confirmOpen.value = false
  try {
    await flushSaves()
    setAttempt(await request<any>(`/exam-attempts/${attempt.value.id}/submit/`, { method: 'POST' }))
    if (import.meta.client) window.scrollTo({ top: 0, behavior: 'smooth' })
  } catch (err) {
    if (auto) await loadAttempt(attempt.value.id)
    else pageError.value = getFirstErrorMessage(err, 'ارسال پاسخ‌ها ناموفق بود؛ دوباره تلاش کنید.')
  } finally {
    submitting.value = false
  }
}

function beforeUnload(e: BeforeUnloadEvent) {
  if (inProgress.value && (pendingSaves.size || textTimers.size)) e.preventDefault()
}
onMounted(() => {
  window.addEventListener('beforeunload', beforeUnload)
  if (overallMs.value === 0) submit(true) // reopened right at the buzzer
})
onBeforeUnmount(() => window.removeEventListener('beforeunload', beforeUnload))

// ---------- result ----------
const resultHeadline = computed(() => {
  const a = attempt.value
  if (!a || a.status === 'in_progress') return null
  const timeout = a.submit_reason === 'timeout'
  return {
    icon: timeout ? '⏰' : '✅',
    title: timeout ? 'زمان آزمون تمام شد' : 'پاسخ‌هایتان ثبت شد',
    text: timeout
      ? 'آزمون بسته شد و پاسخ‌هایی که تا این لحظه داده بودید به‌طور خودکار ارسال و با پاسخ‌نامه مقایسه شد.'
      : 'آزمون را زودتر از موعد به پایان رساندید؛ پاسخ‌هایتان با پاسخ‌نامه مقایسه شد.',
  }
})
const correctCount = computed(() => questions.value.filter((q) => q.is_correct).length)
const when = (iso: string) => `${formatGregorianDate(new Date(iso))} ساعت ${clockTime(iso)}`

const KIND_LABELS: Record<string, string> = {
  single_choice: 'تک‌گزینه‌ای',
  multiple_choice: 'چندگزینه‌ای — همه‌ی گزینه‌های درست را انتخاب کنید',
  true_false: 'درست / نادرست',
  short_answer: 'پاسخ کوتاه',
  essay: 'تشریحی — می‌توانید بنویسید، عکس بفرستید یا صدایتان را ضبط کنید',
}
</script>

<template>
  <div class="mx-auto max-w-6xl">
    <NuxtLink to="/dashboard/exams" class="text-sm text-primary-600 hover:underline dark:text-primary-400">→ آزمون‌ها</NuxtLink>

    <div v-if="loadError || !exam" class="glass mt-6 rounded-2xl p-8 text-center text-gray-600 dark:text-gray-300">این آزمون پیدا نشد.</div>
    <div v-else-if="loadingAttempt && !attempt" class="mt-6 text-gray-500">در حال بارگذاری...</div>

    <!-- ===== before starting ===== -->
    <section v-else-if="!attempt" class="glass mx-auto mt-6 max-w-2xl rounded-3xl p-6 sm:p-8">
      <p class="text-sm text-primary-700 dark:text-primary-300">{{ exam.course_title }}</p>
      <h1 class="mt-1 text-2xl font-extrabold text-gray-900 dark:text-white">{{ exam.title }}</h1>
      <p v-if="exam.description" class="mt-4 whitespace-pre-line leading-7 text-gray-700 dark:text-gray-200">{{ exam.description }}</p>
      <dl class="mt-6 grid grid-cols-3 gap-3 text-center">
        <div class="rounded-2xl bg-black/[0.03] p-3 dark:bg-white/5">
          <dt class="text-xs text-gray-500">سوال</dt>
          <dd class="mt-1 text-xl font-extrabold text-gray-900 dark:text-white">{{ toPersianDigits(exam.question_count) }}</dd>
        </div>
        <div class="rounded-2xl bg-black/[0.03] p-3 dark:bg-white/5">
          <dt class="text-xs text-gray-500">زمان</dt>
          <dd class="mt-1 text-xl font-extrabold text-gray-900 dark:text-white">{{ exam.duration_minutes ? `${toPersianDigits(exam.duration_minutes)} دقیقه` : 'آزاد' }}</dd>
        </div>
        <div class="rounded-2xl bg-black/[0.03] p-3 dark:bg-white/5">
          <dt class="text-xs text-gray-500">حد قبولی</dt>
          <dd class="mt-1 text-xl font-extrabold text-gray-900 dark:text-white">{{ toPersianDigits(exam.pass_percent) }}٪</dd>
        </div>
      </dl>
      <ul class="mt-6 space-y-2 text-sm leading-6 text-gray-700 dark:text-gray-300">
        <li>⏱ زمان از لحظه‌ی شروع حساب می‌شود و با بستن صفحه متوقف نمی‌شود.</li>
        <li>💾 پاسخ‌ها همان لحظه ذخیره می‌شوند؛ اگر زمان تمام شود، خودکار ارسال می‌شوند.</li>
        <li>🔒 بعضی سوال‌ها زمان جداگانه دارند که با باز کردن همان سوال شروع می‌شود.</li>
        <li>📩 فقط یک بار می‌توانید در این آزمون شرکت کنید؛ نتیجه در پیام‌رسان هم برایتان ارسال می‌شود.</li>
        <li v-if="exam.available_until">🚪 آزمون {{ when(exam.available_until) }} بسته می‌شود.</li>
      </ul>
      <p v-if="pageError" class="mt-4 text-sm text-red-600">{{ pageError }}</p>
      <button
        v-if="exam.is_open"
        type="button"
        :disabled="starting"
        class="mt-6 w-full rounded-2xl bg-primary-600 py-3 text-base font-bold text-white shadow-lg shadow-primary-600/30 transition hover:bg-primary-700 disabled:opacity-50"
        @click="start"
      >
        {{ starting ? 'در حال آماده‌سازی…' : 'شروع آزمون' }}
      </button>
      <p v-else-if="exam.available_from && Date.parse(exam.available_from) > Date.now()" class="mt-6 rounded-2xl bg-violet-500/10 p-4 text-center text-sm font-semibold text-violet-700 dark:text-violet-300">
        این آزمون {{ when(exam.available_from) }} باز می‌شود.
      </p>
      <p v-else class="mt-6 rounded-2xl bg-gray-500/10 p-4 text-center text-sm text-gray-600 dark:text-gray-300">مهلت شرکت در این آزمون تمام شده است.</p>
    </section>

    <!-- ===== taking the exam ===== -->
    <template v-else-if="inProgress">
      <div class="glass sticky top-2 z-30 mt-3 flex flex-wrap items-center gap-3 rounded-2xl px-4 py-3 shadow-lg">
        <div class="min-w-0 flex-1">
          <p class="truncate text-xs text-gray-500">{{ attempt.exam.course_title }}</p>
          <h1 class="truncate font-bold text-gray-900 dark:text-white">{{ attempt.exam.title }}</h1>
        </div>
        <ExamCountdown :ms="overallMs" :ends-at="attempt.deadline" label="پایان آزمون" />
        <button
          type="button"
          :disabled="submitting"
          class="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-bold text-white hover:bg-emerald-700 disabled:opacity-50"
          @click="confirmOpen = true"
        >
          {{ submitting ? 'در حال ارسال…' : 'پایان و ارسال' }}
        </button>
      </div>

      <Transition enter-from-class="opacity-0 -translate-y-2" leave-to-class="opacity-0" enter-active-class="transition" leave-active-class="transition">
        <div
          v-if="notice"
          :class="['sticky top-24 z-30 mt-3 rounded-xl px-4 py-2.5 text-sm font-semibold shadow', notice.tone === 'warn' ? 'bg-amber-500 text-white' : 'bg-primary-600 text-white']"
          role="alert"
        >
          {{ notice.text }}
        </div>
      </Transition>
      <p v-if="pageError" class="mt-3 text-sm text-red-600">{{ pageError }}</p>

      <div class="mt-4 grid gap-4 lg:grid-cols-[15rem_1fr]">
        <!-- question list -->
        <nav class="glass h-fit rounded-2xl p-3 lg:sticky lg:top-24" aria-label="فهرست سوال‌ها">
          <p class="px-1 pb-2 text-xs font-semibold text-gray-500">
            {{ toPersianDigits(questions.length - unansweredCount) }} از {{ toPersianDigits(questions.length) }} پاسخ داده شده
          </p>
          <ol class="grid grid-cols-6 gap-1.5 lg:grid-cols-1">
            <li v-for="(q, i) in questions" :key="q.id">
              <button
                type="button"
                :class="[
                  'flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-sm transition',
                  i === current ? 'bg-primary-600 text-white' : 'hover:bg-black/5 dark:hover:bg-white/10',
                ]"
                @click="current = i"
              >
                <span
                  :class="[
                    'flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-xs font-bold',
                    i === current ? 'bg-white/20'
                    : isLocked(q) ? 'bg-gray-400/30 text-gray-500'
                    : isAnswered(q) ? 'bg-emerald-500 text-white'
                    : 'bg-black/5 text-gray-700 dark:bg-white/10 dark:text-gray-200',
                  ]"
                >
                  {{ toPersianDigits(q.number) }}
                </span>
                <span class="hidden min-w-0 flex-1 truncate text-start lg:block">{{ q.text }}</span>
                <span v-if="isLocked(q)" class="hidden lg:inline" title="زمان این سوال تمام شده">🔒</span>
                <span v-else-if="q.time_limit_seconds" class="hidden lg:inline" title="زمان‌دار">⏱</span>
              </button>
            </li>
          </ol>
        </nav>

        <!-- current question -->
        <article v-if="question" :key="question.id" class="glass rounded-2xl p-5 sm:p-6">
          <header class="flex flex-wrap items-center gap-2 border-b border-black/5 pb-3 dark:border-white/10">
            <h2 class="text-lg font-extrabold text-gray-900 dark:text-white">سوال {{ toPersianDigits(question.number) }}</h2>
            <span class="rounded-full bg-black/5 px-2.5 py-0.5 text-xs text-gray-600 dark:bg-white/10 dark:text-gray-300">{{ toPersianDigits(Number(question.points)) }} نمره</span>
            <span class="text-xs text-gray-500">{{ KIND_LABELS[question.kind] }}</span>
            <div class="ms-auto flex items-center gap-2">
              <span v-if="saveState[question.id] === 'saving'" class="text-xs text-gray-500">در حال ذخیره…</span>
              <span v-else-if="saveState[question.id] === 'saved'" class="text-xs text-emerald-600">✓ ذخیره شد</span>
              <span v-else-if="saveState[question.id] === 'error'" class="text-xs text-red-600">ذخیره نشد</span>
              <ExamCountdown v-if="question.deadline && !isLocked(question)" :ms="questionMs(question)" size="sm" label="زمان این سوال" />
            </div>
          </header>

          <!-- timed question not opened yet -->
          <div v-if="needsGate(question)" class="py-10 text-center">
            <p class="text-4xl">⏱</p>
            <p class="mt-3 font-bold text-gray-900 dark:text-white">این سوال {{ formatCountdown(question.time_limit_seconds * 1000) }} زمان دارد.</p>
            <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">زمان آن از لحظه‌ی باز کردن شروع می‌شود و بعد از پایان، پاسخ قابل تغییر نیست.</p>
            <button type="button" :disabled="opening" class="mt-5 rounded-xl bg-primary-600 px-6 py-2.5 text-sm font-bold text-white hover:bg-primary-700 disabled:opacity-50" @click="openQuestion(question)">
              باز کردن سوال
            </button>
          </div>

          <template v-else>
            <div v-if="isLocked(question)" class="mt-4 rounded-xl bg-gray-500/10 px-4 py-2.5 text-sm text-gray-600 dark:text-gray-300">🔒 زمان این سوال تمام شده؛ پاسخ ثبت‌شده‌ی شما حفظ شده است.</div>

            <p class="mt-4 whitespace-pre-line text-base leading-8 text-gray-900 dark:text-white" dir="auto">{{ question.text }}</p>
            <ExamMediaGallery :items="question.media" class="mt-4" />

            <div v-if="question.example" class="mt-5 overflow-hidden rounded-xl border border-black/10 dark:border-white/10">
              <p class="border-b border-black/10 bg-black/[0.04] px-3 py-1.5 text-xs font-bold text-gray-600 dark:border-white/10 dark:bg-white/5 dark:text-gray-300">مثال</p>
              <pre class="whitespace-pre-wrap px-4 py-3 font-mono text-sm leading-7 text-gray-800 dark:text-gray-100" dir="auto">{{ question.example }}</pre>
            </div>

            <!-- answer area -->
            <div class="mt-6">
              <ul v-if="question.choices.length" class="space-y-2">
                <li v-for="(c, ci) in question.choices" :key="c.id">
                  <button
                    type="button"
                    :disabled="isLocked(question)"
                    :class="[
                      'flex w-full items-center gap-3 rounded-xl border-2 px-4 py-3 text-start transition disabled:cursor-not-allowed',
                      question.answer.selected_choices.includes(c.id)
                        ? 'border-primary-500 bg-primary-500/10'
                        : 'border-black/10 hover:border-primary-300 dark:border-white/10',
                    ]"
                    @click="pick(question, c.id)"
                  >
                    <span
                      :class="[
                        'flex h-6 w-6 shrink-0 items-center justify-center border-2 text-xs font-bold',
                        question.kind === 'multiple_choice' ? 'rounded-md' : 'rounded-full',
                        question.answer.selected_choices.includes(c.id) ? 'border-primary-600 bg-primary-600 text-white' : 'border-gray-300 text-gray-500 dark:border-gray-600',
                      ]"
                    >
                      {{ question.answer.selected_choices.includes(c.id) ? '✓' : toPersianDigits(ci + 1) }}
                    </span>
                    <span class="text-gray-900 dark:text-white" dir="auto">{{ c.text }}</span>
                  </button>
                </li>
              </ul>

              <input
                v-else-if="question.kind === 'short_answer'"
                v-model="question.answer.text"
                :disabled="isLocked(question)"
                class="glass w-full rounded-xl px-4 py-3 text-base text-gray-900 outline-none focus:ring-2 focus:ring-primary-500/40 disabled:opacity-60 dark:text-white"
                placeholder="پاسخ خود را بنویسید…"
                dir="auto"
                @input="typed(question)"
              >

              <div v-else class="space-y-3">
                <textarea
                  v-model="question.answer.text"
                  :disabled="isLocked(question)"
                  rows="6"
                  class="glass w-full resize-y rounded-xl px-4 py-3 text-sm leading-7 text-gray-900 outline-none focus:ring-2 focus:ring-primary-500/40 disabled:opacity-60 dark:text-white"
                  placeholder="پاسخ خود را بنویسید…"
                  dir="auto"
                  @input="typed(question)"
                />
                <ExamMediaGallery :items="question.answer.files" :removable="!isLocked(question)" @remove="(id) => removeFile(question, id)" />
                <ExamMediaPicker
                  v-if="question.answer.files.length < 5"
                  :disabled="isLocked(question)"
                  :busy="uploadingFor === question.id"
                  @pick="(f, d) => addFile(question, f, d)"
                />
              </div>
            </div>
          </template>

          <footer class="mt-8 flex items-center justify-between border-t border-black/5 pt-4 dark:border-white/10">
            <button type="button" :disabled="current === 0" class="rounded-xl px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-black/5 disabled:opacity-30 dark:text-gray-200 dark:hover:bg-white/10" @click="current--">→ سوال قبلی</button>
            <button v-if="current < questions.length - 1" type="button" class="rounded-xl bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-700" @click="current++">سوال بعدی ←</button>
            <button v-else type="button" class="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700" @click="confirmOpen = true">پایان و ارسال</button>
          </footer>
        </article>
      </div>

      <!-- confirm early submit -->
      <Teleport to="body">
        <div v-if="confirmOpen" class="fixed inset-0 z-[70] flex items-center justify-center bg-black/40 p-4 backdrop-blur-sm" @click.self="confirmOpen = false">
          <div class="glass w-full max-w-md rounded-2xl p-6 text-center">
            <p class="text-3xl">📝</p>
            <h2 class="mt-2 text-lg font-bold text-gray-900 dark:text-white">آزمون را تمام می‌کنید؟</h2>
            <p v-if="unansweredCount" class="mt-2 text-sm font-semibold text-amber-600">{{ toPersianDigits(unansweredCount) }} سوال هنوز بی‌پاسخ است.</p>
            <p class="mt-2 text-sm text-gray-600 dark:text-gray-400">بعد از ارسال، پاسخ‌ها قابل تغییر نیستند و بلافاصله با پاسخ‌نامه مقایسه می‌شوند.</p>
            <div class="mt-5 flex gap-3">
              <button type="button" class="flex-1 rounded-xl border border-black/10 py-2.5 text-sm font-semibold text-gray-700 dark:border-white/10 dark:text-gray-200" @click="confirmOpen = false">ادامه‌ی آزمون</button>
              <button type="button" class="flex-1 rounded-xl bg-emerald-600 py-2.5 text-sm font-bold text-white hover:bg-emerald-700" @click="submit()">ارسال پاسخ‌ها</button>
            </div>
          </div>
        </div>
      </Teleport>
    </template>

    <!-- ===== result ===== -->
    <template v-else-if="resultHeadline">
      <section class="glass mt-4 overflow-hidden rounded-3xl">
        <div :class="['p-6 sm:p-8', attempt.submit_reason === 'timeout' ? 'bg-amber-500/10' : 'bg-emerald-500/10']">
          <p class="text-4xl">{{ resultHeadline.icon }}</p>
          <h1 class="mt-2 text-2xl font-extrabold text-gray-900 dark:text-white">{{ resultHeadline.title }}</h1>
          <p class="mt-1 text-sm leading-6 text-gray-700 dark:text-gray-300">{{ resultHeadline.text }}</p>
        </div>
        <div class="flex flex-wrap items-center gap-6 p-6 sm:p-8">
          <div class="text-center">
            <p :class="['text-5xl font-black', attempt.status !== 'graded' ? 'text-gray-400' : attempt.passed ? 'text-emerald-600' : 'text-red-600']">
              {{ toPersianDigits(attempt.percent) }}٪
            </p>
            <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">{{ toPersianDigits(Number(attempt.score)) }} از {{ toPersianDigits(Number(attempt.max_score)) }} نمره</p>
          </div>
          <div class="min-w-0 flex-1 space-y-2">
            <p v-if="attempt.status === 'graded'" class="text-lg font-bold text-gray-900 dark:text-white">{{ attempt.verdict }}</p>
            <p v-else class="rounded-xl bg-amber-500/10 px-3 py-2 text-sm font-semibold text-amber-700 dark:text-amber-300">
              ⏳ بخشی از پاسخ‌ها (تشریحی/صوتی/تصویری) را استاد تصحیح می‌کند؛ نمره‌ی نهایی بعد از آن کامل می‌شود.
            </p>
            <p class="text-sm text-gray-600 dark:text-gray-400">
              {{ toPersianDigits(correctCount) }} پاسخ درست از {{ toPersianDigits(questions.length) }} سوال · حد قبولی {{ toPersianDigits(attempt.exam.pass_percent) }}٪
            </p>
            <NuxtLink v-if="attempt.exam.notify_by_message" to="/dashboard/messages" class="inline-block text-sm font-semibold text-primary-600 hover:underline dark:text-primary-400">
              🤖 خلاصه‌ی نتیجه و نکته‌های مرور در پیام‌رسان ←
            </NuxtLink>
          </div>
        </div>
      </section>

      <h2 class="mt-8 text-lg font-bold text-gray-900 dark:text-white">کارنامه و پاسخ‌نامه</h2>
      <ExamAttemptReview :attempt="attempt" class="mt-4" />
    </template>
  </div>
</template>
