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
    { selector: '[data-tour="header-login"]', title: 'ورود یا ثبت‌نام', text: 'برای خرید دوره و شرکت در دوره‌های آنلاین، اول باید وارد حساب خودتون بشید — یه پاپ‌آپ سبک باز می‌شه، نه یه صفحه‌ی جدا.' },
    { selector: '[data-tour="hero-cta"]', title: 'مشاهده‌ی دوره‌ها', text: 'با این دکمه به فهرست کامل دوره‌های سایت می‌رسید.' },
    { selector: '[data-tour="featured-courses"]', title: 'دوره‌ها', text: 'چند نمونه از دوره‌های تازه؛ روی هرکدوم بزنید تا پیش‌نمایش رایگانش رو ببینید.' },
    { selector: '[data-tour="features"]', title: 'چرا این دوره‌ها؟', text: 'پیش‌نمایش رایگان، دوره‌های آنلاین، پرداخت امن و دسترسی همیشگی به دوره‌ی خریداری‌شده.' },
    { selector: '[data-tour="categories"]', title: 'دسته‌بندی دوره‌ها', text: 'روی هر دسته کلیک کنید تا فقط دوره‌های همون موضوع رو ببینید.' },
  ],

  courses: [
    { selector: '[data-tour="course-grid"]', title: 'فهرست دوره‌ها', text: 'همه‌ی دوره‌های منتشرشده اینجا هستن؛ با کلیک روی دسته‌بندی در صفحه‌ی اصلی، همین فهرست فیلتر می‌شه.' },
  ],
  'courses-slug': [
    { selector: '[data-tour="lesson-list"]', title: 'سرفصل‌های دوره', text: 'روی هر جلسه بزنید تا پخش بشه. جلسه‌های قفل‌شده فقط یه پیش‌نمایش کوتاه نشون می‌دن.' },
    { selector: '[data-tour="course-buy-cta"]', title: 'ثبت‌نام در دوره', text: 'با این دکمه به درگاه پرداخت زرین‌پال می‌رید؛ بعد از پرداخت موفق، دسترسی کامل بلافاصله فعال می‌شه.' },
    { selector: '[data-tour="course-enter"]', title: 'ورود به دوره', text: 'اگه ثبت‌نام کردید، از اینجا وارد صفحه‌ی یادگیری دوره می‌شید: ویدیوها، فایل‌ها و پیشرفتتون.' },
  ],

  dashboard: [
    { selector: '[data-tour="dashboard-stats"]', title: 'پیشرفت شما', text: 'چند جلسه رو تموم کردید، در چند دوره ثبت‌نام کردید و چند دقیقه یاد گرفتید.' },
    { selector: '[data-tour="continue-learning"]', title: 'ادامه‌ی یادگیری', text: 'دقیقاً از همون جلسه و همون ثانیه‌ای که آخرین بار ول کردید، ادامه می‌دید.' },
    { selector: '[data-tour="next-session"]', title: 'دوره‌ی آنلاین بعدی', text: 'شمارش معکوس تا دوره‌ی آنلاین بعدی؛ از پونزده دقیقه قبل، دکمه‌ی ورود سبز می‌شه.' },
    { selector: '[data-tour="recent-files"]', title: 'تازه‌ترین فایل‌ها', text: 'جزوه‌ها و فایل‌هایی که استاد تازه گذاشته؛ با یه کلیک دانلود کنید.' },
    { selector: '[data-tour="teacher-card"]', title: 'استاد شما', text: 'همه‌ی دوره‌های استادتون از همین‌جا در دسترسه.' },
  ],
  'dashboard-my-courses': [
    { selector: '[data-tour="my-courses-grid"]', title: 'دوره‌های من', text: 'هر دوره نوار پیشرفت خودش رو داره؛ دوره‌های نیمه‌تموم اول میان. روی هر کدوم بزنید تا وارد صفحه‌ی یادگیری‌اش بشید.' },
  ],
  'dashboard-calendar': [
    { selector: '[data-tour="student-calendar"]', title: 'تقویم دوره‌های آنلاین', text: 'روزهایی که دوره‌ی آنلاین دارید روی تقویم علامت خورده؛ روی یه روز بزنید تا فقط جلسات همون روز رو ببینید.' },
    { selector: '[data-tour="upcoming-sessions"]', title: 'جلسات پیش رو', text: 'زمان دقیق هر دوره‌ی آنلاین و اینکه آنلاینه یا نه، همین‌جا نشون داده می‌شه.' },
  ],
  'dashboard-orders': [
    { selector: '[data-tour="orders-heading"]', title: 'سفارش‌های من', text: 'تاریخچه‌ی خریدها و وضعیت پرداخت هرکدوم اینجا نمایش داده می‌شه.' },
  ],

  admin: [
    { selector: '[data-tour="admin-courses-stat"]', title: 'دوره‌های شما', text: 'تعداد دوره‌هایی که روی سایت منتشر شدن؛ با کلیک وارد فهرست کامل دوره‌ها می‌شید.' },
    { selector: '[data-tour="admin-sessions-stat"]', title: 'دوره‌های آنلاین پیش رو', text: 'تعداد دوره‌های آنلاینی که زمان‌بندی کردید؛ با کلیک به تقویم دوره‌های آنلاین می‌رید.' },
  ],
  'admin-calendar': [
    { selector: '[data-tour="admin-calendar-grid"]', title: 'تقویم دوره‌های آنلاین', text: 'همه‌ی دوره‌های آنلاینتون روی یه تقویم.' },
    { selector: '[data-tour="admin-calendar-sessions"]', title: 'فهرست دوره‌های آنلاین', text: 'با انتخاب یه روز از تقویم، فقط دوره‌های آنلاین همون روز اینجا فیلتر می‌شن.' },
  ],
  'admin-courses': [
    { selector: '[data-tour="new-course-btn"]', title: 'دوره‌ی جدید', text: 'از اینجا دوره‌ی تازه بسازید؛ بلافاصله روی سایت منتشر می‌شه.' },
    { selector: '[data-tour="all-courses-table"]', title: 'همه‌ی دوره‌ها', text: 'از این جدول سرفصل‌ها، ویدیوها و دوره‌های آنلاین هر دوره رو مدیریت کنید، یا دوره رو منتشر کنید و به پیش‌نویس برگردونید.' },
  ],
  'admin-courses-create': [
    { selector: '[data-tour="admin-course-create-form"]', title: 'دوره‌ی جدید', text: 'عنوان، توضیحات، دسته‌بندی و قیمت رو وارد کنید؛ دوره بلافاصله روی سایت منتشر می‌شه.' },
  ],
  'admin-courses-id-lessons': [
    { selector: '[data-tour="lesson-stats"]', title: 'خلاصه‌ی دوره', text: 'تعداد جلسه‌ها، ویدیوهای آماده، فایل‌ها و مدت کل دوره.' },
    { selector: '[data-tour="lesson-add"]', title: 'افزودن جلسه', text: 'عنوان جلسه‌ی جدید رو بنویسید و اضافه کنید؛ جلسه‌ی اول خودکار برای همه رایگانه.' },
    { selector: '[data-tour="lesson-video"]', title: 'ویدیوی جلسه', text: 'ویدیو رو اینجا بکشید و رها کنید؛ درصد، حجم و زمان باقی‌مونده‌ی آپلود رو می‌بینید و بعد خودکار پردازش می‌شه.' },
    { selector: '[data-tour="lesson-files"]', title: 'فایل‌ها و جزوه‌ها', text: 'چند فایل رو با هم آپلود کنید؛ فقط دانشجوهای ثبت‌نام‌شده می‌تونن دانلودشون کنن.' },
    { selector: '[data-tour="lesson-tools"]', title: 'مرتب‌سازی و حذف', text: 'ترتیب جلسه‌ها رو با فلش‌ها عوض کنید یا جلسه رو حذف کنید. برای تغییر عنوان، روی خودش بزنید.' },
    { selector: '[data-tour="class-session-manager"]', title: 'دوره‌های آنلاین', text: 'زمان‌بندی جلسات زنده‌ی این دوره رو از همین‌جا مدیریت می‌کنید.' },
  ],
  'admin-settings': [
    { selector: '[data-tour="settings-brand"]', title: 'نام و لوگوی سایت', text: 'نام و لوگویی که بالای همه‌ی صفحه‌ها و در فوتر دیده می‌شه.' },
    { selector: '[data-tour="settings-background"]', title: 'پس‌زمینه‌ی سایت', text: 'سبک و رنگ‌های پس‌زمینه‌ی متحرک سایت رو انتخاب کنید؛ پشت همین صفحه پیش‌نمایش می‌شه.' },
    { selector: '[data-tour="settings-about"]', title: 'معرفی', text: 'عنوان تخصص و متن معرفی شما در صفحه‌ی اول.' },
    { selector: '[data-tour="settings-photo"]', title: 'عکس صفحه‌ی اول', text: 'عکس پرتره‌ی شما، دقیقاً با همون برشی که در صفحه‌ی اول دیده می‌شه.' },
    { selector: '[data-tour="settings-links"]', title: 'لینک‌ها', text: 'شبکه‌های اجتماعی و لینک‌هاتون رو اضافه یا حذف کنید؛ در فوتر نمایش داده می‌شن.' },
    { selector: '[data-tour="settings-preview"]', title: 'پیش‌نمایش', text: 'قبل از ذخیره ببینید صفحه‌ی اول چه شکلی می‌شه.' },
    { selector: '[data-tour="settings-save"]', title: 'ذخیره', text: 'تا ذخیره نزنید، تغییرات روی سایت نمی‌ره.' },
  ],
  'admin-users': [
    { selector: '[data-tour="user-search"]', title: 'جست‌وجوی کاربر', text: 'با ایمیل یا نام، هر کاربر رو سریع پیدا کنید.' },
    { selector: '[data-tour="user-table"]', title: 'مدیریت دسترسی', text: 'نقش هر کاربر (دانشجو یا ادمین) و فعال یا غیرفعال بودن حسابش رو از همین جدول تغییر بدید.' },
  ],

  profile: [
    { selector: '[data-tour="avatar-upload"]', title: 'عکس و نام پروفایل', text: 'از روی آیکن مداد، عکس پروفایلتون رو عوض کنید و نام و نام خانوادگی رو ویرایش کنید.' },
    { selector: '[data-tour="theme-toggle"]', title: 'حالت روشن و تاریک', text: 'با یه کلیک بین حالت روشن و تاریک سامانه جابه‌جا بشید.' },
    { selector: '[data-tour="palette-picker"]', title: 'پالت رنگی', text: 'رنگ اصلی سامانه رو برای حساب خودتون انتخاب کنید — روی همه‌ی دستگاه‌هاتون اعمال می‌شه.' },
  ],

  'dashboard-courses-slug': [
    { selector: '[data-tour="learn-progress"]', title: 'پیشرفت این دوره', text: 'چند درصد از جلسه‌های این دوره رو تموم کردید.' },
    { selector: '[data-tour="learn-player"]', title: 'پخش جلسه', text: 'ویدیوی جلسه اینجا پخش می‌شه و جای توقفتون خودکار ذخیره می‌شه.' },
    { selector: '[data-tour="learn-complete"]', title: 'علامت تکمیل', text: 'وقتی جلسه رو تموم کردید اینجا بزنید؛ جلسه‌ی بعدی خودکار باز می‌شه.' },
    { selector: '[data-tour="learn-files"]', title: 'فایل‌های جلسه', text: 'جزوه‌ها و فایل‌های همین جلسه؛ روی هرکدوم بزنید تا دانلود بشه.' },
    { selector: '[data-tour="learn-lessons"]', title: 'فهرست جلسه‌ها', text: 'همه‌ی جلسه‌ها با تیک تکمیل، مدت ویدیو و تعداد فایل؛ روی هرکدوم بزنید تا بره سراغش.' },
  ],

  'classroom-id': [
    { selector: '[data-tour="classroom-back"]', title: 'خروج از دوره‌ی آنلاین', text: 'هر وقت خواستید، از اینجا به صفحه‌ای که ازش اومدید برمی‌گردید.' },
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
