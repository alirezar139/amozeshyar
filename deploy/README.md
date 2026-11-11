# استقرار یک سایت آموزش‌یار روی سرور

همه‌چیز (PostgreSQL، Redis، MinIO، API جنگو، Celery و فرانت Nuxt) با Docker روی یک سرور اجرا می‌شود و nginx روی خود سرور، HTTPS و مسیرها را مدیریت می‌کند.

## فایل‌ها

- `docker-compose.prod.yml`: سرویس‌ها، صف‌های جدا و سقف رم (بخش «منابع»)
- `backend.Dockerfile`: ایمیج API و Celery (با ffmpeg)
- `frontend.Dockerfile`: ایمیج Nuxt
- معماری کامل و راهنمای عملیات: [`docs/architecture.md`](../docs/architecture.md)
- `nginx.conf`: نمونه‌ی تنظیم nginx روی سرور (یک دامنه برای همه‌چیز، با محدودیت نرخ و اتصال، بافر آپلود و هدرهای امنیتی)
- `release.sh` (روی لپ‌تاپ) و `server-release.sh` (روی سرور): انتشار با بکاپ، migrate، سوئیچ، بررسی سلامت و بازگشت خودکار
- `backup.sh` و `restore.sh`: بکاپ شبانه‌ی دیتابیس و فایل‌های MinIO، و بازیابی
- `minio-init.sh`: ساخت باکت و کاربر محدود برنامه در MinIO
- `monitor.sh`: بررسی سلامت و منابع هر ۵ دقیقه، با هشدار در بله/تلگرام
- `server-report.sh`: گزارش فقط‌خواندنی منابع سرور

## فایل `deploy/.env` (روی سرور، داخل git نیست)

```env
PUBLIC_URL=https://SITE_HOST
POSTGRES_PASSWORD=...
DJANGO_SECRET_KEY=...
DJANGO_ALLOWED_HOSTS=SITE_HOST,backend   # backend: درخواست‌های SSR فرانت مستقیم به http://backend:8000 می‌آیند
CORS_ALLOWED_ORIGINS=https://SITE_HOST
DATABASE_URL=postgres://amozeshyar:POSTGRES_PASSWORD@postgres:5432/amozeshyar
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
MINIO_ROOT_USER=...          # فقط MinIO و minio-init؛ برنامه هرگز آن را نمی‌بیند
MINIO_ROOT_PASSWORD=...
STORAGE_ACCESS_KEY=...       # کاربر جدا و محدود به همین باکت (minio-init می‌سازدش)
STORAGE_SECRET_KEY=...
STORAGE_BUCKET_NAME=modaresyar-media
STORAGE_ENDPOINT_URL=https://SITE_HOST
STORAGE_REGION=us-east-1
ZARINPAL_MERCHANT_ID=
ZARINPAL_SANDBOX=True
ZARINPAL_CALLBACK_URL=https://SITE_HOST/checkout/callback
SITE_URL=https://SITE_HOST
EMAIL_URL=smtp+tls://USER:PASSWORD@SMTP_HOST:587
DEFAULT_FROM_EMAIL=no-reply@SITE_HOST
SMS_PROVIDER=
```

`EMAIL_URL` برای بازیابی رمز عبور لازم است: بدون آن لینک بازیابی به هیچ‌جا فرستاده نمی‌شود (هم ایمیل خاموش است و هم پیامک، تا وقتی `SMS_PROVIDER` تنظیم نشده باشد). در آن حالت مدرس هنوز می‌تواند از «مدیریت دسترسی کاربران» رمز را دستی عوض کند. رسید خرید و نتیجه‌ی استرداد در هر حال در پیام‌رسان سایت به دانشجو می‌رسد.

`STORAGE_ENDPOINT_URL` عمداً آدرس عمومی سایت است: لینک‌های امضاشده‌ی ویدیو برای همین دامنه ساخته می‌شوند و nginx آن‌ها را به MinIO می‌رساند.

