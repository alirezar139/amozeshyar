export interface TourStep {
  selector: string
  title: string
  text: string
}

// Keyed by Nuxt's auto-generated route *name* (e.g. "courses-slug",
// "admin-courses-id-lessons"), not the raw path — a path like
// `/courses/python-101` never matches a literal key, but its route name
// is always the same regardless of the dynamic param's value. Pages
// without an entry just don't offer "شروع تور این صفحه" — the general
// FAQ in GuidePanel is always available regardless.
export const TOUR_STEPS: Record<string, TourStep[]> = {
  index: [
    { selector: '[data-tour="header-login"]', title: 'ورود یا ثبت‌نام', text: 'برای خرید دوره یا تدریس، اول باید وارد حساب خودتون بشید — یه پاپ‌آپ سبک باز می‌شه، نه یه صفحه‌ی جدا.' },
    { selector: '[data-tour="hero-cta"]', title: 'مشاهده‌ی دوره‌ها', text: 'با این دکمه به فهرست کامل دوره‌های سایت می‌رسید.' },
    { selector: '[data-tour="categories"]', title: 'دسته‌بندی دوره‌ها', text: 'روی هر دسته کلیک کنید تا فقط دوره‌های همون موضوع رو ببینید.' },
    { selector: '[data-tour="features"]', title: 'چرا آموزش‌یار؟', text: 'پیش‌نمایش رایگان، مدرس‌های تاییدشده، پرداخت امن و دسترسی همیشگی به دوره‌ی خریداری‌شده.' },
    { selector: '[data-tour="featured-courses"]', title: 'دوره‌های پیشنهادی', text: 'چند نمونه از دوره‌های تازه؛ روی هرکدوم بزنید تا پیش‌نمایش رایگانش رو ببینید.' },
    { selector: '[data-tour="featured-instructors"]', title: 'مدرس‌های ما', text: 'پروفایل کامل هر مدرس، امتیاز و شماره تماسش از همین‌جا در دسترسه.' },
  ],

  courses: [
    { selector: '[data-tour="course-grid"]', title: 'فهرست دوره‌ها', text: 'همه‌ی دوره‌های منتشرشده اینجا هستن؛ با کلیک روی دسته‌بندی در صفحه‌ی اصلی، همین فهرست فیلتر می‌شه.' },
  ],
  'courses-slug': [
    { selector: '[data-tour="lesson-list"]', title: 'سرفصل‌های دوره', text: 'روی هر جلسه بزنید تا پخش بشه. جلسه‌های قفل‌شده فقط یه پیش‌نمایش کوتاه نشون می‌دن.' },
    { selector: '[data-tour="course-buy-cta"]', title: 'ثبت‌نام در دوره', text: 'با این دکمه به درگاه پرداخت زرین‌پال می‌رید؛ بعد از پرداخت موفق، دسترسی کامل بلافاصله فعال می‌شه.' },
  ],

  instructors: [
    { selector: '[data-tour="instructor-grid"]', title: 'مدرس‌های آموزش‌یار', text: 'امتیاز، شماره تماس و لینک پروفایل کامل هر مدرس از همین کارت‌ها در دسترسه.' },
  ],
  'instructors-slug': [
    { selector: '[data-tour="instructor-header"]', title: 'پروفایل مدرس', text: 'امتیاز، تعداد دانشجوها، شماره تماس و بیوگرافی کامل مدرس اینجاست.' },
  ],

  dashboard: [
    { selector: '[data-tour="continue-learning"]', title: 'ادامه‌ی یادگیری', text: 'دقیقاً از همون جایی که آخرین بار درس رو ول کردید، ادامه می‌دید.' },
  ],
  'dashboard-my-courses': [
    { selector: '[data-tour="my-courses-grid"]', title: 'دوره‌های من', text: 'همه‌ی دوره‌هایی که خریداری کردید اینجا هستن؛ با کلیک روی هرکدوم وارد محتوای کاملش می‌شید.' },
  ],
  'dashboard-calendar': [
    { selector: '[data-tour="student-calendar"]', title: 'تقویم کلاس‌ها', text: 'روزهایی که کلاس زنده دارید روی تقویم علامت خورده؛ روی یه روز بزنید تا فقط جلسات همون روز رو ببینید.' },
    { selector: '[data-tour="upcoming-sessions"]', title: 'جلسات پیش رو', text: 'زمان دقیق هر کلاس زنده و اینکه آنلاینه یا نه، همین‌جا نشون داده می‌شه.' },
  ],
  'dashboard-orders': [
    { selector: '[data-tour="orders-heading"]', title: 'سفارش‌های من', text: 'تاریخچه‌ی خریدها و وضعیت پرداخت هرکدوم اینجا نمایش داده می‌شه.' },
  ],

  'instructor-panel-courses': [
    { selector: '[data-tour="new-course"]', title: 'ساخت دوره‌ی جدید', text: 'دوره‌ی جدید از همین دکمه ساخته می‌شه و برای تایید به صف ادمین می‌ره.' },
    { selector: '[data-tour="manage-lessons-link"]', title: 'مدیریت سرفصل و ویدیو', text: 'از این لینک، ویدیوی هر جلسه رو آپلود و کلاس‌های زنده رو زمان‌بندی می‌کنید.' },
  ],
  'instructor-panel-courses-create': [
    { selector: '[data-tour="course-create-form"]', title: 'ساخت دوره‌ی جدید', text: 'عنوان، توضیحات، دسته‌بندی و قیمت رو وارد کنید. دوره تا تایید ادمین برای عموم نمایش داده نمی‌شه.' },
  ],
  'instructor-panel-courses-id-lessons': [
    { selector: '[data-tour="lesson-manager"]', title: 'سرفصل‌ها و ویدیو', text: 'جلسه بسازید و ویدیوش رو آپلود کنید؛ پردازش و ساخت پیش‌نمایش رایگان خودکار انجام می‌شه.' },
    { selector: '[data-tour="class-session-manager"]', title: 'کلاس‌های زنده', text: 'برای جلسات زنده (نه ویدیوی ضبط‌شده)، زمانش رو اینجا ثبت کنید تا در تقویم دانشجوها بیفته.' },
  ],

  admin: [
    { selector: '[data-tour="admin-pending-courses-stat"]', title: 'دوره‌های در انتظار تایید', text: 'تعداد دوره‌هایی که منتظر بررسی شما هستن؛ با کلیک وارد فهرست کامل می‌شید.' },
    { selector: '[data-tour="admin-pending-instructors-stat"]', title: 'مدرس‌های در انتظار تایید', text: 'تعداد مدرس‌هایی که ثبت‌نامشون منتظر تایید شماست.' },
  ],
  'admin-board': [
    { selector: '[data-tour="board-column-pending_review"]', title: 'در انتظار بررسی', text: 'دوره‌های تازه ارسال‌شده اینجا منتظر تصمیم شما می‌مونن.' },
    { selector: '[data-tour="board-card"]', title: 'کارت دوره', text: 'هر کارت رو بکشید و به ستون دیگه ببرید تا وضعیتش تغییر کنه — رد کردن یه دلیل می‌خواد.' },
  ],
  'admin-calendar': [
    { selector: '[data-tour="admin-calendar-grid"]', title: 'تقویم سامانه', text: 'همه‌ی کلاس‌های زنده‌ی تمام دوره‌ها، از تمام مدرس‌ها، روی یه تقویم.' },
    { selector: '[data-tour="admin-calendar-sessions"]', title: 'فهرست کلاس‌ها', text: 'با انتخاب یه روز از تقویم، فقط کلاس‌های همون روز اینجا فیلتر می‌شن.' },
  ],
  'admin-courses': [
    { selector: '[data-tour="course-approval-list"]', title: 'تایید یا رد دوره', text: 'رزومه‌ی مدرس رو ببینید و بعد دوره رو تایید یا با ذکر دلیل رد کنید.' },
    { selector: '[data-tour="all-courses-table"]', title: 'همه‌ی دوره‌ها', text: 'از این جدول، به مدیریت سرفصل و ویدیوی هر دوره (حتی دوره‌های ساخته‌شده توسط خودتان) دسترسی دارید.' },
  ],
  'admin-courses-create': [
    { selector: '[data-tour="admin-course-create-form"]', title: 'ثبت مستقیم دوره', text: 'دوره‌ای که خودتان اینجا می‌سازید نیازی به تایید نداره و بلافاصله منتشر می‌شه.' },
  ],
  'admin-courses-id-lessons': [
    { selector: '[data-tour="lesson-manager"]', title: 'سرفصل‌ها و ویدیو', text: 'جلسه بسازید و ویدیوش رو آپلود کنید؛ پردازش و ساخت پیش‌نمایش رایگان خودکار انجام می‌شه.' },
    { selector: '[data-tour="class-session-manager"]', title: 'کلاس‌های زنده', text: 'زمان‌بندی جلسات زنده‌ی این دوره رو از همین‌جا مدیریت می‌کنید.' },
  ],
  'admin-instructors': [
    { selector: '[data-tour="instructor-approval-list"]', title: 'تایید یا رد مدرس', text: 'رزومه رو بررسی کنید و بعد پروفایل مدرس رو تایید یا با ذکر دلیل رد کنید.' },
  ],
  'admin-instructors-create': [
    { selector: '[data-tour="instructor-create-form"]', title: 'افزودن مدرس جدید', text: 'حساب مدرس مستقیماً ساخته می‌شه؛ بعداً خودش با همین ایمیل و رمز وارد می‌شه و پروفایلش رو تکمیل می‌کنه.' },
  ],
  'admin-users': [
    { selector: '[data-tour="user-search"]', title: 'جست‌وجوی کاربر', text: 'با ایمیل یا نام، هر کاربر رو سریع پیدا کنید.' },
    { selector: '[data-tour="user-table"]', title: 'مدیریت دسترسی', text: 'نقش هر کاربر (دانشجو، مدرس، ادمین) و فعال یا غیرفعال بودن حسابش رو از همین جدول تغییر بدید.' },
  ],

  profile: [
    { selector: '[data-tour="avatar-upload"]', title: 'عکس و نام پروفایل', text: 'از روی آیکن مداد، عکس پروفایلتون رو عوض کنید و نام و نام خانوادگی رو ویرایش کنید.' },
    { selector: '[data-tour="theme-toggle"]', title: 'حالت روشن و تاریک', text: 'با یه کلیک بین حالت روشن و تاریک سامانه جابه‌جا بشید.' },
    { selector: '[data-tour="palette-picker"]', title: 'پالت رنگی', text: 'رنگ اصلی سامانه رو برای حساب خودتون انتخاب کنید — روی همه‌ی دستگاه‌هاتون اعمال می‌شه.' },
  ],
}

