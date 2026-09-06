<script setup lang="ts">
const { isOpen, close, startTour, stepsForRoute } = useGuide()
const authStore = useAuthStore()

const role = computed(() => authStore.user?.role ?? 'guest')

const FAQS: Record<string, { q: string; a: string }[]> = {
  guest: [
    { q: 'چطور ثبت‌نام کنم؟', a: 'از دکمه‌ی «ثبت‌نام» در هدر یا فوتر، فرم پاپ‌آپ باز می‌شود؛ نوع حساب (دانشجو یا مدرس) را انتخاب کنید.' },
    { q: 'قبل از خرید می‌توانم دوره را ببینم؟', a: 'بله، هر دوره یک پیش‌نمایش رایگان دارد که بدون نیاز به خرید قابل تماشاست.' },
    { q: 'پرداخت از چه طریقی انجام می‌شود؟', a: 'از طریق درگاه زرین‌پال، به‌صورت امن.' },
  ],
  student: [
    { q: 'چطور به دوره‌ی خریداری‌شده دسترسی داشته باشم؟', a: 'از «داشبورد → دوره‌های من» به کل محتوای دوره دسترسی دارید.' },
    { q: 'ادامه‌ی یادگیری یعنی چه؟', a: 'محل دقیق توقف هر ویدیو ذخیره می‌شود؛ با دکمه‌ی «ادامه‌ی یادگیری» در داشبورد به همان‌جا برمی‌گردید.' },
    { q: 'کلاس‌های زنده را از کجا ببینم؟', a: 'از «تقویم کلاس‌ها» در داشبورد، زمان تمام جلسات زنده‌ی دوره‌های خریداری‌شده‌تان را می‌بینید.' },
  ],
  instructor: [
    { q: 'چطور دوره‌ی جدید بسازم؟', a: 'از «پنل مدرس → دوره‌ی جدید»؛ دوره‌ی ساخته‌شده تا زمان تایید ادمین منتشر نمی‌شود.' },
    { q: 'چطور ویدیوی هر جلسه را آپلود کنم؟', a: 'از صفحه‌ی «مدیریت سرفصل‌ها و ویدیو»ی همان دوره؛ پردازش و ساخت پیش‌نمایش خودکار انجام می‌شود.' },
    { q: 'چطور کلاس زنده زمان‌بندی کنم؟', a: 'در همان صفحه‌ی مدیریت سرفصل‌ها، بخش «زمان‌بندی کلاس‌های زنده» را پر کنید.' },
  ],
  admin: [
    { q: 'چطور یک دوره را تایید یا رد کنم؟', a: 'از «تخته‌ی دوره‌ها» کارت را به ستون موردنظر بکشید، یا از «تایید دوره‌ها» به‌صورت فهرستی.' },
    { q: 'چطور نقش یک کاربر را عوض کنم؟', a: 'از «مدیریت دسترسی کاربران»، نقش یا وضعیت فعال‌بودن هر کاربر را تغییر دهید (به‌جز حساب خودتان).' },
    { q: 'رزومه‌ی مدرس را کجا می‌بینم؟', a: 'روی کارت مدرس یا دوره در صف تایید، لینک «مشاهده رزومه» وجود دارد.' },
  ],
}

const openFaqIndex = ref<number | null>(null)
function toggleFaq(i: number) {
  openFaqIndex.value = openFaqIndex.value === i ? null : i
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="isOpen" class="fixed inset-0 z-[90] flex items-end justify-start p-4 sm:items-center" @click.self="close">
        <div class="glass w-full max-w-sm rounded-2xl p-5">
          <div class="flex items-center justify-between">
            <h2 class="font-bold text-gray-900 dark:text-white">راهنمای آموزش‌یار</h2>
            <button aria-label="بستن" class="text-gray-500 hover:text-gray-800 dark:hover:text-white" @click="close">✕</button>
          </div>

          <button
            v-if="stepsForRoute.length"
            type="button"
            class="mt-4 flex w-full items-center justify-between rounded-lg bg-primary-600 px-4 py-3 text-sm font-semibold text-white hover:bg-primary-500"
            @click="startTour"
          >
            شروع تور این صفحه
            <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M14 5l7 7m0 0l-7 7m7-7H3" /></svg>
          </button>
          <p v-else class="mt-4 rounded-lg bg-white/40 px-4 py-3 text-xs text-gray-500 dark:bg-white/5 dark:text-gray-400">
            برای این صفحه تور مرحله‌به‌مرحله تعریف نشده — سوالات پرتکرار زیر رو ببینید.
          </p>

          <div class="mt-4 max-h-72 space-y-2 overflow-y-auto">
            <div v-for="(item, i) in FAQS[role]" :key="i" class="glass rounded-lg">
              <button
                type="button"
                class="flex w-full items-center justify-between px-4 py-3 text-start text-sm font-medium text-gray-800 dark:text-gray-100"
                @click="toggleFaq(i)"
              >
                {{ item.q }}
                <span class="text-gray-400">{{ openFaqIndex === i ? '−' : '+' }}</span>
              </button>
              <p v-if="openFaqIndex === i" class="px-4 pb-3 text-sm text-gray-600 dark:text-gray-300">{{ item.a }}</p>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.15s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