متغیرهای اختیاری. پیش‌فرض‌ها در آزمایش پایلوت اندازه‌گیری شده‌اند و معمولاً لازم نیست آن‌ها را بنویسید:

```env
THROTTLE_ANON_RATE=2000/hour     # درخواست‌های بدون ورود برای هر IP
THROTTLE_AUTH_RATE=30/minute     # ورود و ثبت‌نام برای هر IP
STORAGE_UPLOAD_THREADS=8         # موازی‌سازی ارسال فایل به MinIO
```

یک کلاس روی یک Wi-Fi، یا کاربرانی که پشت NAT اپراتور موبایل‌اند، همه یک IP حساب می‌شوند. با مقادیر قبلی (۱۰۰ در ساعت و ۱۰ در دقیقه)، از ۳۰ دانشجویی که هم‌زمان وارد می‌شدند فقط ۴ نفر موفق شدند. با مقادیر فعلی هر ۳۰ نفر وارد شدند. جلوی حدس رمز را همچنان پازل امنیتی می‌گیرد، چون برای هر تلاش ورود لازم است.

## راه‌اندازی

ایمیج‌ها را GitHub Actions می‌سازد ([`images.yml`](../.github/workflows/images.yml)) و سرور فقط از `ghcr.io` می‌کشد؛ build روی خود سرور به خاطر قطعی PyPI/npm قابل اعتماد نیست. `IMAGE_TAG` در `.env` مشخص می‌کند کدام commit اجرا شود (`release.sh` خودش تنظیمش می‌کند).

```bash
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env pull
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env up -d
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env exec backend python manage.py migrate
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env exec backend python manage.py setup_site --email ... --password ... --first-name ... --last-name ...
```

باکت MinIO و کاربر محدود برنامه را سرویس یک‌باره‌ی `minio-init` در هر `up` می‌سازد یا به‌روز می‌کند (بخش «کاربر جدا برای MinIO»). کار دستی لازم نیست.

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

