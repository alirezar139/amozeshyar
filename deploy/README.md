# استقرار یک سایت آموزش‌یار روی سرور

همه‌چیز (PostgreSQL، Redis، MinIO، API جنگو، Celery و فرانت Nuxt) با Docker روی یک سرور اجرا می‌شود و nginx روی خود سرور، HTTPS و مسیرها را مدیریت می‌کند.

## فایل‌ها

- `docker-compose.prod.yml`: سرویس‌ها، با سقف رم برای سرور ۲ گیگی
- `backend.Dockerfile`: ایمیج API و Celery (با ffmpeg)
- `frontend.Dockerfile`: ایمیج Nuxt
- معماری کامل و راهنمای عملیات: [`docs/architecture.md`](../docs/architecture.md)
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

ایمیج‌ها را GitHub Actions می‌سازد ([`images.yml`](../.github/workflows/images.yml)) و سرور فقط از `ghcr.io` می‌کشد؛ build روی خود سرور به خاطر قطعی PyPI/npm قابل اعتماد نیست. `IMAGE_TAG` در `.env` مشخص می‌کند کدام commit اجرا شود (`release.sh` خودش تنظیمش می‌کند).

```bash
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env pull
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env up -d
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env exec backend python manage.py migrate
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env exec backend python manage.py setup_site --email ... --password ... --first-name ... --last-name ...
```

باکت MinIO (`modaresyar-media`) باید یک بار ساخته شود (مثلاً با boto3 از داخل کانتینر backend).

## بکاپ

```bash
install -m 700 deploy/backup.sh /usr/local/bin/amozeshyar-backup
echo '30 3 * * * root /usr/local/bin/amozeshyar-backup >> /var/log/amozeshyar-backup.log 2>&1' > /etc/cron.d/amozeshyar-backup
```

هر شب دیتابیس (۱۴ نسخه‌ی آخر) و فایل‌های MinIO در `/var/backups/amozeshyar` ذخیره می‌شوند. این کپی روی همان دیسک سرور است، پس برای خرابی کامل سرور کافی نیست؛ بخش بعد کپی بیرون از سرور را راه می‌اندازد.

### کپی بیرون از سرور (rclone)

