# اپ اندروید

اپ با [Capacitor](https://capacitorjs.com) ساخته شده و سایت زنده‌ی مدرس را باز می‌کند. هر تغییری در سایت بدون انتشار نسخه‌ی جدید به اپ هم می‌رسد. هر مدرس یک APK جدا با نام و شناسه‌ی خودش می‌گیرد.

## چه چیزی اپ را از سایت در مرورگر بهتر می‌کند

| | کجا |
|---|---|
| جلوگیری از اسکرین‌شات و ضبط صفحه (ویدیوها فقط پخش آنلاین دارند) | `MainActivity.java` — `FLAG_SECURE` |
| تمام‌صفحه‌ی واقعی پخش‌کننده (افقی، بدون نوار سیستم، دکمه‌ی back از تمام‌صفحه خارج می‌شود) | `FullscreenChromeClient.java` |
| دانلود فایل‌های درس در پوشه‌ی Downloads با اعلان | `MainActivity.java` — `DownloadManager` |
| میکروفون برای ویس در چت کلاس | `AndroidManifest.xml` |
| پرداخت زرین‌پال/شاپرک داخل اپ (دانشجو واردشده برمی‌گردد)؛ بقیه‌ی لینک‌های بیرونی در مرورگر گوشی | `capacitor.config.ts` — `allowNavigation` |
| صفحه‌ی «اتصال برقرار نیست» وقتی اینترنت قطع است | `www/index.html` |

## ساخت APK

APK در GitHub Actions ساخته می‌شود ([`.github/workflows/android.yml`](../.github/workflows/android.yml)). از داخل ایران build محلی کار نمی‌کند، چون مخزن Maven گوگل (`dl.google.com`) به IP ایران جواب ۴۰۴ می‌دهد.

- **هر push که `mobile/` را تغییر دهد**، اپ پیش‌فرض (مدرس‌یار) را می‌سازد.
- **برای یک مدرس دیگر:** در GitHub ← Actions ← Android ← «Run workflow» و آدرس سایت، شناسه‌ی پکیج (مثلاً `site.ali.app`) و نام اپ را وارد کنید.

خروجی در صفحه‌ی همان اجرا، بخش Artifacts است (یک فایل zip شامل APK).

- `app-debug.apk`: برای تست روی گوشی خودتان.
- `app-release.apk`: فقط وقتی کلید امضا تنظیم شده باشد (بخش بعد). برای انتشار در مارکت‌ها همین فایل لازم است.

`versionCode` خودکار شماره‌ی اجرای workflow است و همیشه بزرگ‌تر می‌شود، همان‌طور که مارکت‌ها می‌خواهند.

## کلید امضای انتشار

یک بار بسازید و **برای همیشه نگه دارید**. اگر گم شود، دیگر نمی‌شود برای همان اپ در مارکت به‌روزرسانی منتشر کرد.

```bash
keytool -genkeypair -v -keystore release.jks -alias release -keyalg RSA -keysize 4096 -validity 10000
base64 -w0 release.jks   # خروجی را در secret زیر بگذارید
```

در GitHub ← Settings ← Secrets and variables ← Actions این چهار secret را بسازید: `ANDROID_KEYSTORE_BASE64`، `ANDROID_KEYSTORE_PASSWORD`، `ANDROID_KEY_ALIAS` (مثلاً `release`)، `ANDROID_KEY_PASSWORD`.

`keytool` همراه هر JDK نصب می‌شود.

## شناسه‌ی پکیج

`app_id` (مثلاً `site.ali.app`) بعد از اولین انتشار در مارکت **نباید عوض شود**. مارکت آن را یک اپ دیگر حساب می‌کند. برای هر مدرس یکتا باشد.

## آیکون و اسپلش

فعلاً آیکون پیش‌فرض Capacitor است. برای آیکون هر مدرس: یک لوگوی ۱۰۲۴×۱۰۲۴ در `mobile/assets/icon.png` بگذارید و `npx @capacitor/assets generate --android` را اجرا کنید.
