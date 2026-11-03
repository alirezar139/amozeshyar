package site.modaresyar.app;

import android.app.DownloadManager;
import android.content.Context;
import android.net.Uri;
import android.os.Bundle;
import android.os.Environment;
import android.view.WindowManager;
import android.webkit.CookieManager;
import android.webkit.URLUtil;
import android.webkit.WebView;
import android.widget.Toast;
import androidx.activity.OnBackPressedCallback;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {

    private FullscreenChromeClient chromeClient;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Course videos are stream-only: keep them (and exams) out of
        // screenshots, screen recordings and the recent-apps thumbnail.
        getWindow().setFlags(WindowManager.LayoutParams.FLAG_SECURE, WindowManager.LayoutParams.FLAG_SECURE);

        WebView webView = bridge.getWebView();

        // Capacitor's own client cancels fullscreen right away, which breaks
        // the video player's fullscreen button.
        OnBackPressedCallback exitFullscreen = new OnBackPressedCallback(false) {
            @Override
            public void handleOnBackPressed() {
                chromeClient.exitFullscreen();
            }
        };
        chromeClient = new FullscreenChromeClient(bridge, exitFullscreen::setEnabled);
        webView.setWebChromeClient(chromeClient);
        // Registered after the plugins' own back handler, so it wins while a video is fullscreen.
        getOnBackPressedDispatcher().addCallback(this, exitFullscreen);

        webView.setDownloadListener((url, userAgent, contentDisposition, mimeType, contentLength) ->
            download(url, userAgent, contentDisposition, mimeType)
        );
    }

    /** Lesson files: the site navigates to a signed link, which a WebView ignores unless handed to the system. */
    private void download(String url, String userAgent, String contentDisposition, String mimeType) {
        String fileName = URLUtil.guessFileName(url, contentDisposition, mimeType);
        DownloadManager.Request request = new DownloadManager.Request(Uri.parse(url))
            .setMimeType(mimeType)
            .addRequestHeader("User-Agent", userAgent)
            .setTitle(fileName)
            .setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
            .setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, fileName);
        String cookies = CookieManager.getInstance().getCookie(url);
        if (cookies != null) {
            request.addRequestHeader("Cookie", cookies);
        }
        ((DownloadManager) getSystemService(Context.DOWNLOAD_SERVICE)).enqueue(request);
        Toast.makeText(this, "دانلود شروع شد: " + fileName, Toast.LENGTH_SHORT).show();
    }
}
