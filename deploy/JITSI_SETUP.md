# راه‌اندازی کلاس زنده: Jitsi روی سرور خودتان

## چرا

- **`meet.jit.si` عمومی** هر جلسه‌ای را که داخل سایت دیگری embed شده باشد بعد از ۵ دقیقه قطع می‌کند ([اعلام Jitsi](https://community.jitsi.org/t/important-embedding-meet-jit-si-in-your-web-app-will-no-longer-be-supported-please-use-jaas/123003)). صفحه‌ی کلاس سایت دقیقاً همین را embed می‌کند.
- **ساخت خودکار جلسه با Google Meet API از سرور ایرانی ممکن نیست.** `meet.googleapis.com` از ایران پاسخ 403 می‌دهد (آزمایش ۲۰ آبان ۱۴۰۵).

Jitsi روی سرور خودتان این محدودیت‌ها را ندارد:

- محدودیت زمانی و تحریم ندارد؛
- همان صفحه‌ی کلاس فعلی سایت با آن کار می‌کند؛
- با **JWT** فقط کسی وارد می‌شود که سایت به او اجازه داده باشد.

## سایت چطور با Jitsi کار می‌کند

1. دانشجو یا استاد دکمه‌ی ورود به کلاس را می‌زند. سایت (`ClassSessionViewSet.join`) بررسی می‌کند که کاربر استاد سایت است یا ثبت‌نام فعال در همان دوره دارد.
2. سایت یک توکن کوتاه‌مدت می‌سازد (`apps/courses/live_class.py`). توکن یک ساعت اعتبار دارد، فقط برای همان اتاق و همان شخص است، و با `JITSI_APP_SECRET` امضا شده.
3. مرورگر با همین توکن وارد Jitsi می‌شود. Jitsi امضا، زمان انقضا و اتاق را بررسی می‌کند. **استاد moderator است و دانشجو فقط participant**، حتی اگر دانشجو اول وارد شده باشد.

آزمایش‌شده روی `docker-jitsi-meet` نسخه‌ی `stable-11248-3`، با پروتکل XMPP و همان کاری که کلاینت Jitsi می‌کند:

| حالت | نتیجه |
|---|---|
| دانشجو با توکن معتبر | ✅ وارد شد، با نقش participant و member |
| بدون توکن | ✅ رد شد |
| توکن جعلی | ✅ رد شد |
| توکن منقضی | ✅ رد شد |
| توکن معتبر برای اتاق دیگر | ✅ رد شد |
| استاد | ✅ وارد شد، با نقش moderator و owner |

**آزمایش‌نشده:** تماس واقعی صوت و تصویر در مرورگر، و کیفیت اتصال از اینترنت ایران. این دو در بخش «آزمایش نهایی» پایین آمده‌اند.

## ۱. سرور

| | حداقل | توصیه‌شده |
|---|---|---|
| CPU و رم | ۲ هسته، ۴GB (حدود ۲۰ تا ۳۰ نفر) | ۴ هسته، ۸GB |
| پهنای باند | حدود ۳ تا ۵ مگابیت برای هر نفر با ویدیو؛ کلاسی که فقط ویدیوی استاد روشن است خیلی کمتر مصرف می‌کند | ۱Gbps با ترافیک کافی |
| پورت‌ها | `443/tcp` و **`10000/udp`** (صوت و تصویر). بدون UDP، کلاس وصل می‌شود ولی تصویر نمی‌آید. | |
| دامنه | مثلاً `meet.SITE_HOST`، با یک رکورد A به IP همین سرور | |

یک سرور Jitsi می‌تواند بین چند مدرس مشترک باشد. هر سایت فقط اتاق‌های خودش را با توکن خودش باز می‌کند.

## ۲. نصب

```bash
# نسخه‌ی ثابت؛ ایمیج‌ها از ghcr.io/jitsi کشیده می‌شوند (نه Docker Hub)
curl -L -o djm.tgz https://github.com/jitsi/docker-jitsi-meet/archive/refs/tags/stable-11248-3.tar.gz
tar xzf djm.tgz && cd docker-jitsi-meet-stable-11248-3
cp env.example .env
./gen-passwords.sh                              # رمزهای داخلی خود Jitsi
mkdir -p ~/.jitsi-meet-cfg/{web,transcripts,prosody/config,prosody/prosody-plugins-custom,jicofo,jvb,jigasi,jibri}
openssl rand -hex 32                            # JWT_APP_SECRET؛ آن را جای امنی نگه دارید
```

این‌ها را به `.env` اضافه کنید یا مقدارشان را عوض کنید:

```env
PUBLIC_URL=https://meet.SITE_HOST
JVB_ADVERTISE_IPS=PUBLIC_IP_OF_THIS_SERVER
TZ=Asia/Tehran
HTTP_PORT=80
HTTPS_PORT=443
ENABLE_LETSENCRYPT=1
LETSENCRYPT_DOMAIN=meet.SITE_HOST
LETSENCRYPT_EMAIL=you@example.com

# ورود فقط با توکن سایت
ENABLE_AUTH=1
AUTH_TYPE=jwt
ENABLE_GUESTS=0
JWT_ALLOW_EMPTY=0
JWT_APP_ID=amozeshyar
JWT_APP_SECRET=<همان openssl rand -hex 32>
JWT_ACCEPTED_ISSUERS=amozeshyar
JWT_ACCEPTED_AUDIENCES=jitsi

# moderator فقط از روی توکن (استاد)، نه «اولین نفری که وارد شد»
XMPP_MUC_MODULES=token_affiliation
ENABLE_AUTO_OWNER=0
```

```bash
docker compose up -d
docker compose ps        # web، prosody، jicofo و jvb باید Up باشند
```

اگر روی همین سرور nginx دیگری پورت 443 را گرفته، `HTTP_PORT` و `HTTPS_PORT` را عوض کنید (مثلاً 8000 و 8443) و `ENABLE_LETSENCRYPT=0` بگذارید. بعد در nginx برای `meet.SITE_HOST` یک proxy به `http://127.0.0.1:8000` بسازید، با پشتیبانی WebSocket برای `/xmpp-websocket` و `/colibri-ws`.

## ۳. اتصال سایت

در `deploy/.env` سایت مدرس:

```env
JITSI_DOMAIN=meet.SITE_HOST
JITSI_APP_ID=amozeshyar
JITSI_APP_SECRET=<همان JWT_APP_SECRET>
```

در `nginx.conf` سایت، `JITSI_HOST` را با `meet.SITE_HOST` جایگزین کنید. این مقدار در CSP و Permissions-Policy است و بدون آن مرورگر اجازه‌ی بارگذاری کلاس یا دسترسی به دوربین را نمی‌دهد. بعد:

```bash
nginx -t && systemctl reload nginx
bash deploy/release.sh          # تا backend متغیرهای جدید را بخواند
```

**هیچ‌وقت `JITSI_APP_SECRET` را commit نکنید.** هر کسی که آن را داشته باشد می‌تواند برای هر اتاقی توکن بسازد. اگر لو رفت، در هر دو طرف عوضش کنید.

## ۴. آزمایش نهایی (در مرورگر)

1. استاد در پنل یک جلسه‌ی آنلاین می‌سازد و وارد کلاس می‌شود. باید به‌عنوان moderator وارد شود و بتواند صدای دیگران را ببندد.
2. یک دانشجوی ثبت‌نام‌شده از «تقویم» وارد می‌شود. صدا و تصویر هر دو طرف باید کار کند. این را **با اینترنت موبایل** هم امتحان کنید.
3. یک کاربر ثبت‌نام‌نشده آدرس `/classroom/<id>` را باز می‌کند. باید پیام «دسترسی ندارید» ببیند.
4. کسی آدرس مستقیم `https://meet.SITE_HOST/<نام اتاق>` را باز می‌کند. Jitsi باید ورود را رد کند.
5. Console مرورگر نباید خطای `Content-Security-Policy` نشان دهد.

## بازگشت به حالت قبل

در `deploy/.env`، `JITSI_APP_SECRET` را خالی کنید و `JITSI_DOMAIN=meet.jit.si` بگذارید. در `nginx.conf` هم `JITSI_HOST` را `meet.jit.si` کنید. سایت دقیقاً مثل قبل کار می‌کند (با همان قطع بعد از ۵ دقیقه). نیازی به migration نیست.

## محدودیت‌ها

- ضبط کلاس (Jibri) راه‌اندازی نشده است. سرور جدا و منابع زیادی لازم دارد.
- کیفیت اتصال، به‌خصوص UDP روی اینترنت ایران، باید در آزمایش نهایی سنجیده شود.
- توکن یک ساعت اعتبار دارد و فقط هنگام ورود بررسی می‌شود. کلاس طولانی‌تر قطع نمی‌شود، ولی ورود دوباره از سایت یک توکن تازه می‌گیرد.
