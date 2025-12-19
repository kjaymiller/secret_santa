from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

from events.views import HomeView


urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path(settings.ADMIN_URL, admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("events/", include("events.urls")),
]

if settings.DEBUG:
    urlpatterns += [
        path("styleguide/", TemplateView.as_view(template_name="styleguide.html"), name="styleguide"),
    ]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