اسکریپت بعد از بکاپ محلی، اگر `OFFSITE_REMOTE` تنظیم شده باشد، همه‌چیز را با [rclone](https://rclone.org) به آن مقصد می‌فرستد. مقصد هر چیزی می‌تواند باشد که rclone می‌شناسد؛ پیشنهاد: **فضای ذخیره‌سازی ابری آروان (S3)** چون از سرور ایران سریع و بدون مشکل تحریم در دسترس است. یک سرور دیگر با SFTP هم کار می‌کند.

کپی قبل از خروج از سرور با یک remote از نوع `crypt` رمزنگاری می‌شود (بکاپ ایمیل و اطلاعات دانشجوها را دارد) و صاحب فضای ابری هم نمی‌تواند آن را بخواند.

۱. نصب: `apt install rclone`

۲. ساخت دو remote با `rclone config` (تنظیمات در `/root/.config/rclone/rclone.conf` ذخیره می‌شود):
   - `offsite`: نوع `s3`، provider `Other` (یا `Arvan` اگر در لیست بود)، endpoint و access key/secret از پنل آروان. یک باکت خصوصی در پنل بسازید (مثلاً `amozeshyar-backup`).
   - `offsite-crypt`: نوع `crypt`، با `remote = offsite:amozeshyar-backup`، رمزنگاری نام فایل `standard`، و دو رمز تصادفی (`rclone config` خودش می‌سازد).

۳. **رمزهای `offsite-crypt` را بیرون از سرور نگه دارید** (مثلاً در password manager خودتان). اگر سرور از بین برود و این رمزها فقط روی آن بوده باشند، بکاپ بیرونی قابل باز کردن نیست. ساده‌ترین راه: یک کپی از `rclone.conf` را جای امنی ذخیره کنید.

۴. فایل `/etc/amozeshyar-backup.conf` (دسترسی `600`):
   ```bash
   OFFSITE_REMOTE=offsite-crypt:
   OFFSITE_BWLIMIT=2M   # اختیاری: سقف سرعت آپلود تا سایت کند نشود
   ```

۵. یک بار دستی اجرا و بررسی کنید:
   ```bash
   /usr/local/bin/amozeshyar-backup
   rclone ls offsite-crypt:db | tail -3
   ```

اولین اجرا همه‌ی ویدیوها را می‌فرستد و ممکن است چند ساعت طول بکشد؛ از آن به بعد فقط فایل‌های جدید آن روز. دیتابیس در مقصد هم مثل سرور ۱۴ نسخه نگه داشته می‌شود؛ فایل‌های رسانه هیچ‌وقت از مقصد پاک نمی‌شوند.

وضعیت هر شب در `/var/log/amozeshyar-backup.log` است (`local backup ok` و `off-site copy ok`). هر چند وقت یک بار نگاهی بیندازید.

### بازیابی از کپی بیرونی (روی سرور جدید)

بعد از راه‌اندازی سرور طبق بخش «راه‌اندازی» و گذاشتن `rclone.conf` ذخیره‌شده در `/root/.config/rclone/`:

```bash
rclone copy offsite-crypt:db /var/backups/amozeshyar/db
rclone copy offsite-crypt:media /var/backups/amozeshyar/media
C="docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env"

# فایل‌ها: MinIO را متوقف کنید، محتوای volume را برگردانید، دوباره روشن کنید
$C stop minio
rsync -a /var/backups/amozeshyar/media/ "$(docker volume inspect amozeshyar_minio-data --format '{{ .Mountpoint }}')/"
$C start minio

# دیتابیس: آخرین dump
$C stop backend worker
docker exec -i amozeshyar-postgres-1 pg_restore -U amozeshyar -d amozeshyar --clean --if-exists     < "$(ls -1 /var/backups/amozeshyar/db/amozeshyar_*.dump | tail -1)"
$C start backend worker
```

## نوع فایل‌های ذخیره‌شده (یک بار، بعد از انتشار اصلاح SEC-01)

فایل‌هایی که قبل از این اصلاح آپلود شده‌اند با `Content-Type`ی ذخیره شده‌اند که مرورگر کاربر فرستاده بود (ممکن است `text/html` باشد). هدرهای جدید nginx روی `/modaresyar-media/` همین حالا جلوی اجرای آن‌ها را می‌گیرند؛ این دستور خود فایل‌ها را هم درست می‌کند:

```bash
C="docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env"
$C exec backend python manage.py secure_media_headers           # فقط گزارش: کدام فایل‌ها عوض می‌شوند
$C exec backend python manage.py secure_media_headers --apply   # بازنویسی هدرها
```

فقط `ContentType`/`ContentDisposition` هر شیء عوض می‌شود (کپی درجا با `MetadataDirective=REPLACE`)؛ محتوا و نام فایل‌ها دست نمی‌خورد و چیزی پاک نمی‌شود. اجرای دوباره بی‌خطر است.

### دامنه‌ی جدا برای فایل‌ها (پیشنهادی)

قوی‌ترین جداسازی این است که فایل‌ها اصلاً روی دامنه‌ی سایت نباشند. برای این کار یک زیر‌دامنه (مثلاً `media.SITE_HOST`) با گواهی جدا بسازید، یک `server` در nginx برای آن با همان `location /modaresyar-media/` (و همان هدرها) تعریف کنید و `STORAGE_ENDPOINT_URL=https://media.SITE_HOST` بگذارید. بعد از آن کوکی‌های سایت به آن دامنه فرستاده نمی‌شوند. فعلاً اختیاری است، چون سه لایه‌ی بالا مستقل از دامنه کار می‌کنند.

## گزارش پرداخت‌ها (`audit_payments`)

این دستور فقط گزارش می‌دهد و چیزی را تغییر نمی‌دهد. پرداخت دوباره برای یک سفارش یا یک دوره، کد تخفیفی که از سقفش رد شده، و پرداخت‌هایی را که بعد از دو روز هنوز روشن نشده‌اند فهرست می‌کند:

```bash
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env exec backend python manage.py audit_payments
```

یک بار قبل از انتشار اصلاح پرداخت (PAY-01/02/03) اجرایش کنید و موارد قدیمی را دستی در پنل زرین‌پال پیگیری کنید (استرداد). بعد از آن هم گاهی اجرا شود. پرداختی که الان `canceled` می‌شود نیازی به کار دستی ندارد، چون verify نشده و زرین‌پال خودکار پولش را برمی‌گرداند.

## پنل ادمین جنگو

`/admin/` عمداً از بیرون باز نیست. برای دسترسی: `ssh -L 8100:127.0.0.1:8100 root@SERVER` و بعد `http://localhost:8100/admin/`.
