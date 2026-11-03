from django.urls import path

from . import views

urlpatterns = [
    path("", views.SiteOwnerView.as_view(), name="site-owner"),
    path("android.apk", views.AndroidAppDownloadView.as_view(), name="site-android-app"),
    path("settings/", views.SiteSettingsView.as_view(), name="site-settings"),
]
