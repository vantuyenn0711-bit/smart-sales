from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.views import LogoutView
from django.urls import include, path

from accounts.views import SalesLoginView
from config.views import health

urlpatterns = [
    path("health/", health, name="health"),
    path("login/", SalesLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("reports/", include("analytics.urls")),
    path("inventory/movements/", include("inventory.urls")),
    path("", include("core.urls")),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
handler403 = "config.views.error_403"
handler404 = "config.views.error_404"
handler500 = "config.views.error_500"