export function useGuide() {
  const isOpen = useState('guide-open', () => false)
  const isTouring = useState('guide-touring', () => false)
  const stepIndex = useState('guide-step', () => 0)
  // The tour narrates itself by default (auto-advancing through every
  // step) — this just toggles whether it's currently doing that; the
  // step list and position stay the same either way, so pausing never
  // loses your place.
  const isAutoPlaying = useState('guide-autoplay', () => true)

  const route = useRoute()
  const routeName = computed(() => String(route.name ?? ''))
  const stepsForRoute = computed(() => TOUR_STEPS[routeName.value] ?? [])
  // Narration is pre-rendered per step (see scripts/extract-tour-text.mjs
  // and the generation notes in public/audio/tour/README.md) — a static
  // file the browser just plays, not something synthesized on the fly.
  const currentAudioUrl = computed(() => {
    if (!stepsForRoute.value.length) return null
    return `/audio/tour/${routeName.value}-${stepIndex.value}.wav`
  })

  function open() {
    isOpen.value = true
  }
  function close() {
    isOpen.value = false
  }
  function startTour() {
    if (!stepsForRoute.value.length) return
    stepIndex.value = 0
    isAutoPlaying.value = true
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
  function toggleAutoPlay() {
    isAutoPlaying.value = !isAutoPlaying.value
  }

  return {
    isOpen, isTouring, stepIndex, stepsForRoute, isAutoPlaying, currentAudioUrl,
    open, close, startTour, endTour, next, prev, toggleAutoPlay,
  }
}
