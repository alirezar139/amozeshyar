# استقرار یک سایت آموزش‌یار روی سرور

همه‌چیز (PostgreSQL، Redis، MinIO، API جنگو، Celery و فرانت Nuxt) با Docker روی یک سرور اجرا می‌شود و nginx روی خود سرور، HTTPS و مسیرها را مدیریت می‌کند.

## فایل‌ها

- `docker-compose.prod.yml`: سرویس‌ها، با سقف رم برای سرور ۲ گیگی
- `backend.Dockerfile`: ایمیج API و Celery (با ffmpeg)
- `frontend.Dockerfile`: ایمیج Nuxt
- `nginx.conf`: نمونه‌ی تنظیم nginx روی سرور (یک دامنه برای همه‌چیز، با محدودیت نرخ و هدرهای امنیتی)
- `backup.sh`: بکاپ شبانه‌ی دیتابیس و فایل‌های MinIO

## فایل `deploy/.env` (روی سرور، داخل git نیست)

```env
PUBLIC_URL=https://SITE_HOST
POSTGRES_PASSWORD=...
DJANGO_SECRET_KEY=...
DJANGO_ALLOWED_HOSTS=SITE_HOST
CORS_ALLOWED_ORIGINS=https://SITE_HOST
DATABASE_URL=postgres://amozeshyar:POSTGRES_PASSWORD@postgres:5432/amozeshyar
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
STORAGE_ACCESS_KEY=...
STORAGE_SECRET_KEY=...
STORAGE_BUCKET_NAME=modaresyar-media
STORAGE_ENDPOINT_URL=https://SITE_HOST
STORAGE_REGION=us-east-1
ZARINPAL_MERCHANT_ID=
ZARINPAL_SANDBOX=True
ZARINPAL_CALLBACK_URL=https://SITE_HOST/checkout/callback
```

`STORAGE_ENDPOINT_URL` عمداً آدرس عمومی سایت است: لینک‌های امضاشده‌ی ویدیو برای همین دامنه ساخته می‌شوند و nginx آن‌ها را به MinIO می‌رساند.

## راه‌اندازی

```bash
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env up -d --build
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env exec backend python manage.py migrate
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env exec backend python manage.py setup_site --email ... --password ... --first-name ... --last-name ...
```

باکت MinIO (`modaresyar-media`) باید یک بار ساخته شود (مثلاً با boto3 از داخل کانتینر backend).

## بکاپ

```bash
install -m 700 deploy/backup.sh /usr/local/bin/amozeshyar-backup
echo '30 3 * * * root /usr/local/bin/amozeshyar-backup' > /etc/cron.d/amozeshyar-backup
```

بکاپ‌ها در `/var/backups/amozeshyar` روی همان دیسک سرور است؛ برای امنیت واقعی، گاهی یک کپی بیرون از سرور بگیرید.

## پنل ادمین جنگو

`/admin/` عمداً از بیرون باز نیست. برای دسترسی: `ssh -L 8100:127.0.0.1:8100 root@SERVER` و بعد `http://localhost:8100/admin/`.
