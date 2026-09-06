export interface TourStep {
  selector: string
  title: string
  text: string
}

// One entry per route that has a guided tour defined. Pages without an
// entry just don't offer "شروع تور این صفحه" — the general FAQ in
// GuidePanel is always available regardless.
export const TOUR_STEPS: Record<string, TourStep[]> = {
  '/': [
    { selector: '[data-tour="hero-cta"]', title: 'مشاهده‌ی دوره‌ها', text: 'با این دکمه به فهرست کامل دوره‌های سایت می‌رسید.' },
    { selector: '[data-tour="categories"]', title: 'دسته‌بندی دوره‌ها', text: 'روی هر دسته کلیک کنید تا فقط دوره‌های همون موضوع رو ببینید.' },
    { selector: '[data-tour="featured-instructors"]', title: 'مدرس‌های ما', text: 'پروفایل کامل هر مدرس، امتیاز و شماره تماسش از همین‌جا در دسترسه.' },
    { selector: '[data-tour="header-login"]', title: 'ورود یا ثبت‌نام', text: 'برای خرید دوره یا تدریس، اول باید وارد حساب خودتون بشید.' },
  ],
  '/instructor-panel/courses': [
    { selector: '[data-tour="new-course"]', title: 'ساخت دوره‌ی جدید', text: 'دوره‌ی جدید از همین دکمه ساخته می‌شه و برای تایید به صف ادمین می‌ره.' },
    { selector: '[data-tour="manage-lessons-link"]', title: 'مدیریت سرفصل و ویدیو', text: 'از این لینک، ویدیوی هر جلسه رو آپلود و کلاس‌های زنده رو زمان‌بندی می‌کنید.' },
  ],
  '/admin/board': [
    { selector: '[data-tour="board-column-pending_review"]', title: 'در انتظار بررسی', text: 'دوره‌های تازه ارسال‌شده اینجا منتظر تصمیم شما می‌مونن.' },
    { selector: '[data-tour="board-card"]', title: 'کارت دوره', text: 'هر کارت رو بکشید و به ستون دیگه ببرید تا وضعیتش تغییر کنه — رد کردن یه دلیل می‌خواد.' },
  ],
  '/dashboard': [
    { selector: '[data-tour="continue-learning"]', title: 'ادامه‌ی یادگیری', text: 'دقیقاً از همون جایی که آخرین بار درس رو ول کردید، ادامه می‌دید.' },
  ],
}

export function useGuide() {
  const isOpen = useState('guide-open', () => false)
  const isTouring = useState('guide-touring', () => false)
  const stepIndex = useState('guide-step', () => 0)

  const route = useRoute()
  const stepsForRoute = computed(() => TOUR_STEPS[route.path] ?? [])

  function open() {
    isOpen.value = true
  }
  function close() {
    isOpen.value = false
  }
  function startTour() {
    if (!stepsForRoute.value.length) return
    stepIndex.value = 0
    isTouring.value = true
    isOpen.value = false
  }
  function endTour() {
    isTouring.value = false
  }
  function next() {
    if (stepIndex.value < stepsForRoute.value.length - 1) stepIndex.value++
    else endTour()
  }
  function prev() {
    if (stepIndex.value > 0) stepIndex.value--
  }

  return { isOpen, isTouring, stepIndex, stepsForRoute, open, close, startTour, endTour, next, prev }
}
