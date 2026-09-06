# آموزش‌یار — پلتفرم آموزش آنلاین و ویترین مدرس‌ها

پلتفرم LMS با فرانت‌اند Nuxt 3 (Vue.js)، بک‌اند Django + Django REST Framework، و دیتابیس PostgreSQL. جزئیات کامل معماری و تصمیمات فنی در [docs/adr/](docs/adr/) مستند شده‌اند.

## ساختار مخزن

```
amozeshyar/
├── backend/       # Django + DRF API
├── frontend/      # Nuxt 3 (Vue.js) — SSR برای سئو
├── docs/          # مستندات معماری و ADRها
└── docker-compose.yml
```

## راه‌اندازی سریع (لوکال)

### پیش‌نیازها
- Docker Desktop (برای Postgres, Redis, MinIO)
- Python 3.12+ (اگر بک‌اند را خارج از Docker اجرا می‌کنید)
- Node.js 20+ (اگر فرانت را خارج از Docker اجرا می‌کنید)

### با Docker Compose

```bash
docker compose up -d postgres redis minio
```

### بک‌اند (خارج از Docker)

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # ویندوز
cp .env.example .env     # و مقادیر را تنظیم کنید
pip install -r requirements/dev.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

مستندات API: `http://localhost:8000/api/docs/` (Swagger) و `http://localhost:8000/api/redoc/`

### فرانت‌اند (خارج از Docker)

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

اپ روی `http://localhost:3000` بالا می‌آید.

### Celery worker (پردازش ویدیو)

```bash
cd backend
celery -A config worker -l info
```

## ویژگی‌های کلیدی

- ثبت‌نام/ورود با نقش‌های دانشجو، مدرس، ادمین (JWT)
- پروفایل عمومی مدرس و صفحه‌ی دوره با نیاز به تایید ادمین قبل از انتشار
- آپلود ویدیو با پردازش خودکار (ffmpeg/Celery) و تولید کلیپ پیش‌نمایش رایگان (پیش‌فرض ۳۰ ثانیه) — نگاه کنید به [docs/adr/0003-video-preview-gating.md](docs/adr/0003-video-preview-gating.md)
- پرداخت با زرین‌پال و ثبت‌نام تراکنشی در دوره
- سئو: رندر سمت سرور (SSR) برای صفحات عمومی، JSON-LD، sitemap/robots خودکار
- دو زبانه: فارسی (پیش‌فرض، RTL) و انگلیسی

## مستندات بیشتر

- [backend/README.md](backend/README.md)
- [frontend/README.md](frontend/README.md)
- [docs/adr/](docs/adr/) — تصمیمات معماری و دلیل هرکدام
