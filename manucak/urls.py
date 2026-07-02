"""
URL configuration for manucak project.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve as media_serve

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("cafe.urls")),
]

# Media (ürün görselleri, QR kodları) — hem yerelde hem canlıda sunulur
urlpatterns += [
    re_path(r"^media/(?P<path>.*)$", media_serve, {"document_root": settings.MEDIA_ROOT}),
]

# Statikler: yerelde Django dev sunucusu, canlıda WhiteNoise sunar
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.BASE_DIR / "cafe" / "static")