$C up -d
bash deploy/restore.sh          # آخرین dump + فایل‌ها؛ برای dump خاص: --db FILE.dump
```

`restore.sh` برنامه را متوقف می‌کند، checksum فایل dump را بررسی می‌کند، دیتابیس را برمی‌گرداند (`pg_restore --clean`)، فایل‌های MinIO را از mirror کپی می‌کند (چیزی پاک نمی‌کند)، همه‌چیز را دوباره روشن می‌کند و در آخر تعداد ردیف‌ها را برای بررسی سریع نشان می‌دهد. نتیجه‌ی آزمایش واقعی این مراحل در بخش «آزمایش بکاپ و بازیابی» آمده است.

### آزمایش بکاپ و بازیابی

آزمایش واقعی (۱۱ آبان ۱۴۰۵ / 2026-11-11) روی یک نسخه‌ی کامل همین compose با داده‌ی آزمایشی: ۲۰۱ کاربر، ۵ درس، ۳ ویدیوی ۱۰ دقیقه‌ای 720p با HLS و ۲۰ فایل دیگر.

| مرحله | نتیجه |
|---|---|
| بکاپ کامل (`backup.sh`) | ۳۰٫۵ ثانیه: dump ‏۱۷۲KB (۴۱۱ ورودی، بررسی‌شده با `pg_restore --list`) در کمتر از ۱ ثانیه، و ۱٫۶GB فایل در ۲۹ ثانیه |
| بکاپ قبل از انتشار (`--db-only`) | حدود ۱ ثانیه |
| خرابی | `docker compose down -v`: همه‌ی کانتینرها و volumeها (دیتابیس، MinIO، Redis) پاک شدند |
| بازیابی روی سرور خالی (`up -d` و بعد `restore.sh --yes`) | ۴۰٫۷ ثانیه: دیتابیس ۴ ثانیه، فایل‌ها ۲۴ ثانیه، بقیه روشن شدن |
| مقایسه با قبل از خرابی | یکسان: ۴۰ جدول با ۴۱۳ ردیف، و ۸۵ شیء (۱٫۶GB) با sha256 یکسان؛ فایل‌ها با کاربر محدود برنامه خوانده شدند |

زمان‌ها روی SSD لپ‌تاپ است. روی سرور با دیسک کندتر، زمان کپی فایل‌ها تقریباً با حجم آن‌ها بالا می‌رود (حدود ۳۰ ثانیه برای هر ۱٫۵GB روی SSD). دیتابیس این سایت‌ها کوچک است و بازیابی‌اش چند ثانیه طول می‌کشد. **هر سه ماه یک بار** همین آزمایش را روی یک سرور یا ماشین جدا تکرار کنید. بکاپی که بازیابی‌اش امتحان نشده، فقط امید است.

## منابع

اندازه‌گیری روی همین compose، هنگام کار عادی و هنگام تبدیل ویدیوی 720p (مگابایت، `docker stats` و `memory.stat` هر کانتینر):

| سرویس | معمول | بیشینه | سقف (`MEM_*`) |
|---|---|---|---|
| worker-video (حین ffmpeg) | ۴۲۰ | ۴۳۴ | ۶۴۰ (`MEM_WORKER_VIDEO`) |
| backend (gunicorn ۲×۴) | ۱۶۰ | ۳۲۰ (حین آپلود ویدیوی ۴۷۰MB) | ۵۱۲ (`MEM_BACKEND`) |
| worker (صف default و beat) | ۱۱۴ | ۱۴۸ | ۲۲۴ (`MEM_WORKER`) |
| minio | ۸۸ | ۲۳۸ | ۲۵۶ (`MEM_MINIO`) |
| frontend | ۳۷ | ۸۶ | ۱۹۲ (`MEM_FRONTEND`) |
| postgres | ۴۳ | ۵۱ | ۲۵۶ (`MEM_POSTGRES`) |
| redis | ۵ | ۱۲ | ۱۲۸ (`MEM_REDIS`) |

- سقف‌ها حد بالا هستند و رزرو نمی‌شوند. جمع بیشینه‌ها حدود ۱٫۳GB است و بیشترش مال تبدیل ویدیوست. **حداقل سرور: ۲GB رم با ۲GB swap**. اندازه‌ی راحت ۴GB است.
- ffmpeg حدود ۳۵۰MB می‌گیرد (720p، `VIDEO_TRANSCODE_THREADS=2`، preset `medium`). اگر رم کم است، `VIDEO_TRANSCODE_THREADS=1` بگذارید (کندتر و کم‌حافظه‌تر). اگر worker-video در `monitor.sh` نزدیک سقف دیده شد، `MEM_WORKER_VIDEO` را بالا ببرید.
- **یک باگ پیدا و رفع شد:** خواندن فایل از MinIO کل فایل را در رم نگه می‌داشت (پیش‌فرض django-storages). ویدیوی ۲GB worker را با OOM می‌کشت و هیچ‌وقت پردازش نمی‌شد. الان بیش از ۸MB روی دیسک می‌رود (`AWS_S3_MAX_MEMORY_SIZE`)، و فایل اصلی ویدیو مستقیم روی دیسک دانلود می‌شود.
- آپلود ویدیو (آزمایش پایلوت، فایل ۴۷۰MB از طریق nginx با TLS): سرور حدود ۵۳ ثانیه طول می‌کشد تا فایل را به MinIO برساند. backend در این مدت حداکثر ۳۲۰MB رم می‌گیرد. با تنظیم پیش‌فرض boto3 این عدد به ۴۰۵MB می‌رسید که از سقف قبلی (۳۸۴MB) بیشتر بود؛ برای همین سقف به ۵۱۲MB رسید، تا دو آپلود هم‌زمان هم جا شوند. در عمل سرعت اینترنت مدرس تعیین‌کننده است: با آپلود ۱۰ مگابیت، همین فایل حدود ۶٫۵ دقیقه طول می‌کشد. nginx کل فایل را اول خودش دریافت می‌کند، پس در این مدت هیچ thread از gunicorn اشغال نیست.
- تبدیل ویدیو روی ۲ هسته حدود ۰٫۷ برابر طول ویدیو طول می‌کشد: ویدیوی ۱۰ دقیقه‌ای در ۴۱۲ ثانیه و جلسه‌ی ۹۰ دقیقه‌ای حدود یک ساعت. ویدیوها یکی‌یکی پردازش می‌شوند.
- دیسک: تبدیل هر ویدیو موقتاً حدود دو برابر حجم فایل اصلی جا در `/tmp` کانتینر می‌خواهد. بکاپ محلی هم به اندازه‌ی کل فایل‌های MinIO جا می‌گیرد. `monitor.sh` بالای ۸۵٪ هشدار می‌دهد.
- PostgreSQL برای سقفش تنظیم شده (`shared_buffers=64MB`، `max_connections=40`). کوئری‌های کندتر از ۲ ثانیه در لاگش ثبت می‌شوند.
- گزارش منابع سرور واقعی (فقط‌خواندنی): `bash deploy/server-report.sh`. قبل از اولین انتشار این نسخه، خروجی‌اش را با جدول بالا مقایسه کنید.

## صف‌ها و پردازش ویدیو

| worker | صف | کار |
|---|---|---|
| `worker` | `default` و `celery` | بررسی پرداخت‌ها، پاک کردن فایل ویدیوهای حذف‌شده، و زمان‌بند (beat). صف `celery` برای ایمیج‌های قدیمی است تا بعد از rollback کارشان گم نشود. |
| `worker-video` | `video` | فقط تبدیل ویدیو، یکی‌یکی، با یک پروسه‌ی تازه برای هر ویدیو |

آزمایش‌شده:
- **جدا بودن صف‌ها:** حین تبدیل یک ویدیوی طولانی، بررسی پرداخت در ۰٫۰۵ ثانیه انجام شد.
- **توقف worker-video وسط تبدیل** (انتشار، ری‌استارت): با `SIGQUIT` در ۶ ثانیه متوقف می‌شود و کار فوراً به صف برمی‌گردد. همان کار وقتی دوباره می‌رسد، ویدیو را پس می‌گیرد و از اول شروع می‌کند. با تنظیم پیش‌فرض Docker (`SIGTERM`)، کار ۷ ساعت در Redis گیر می‌ماند.
- **ری‌استارت Redis:** صف‌ها حفظ شدند (AOF) و workerها در ۲ ثانیه وصل شدند. تبدیل در جریان ادامه پیدا کرد و تکرار نشد.
- **خاموشی ناگهانی کل Docker وسط تبدیل:** بعد از روشن شدن، کار برگشت و ویدیو `ready` شد.
- **ویدیوی گیرکرده** (worker مرده، یا ویدیویی که هنگام انتشار در حال پردازش بوده): `recover_stuck_videos` هر ۱۵ دقیقه آن را دوباره در صف می‌گذارد. بعد از ۳ بار، ویدیو `failed` می‌شود و مدرس در کارت درس دکمه‌ی «پردازش دوباره» را می‌بیند.
- خطای موقت ذخیره‌سازی تا ۴ بار دوباره امتحان می‌شود (۱، ۲، ۴، ۸ دقیقه). اگر ffmpeg فایل را رد کند یا زمانش تمام شود، ویدیو فوراً `failed` می‌شود و پیام روشنی دارد. سقف زمان ۳ برابر طول ویدیوست، بین ۳۰ دقیقه و ۶ ساعت.

فایل‌های ویدیوی حذف‌شده یا جایگزین‌شده بعد از commit پاک می‌شوند، و فقط وقتی هیچ ویدیوی دیگری از آن‌ها استفاده نکند. برای پیدا کردن فایل‌های یتیم قدیمی:

```bash
$C exec backend python manage.py cleanup_video_files                 # فقط فهرست (پیش‌فرض)
$C exec backend python manage.py cleanup_video_files --apply         # پاک کردن؛ فقط زیر lessons/ و قدیمی‌تر از ۲۴ ساعت
```

## کاربر جدا برای MinIO

برنامه با یک کاربر محدود به MinIO وصل می‌شود، نه با کاربر root. `minio-init.sh` این کاربر را می‌سازد. آزمایش‌شده: این کاربر در باکت خودش می‌تواند بنویسد، بخواند، فهرست بگیرد و پاک کند. ساختن یا پاک کردن باکت، تغییر policy، دیدن باکت‌های دیگر و دسترسی بی‌نام **رد می‌شوند**. کانتینرهای برنامه کلید root را ندارند.

**مهاجرت سرور موجود** (که الان `STORAGE_ACCESS_KEY` همان root است). ترتیب مهم است:

۱. در `deploy/.env`، مقدار فعلی `STORAGE_ACCESS_KEY` و `STORAGE_SECRET_KEY` را عیناً به `MINIO_ROOT_USER` و `MINIO_ROOT_PASSWORD` منتقل کنید. root خود MinIO نباید عوض شود، وگرنه MinIO با داده‌های قبلی بالا نمی‌آید.

۲. برای برنامه کلید تازه بگذارید:
   ```bash
   STORAGE_ACCESS_KEY=app-$(openssl rand -hex 4)
   STORAGE_SECRET_KEY=$(openssl rand -hex 24)
   ```

۳. انتشار عادی (`release.sh`). `minio-init` کاربر جدید را می‌سازد و برنامه با آن بالا می‌آید.

۴. بررسی: `$C logs minio-init` باید «app user limited to it» را نشان دهد، و پخش یک ویدیو در سایت باید کار کند.

اگر `MINIO_ROOT_*` تنظیم نشده باشد، compose مثل قبل از کلید برنامه به‌عنوان root استفاده می‌کند و `minio-init` کاری نمی‌کند. پس سرورهای قدیمی بدون این مراحل هم بالا می‌آیند.

**ایمیج MinIO:** MinIO دیگر ایمیج عمومی جدید منتشر نمی‌کند. tag مشخص‌شده (`RELEASE.2025-09-07T16-13-09Z`) را روی سرور نگه دارید (`docker image ls minio/minio`) و یک کپی از آن داشته باشید (`docker save minio/minio:RELEASE.2025-09-07T16-13-09Z | gzip > minio.tar.gz`)، تا سرور جدید به Docker Hub وابسته نباشد.

## انتشار و بازگشت

```bash
bash deploy/release.sh              # از لپ‌تاپ: آخرین commit برنچ main
bash deploy/release.sh --rollback   # برگشت به ایمیج‌های قبلی
```

روی سرور، `server-release.sh` این مراحل را به ترتیب انجام می‌دهد:

1. ایمیج‌های جدید را می‌کشد.
2. **از دیتابیس بکاپ می‌گیرد.** اگر بکاپ شکست بخورد، هیچ چیز را تغییر نمی‌دهد و متوقف می‌شود.
3. migrate را با ایمیج جدید اجرا می‌کند، در حالی که نسخه‌ی قبلی هنوز سرویس می‌دهد.
4. کانتینرها را عوض می‌کند.
5. منتظر سالم شدن backend و frontend می‌ماند. اگر کانتینری کرش کند یا ناسالم شود، **خودکار به نسخه‌ی قبل برمی‌گردد** و با کد خطا تمام می‌شود.

همه‌ی انتشارها و بازگشت‌ها در `deploy/.release-history` ثبت می‌شوند.

آزمایش‌شده:

| سناریو | نتیجه |
|---|---|
| انتشار عادی | ۲۳ ثانیه، با بکاپ و migrate. حدود ۵ ثانیه API جواب نمی‌دهد (موقع عوض شدن backend). nginx در این فاصله 502 می‌دهد. |
| نسخه‌ای که بالا نمی‌آید | تشخیص کرش و بازگشت خودکار، با ۱۴ ثانیه قطعی |
| بازگشت دستی | ۱۴ ثانیه. کد قبلی روی دیتابیس جدید سالم کار کرد. |

بازگشت فقط ایمیج‌ها را برمی‌گرداند و به دیتابیس دست نمی‌زند. Migrationهای این پروژه افزایشی هستند، پس کد قبلی روی دیتابیس جدید کار می‌کند. اگر لازم شد دیتابیس هم برگردد، از dump قبل از همان انتشار استفاده کنید. اطلاعات بعد از آن انتشار از بین می‌رود:

```bash
ls /var/backups/amozeshyar/db/*_pre-*.dump | tail -3
bash deploy/restore.sh --db /var/backups/amozeshyar/db/amozeshyar_..._pre-XXXXXXX.dump --db-only
```

## مانیتورینگ و لاگ

`release.sh` اسکریپت `monitor.sh` را در cron نصب می‌کند (هر ۵ دقیقه). این اسکریپت این موارد را بررسی می‌کند:
- پاسخ سایت؛
- روشن و سالم بودن کانتینرها، و ری‌استارت‌شدنشان (معمولاً یعنی کمبود حافظه)؛
- دیسک و رم سرور، و نزدیک شدن هر کانتینر به سقف رمش؛
- انباشته شدن صف‌ها؛
- تازه بودن بکاپ؛
- پرداخت‌هایی که بیش از ۳ ساعت تعیین تکلیف نشده‌اند.

هر مشکل یک بار هشدار داده می‌شود، تا وقتی ادامه دارد هر ۶ ساعت یادآوری می‌شود، و وقتی رفع شد «برطرف شد» می‌آید. این رفتار آزمایش شده است: worker متوقف شد، هشدار یک بار آمد و تکرار نشد، و بعد از روشن شدن «برطرف شد» آمد.

هشدار در بله: با @botfather در بله یک ربات بسازید و در یک گروه یا چت عضوش کنید. بعد `/etc/amozeshyar-monitor.conf` را با دسترسی `600` بسازید:

```bash
ALERT_BOT_TOKEN=...
ALERT_CHAT_ID=...
ALERT_BOT_API=https://tapi.bale.ai     # برای تلگرام: https://api.telegram.org
```

یک بار دستی امتحان کنید: `/usr/local/bin/amozeshyar-monitor`. خروجی در `/var/log/amozeshyar-monitor.log` است.

لاگ همه‌ی کانتینرها چرخشی است: حداکثر ۵ فایل ۱۰ مگابایتی برای هر کانتینر، پس دیسک را پر نمی‌کند. لاگ جنگو در production یک خط برای هر رویداد است، با زمان، سطح و ماژول:

```bash
$C logs --since 1h backend worker worker-video | grep -E "ERROR|WARNING"
```

## CSP و هدرهای امنیتی

nginx روی همه‌ی صفحه‌های Nuxt یک `Content-Security-Policy` می‌فرستد. اسکریپت، اتصال، iframe و فرم فقط از خود سایت مجازند؛ تنها استثنا Jitsi برای کلاس زنده است. `object-src` و `base-uri` بسته‌اند و سایت‌های دیگر نمی‌توانند صفحه‌ها را در iframe نشان دهند.

این policy روی ۸ صفحه‌ی اصلی، هم برای بازدیدکننده و هم برای کاربر واردشده، بررسی شد: همه‌ی منابع از خود سایت می‌آیند. در فایل‌های JS هم آدرس خارجی‌ای که بارگذاری شود پیدا نشد.

**محدودیت باقی‌مانده:** اسکریپت inline هنوز مجاز است (`'unsafe-inline'`). Nuxt تنظیمات زمان اجرا و اسکریپت تم را inline می‌گذارد، و اولی با هر انتشار تغییر می‌کند. قدم بعدی nonce با ماژول `nuxt-security` است. این policy هنوز در مرورگر واقعی امتحان نشده؛ چک‌لیست بعد از انتشار همین را می‌خواهد.

`Permissions-Policy` دوربین، میکروفون و اشتراک صفحه را فقط برای Jitsi باز می‌گذارد. مقدار قبلی (`camera=()`) دوربین کلاس زنده را هم خاموش می‌کرد.

**کلاس زنده:** نسخه‌ی عمومی `meet.jit.si` از ۱۸ مه ۲۰۲۳ هر جلسه‌ی embed شده را بعد از ۵ دقیقه قطع می‌کند ([اعلام Jitsi](https://community.jitsi.org/t/important-embedding-meet-jit-si-in-your-web-app-will-no-longer-be-supported-please-use-jaas/123003)). صفحه‌ی کلاس زنده دقیقاً همین را embed می‌کند، پس تا جایگزین شدنش با JaaS، Jitsi روی سرور خودتان یا یک سرویس داخلی، کلاس زنده را در پایلوت عرضه نکنید.

## چک‌لیست استقرار این نسخه

قبل از انتشار:
- [ ] `bash deploy/server-report.sh` روی سرور: رم (حداقل ۲GB به‌اضافه‌ی swap)، دیسک آزاد (حداقل ۲ برابر حجم فایل‌های MinIO به‌اضافه‌ی ۱۰GB)، و نسخه‌ی Docker Compose (۲.۲۴ یا بالاتر، برای `!reset`)
- [ ] ایمیج `minio/minio:RELEASE.2025-09-07T16-13-09Z` روی سرور هست (`docker image ls`)
- [ ] یک بکاپ کامل دستی گرفته شده: `/usr/local/bin/amozeshyar-backup`
- [ ] در `.env`، `DJANGO_ALLOWED_HOSTS` شامل `backend` است
- [ ] در `.env`، مقادیر `MINIO_ROOT_USER` و `MINIO_ROOT_PASSWORD` همان root فعلی‌اند و `STORAGE_ACCESS_KEY` و `STORAGE_SECRET_KEY` کلیدهای تازه‌اند (بخش «کاربر جدا برای MinIO»)
- [ ] تنظیم nginx با `deploy/nginx.conf` مقایسه و `nginx -t && systemctl reload nginx` اجرا شده. تغییرهای این نسخه:
  - بافر آپلود و `limit_conn`؛
  - CSP و Permissions-Policy؛
  - مسیر `/modaresyar-media` بدون اسلش آخر (بدون آن فایل‌های ویدیوی حذف‌شده پاک نمی‌شوند)؛
  - `/_ipx/`؛
  - `burst=60` برای ورود.
- [ ] فایل `/etc/amozeshyar-monitor.conf` با توکن ربات بله ساخته شده

انتشار:
- [ ] `bash deploy/release.sh`، که با «released» تمام می‌شود
- [ ] `$C ps`: همه‌ی کانتینرها `Up` باشند، backend و frontend `healthy`، و `minio-init` با `Exited (0)`
- [ ] `$C logs minio-init`، که «app user limited to it» را نشان می‌دهد

بعد از انتشار:
- [ ] ورود، صفحه‌ی دوره و پخش یک ویدیو، در مرورگر واقعی. Console مرورگر را باز کنید: نباید خطای `Content-Security-Policy` ببینید.
- [ ] `curl -sI https://SITE_HOST/ | grep -i content-security-policy`، که باید هدر CSP را نشان دهد
- [ ] نام سایت در `https://SITE_HOST/manifest.webmanifest` همان نام مدرس باشد، نه «مدرس‌یار»
- [ ] یک پرداخت واقعی با مبلغ کم (فقط با تأیید مالک) که به «پرداخت موفق» و دسترسی به دوره برسد، و بعد استرداد آن از پنل مدرس
- [ ] آپلود یک ویدیوی کوتاه که به `ready` برسد. حین تبدیل، `docker stats` را برای worker-video ببینید.
- [ ] `$C exec redis redis-cli CONFIG GET appendonly`، که `yes` برمی‌گرداند
- [ ] `/usr/local/bin/amozeshyar-monitor`، که «ok» بدهد (یا فقط هشدارهای قابل‌توضیح)
- [ ] فردای انتشار: `/var/log/amozeshyar-backup.log` شامل `backup ok` باشد

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
