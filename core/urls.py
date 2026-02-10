from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include

urlpatterns = [
    path("api/", include(("api.routers", "api"), namespace="api")),
]

print("=" * 80)
print(f"DEBUG mode: {settings.DEBUG}")
print(f"MEDIA_URL: {settings.MEDIA_URL}")
print(f"MEDIA_ROOT: {settings.MEDIA_ROOT}")
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    print(f"Media serving configured: {settings.MEDIA_URL} -> {settings.MEDIA_ROOT}")
else:
    print("DEBUG is False - media files will NOT be served by Django")
print("=" * 80)
