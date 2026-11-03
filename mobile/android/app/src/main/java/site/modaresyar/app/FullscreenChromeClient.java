package site.modaresyar.app;

import android.app.Activity;
import android.content.pm.ActivityInfo;
import android.view.View;
import android.view.ViewGroup;
import android.widget.FrameLayout;
import androidx.core.util.Consumer;
import androidx.core.view.WindowCompat;
import androidx.core.view.WindowInsetsCompat;
import androidx.core.view.WindowInsetsControllerCompat;
import com.getcapacitor.Bridge;
import com.getcapacitor.BridgeWebChromeClient;

/**
 * Real fullscreen for the site's video player (the player fullscreens its
 * wrapper element, so the watermark stays on top): the element is shown
 * over the whole window, landscape, with the system bars hidden.
 */
class FullscreenChromeClient extends BridgeWebChromeClient {

    private final Activity activity;
    private final Consumer<Boolean> onFullscreenChanged;
    private View customView;
    private CustomViewCallback customViewCallback;

    FullscreenChromeClient(Bridge bridge, Consumer<Boolean> onFullscreenChanged) {
        super(bridge);
        this.activity = bridge.getActivity();
        this.onFullscreenChanged = onFullscreenChanged;
    }

    @Override
    public void onShowCustomView(View view, CustomViewCallback callback) {
        if (customView != null) {
            callback.onCustomViewHidden();
            return;
        }
        customView = view;
        customViewCallback = callback;
        decorView().addView(
            view,
            new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT)
        );
        WindowInsetsControllerCompat bars = insetsController();
        bars.setSystemBarsBehavior(WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE);
        bars.hide(WindowInsetsCompat.Type.systemBars());
        activity.setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE);
        onFullscreenChanged.accept(true);
    }

    @Override
    public void onHideCustomView() {
        if (customView == null) {
            return;
        }
        decorView().removeView(customView);
        customView = null;
        insetsController().show(WindowInsetsCompat.Type.systemBars());
        activity.setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED);
        onFullscreenChanged.accept(false);
        // Tells the page it left fullscreen (fires its fullscreenchange).
        CustomViewCallback callback = customViewCallback;
        customViewCallback = null;
        callback.onCustomViewHidden();
    }

    /** For the back button: leave fullscreen instead of navigating away. */
    void exitFullscreen() {
        onHideCustomView();
    }

    private FrameLayout decorView() {
        return (FrameLayout) activity.getWindow().getDecorView();
    }

    private WindowInsetsControllerCompat insetsController() {
        return WindowCompat.getInsetsController(activity.getWindow(), activity.getWindow().getDecorView());
    }
}
