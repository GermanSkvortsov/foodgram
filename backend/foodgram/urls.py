"""
Головные URL-маршруты проекта foodgram.

Подключает админку, API, короткие ссылки и статические файлы.
"""

from api.views import redirect_to_recipe
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
    path("s/<str:code>/", redirect_to_recipe, name="short_link_redirect"),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
