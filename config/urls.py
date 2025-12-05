from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from events.views import HomeView


urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path(settings.ADMIN_URL, admin.site.urls),
    path("events/", include("events.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
