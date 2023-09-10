import debug_toolbar
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include

from backup import views

urlpatterns = [
    path("list/", views.list_backups, name="list_backups"),
    path(
        "download/<str:backup_type>/version/<str:version_id>/",
        views.download_backup,
        name="download_backup",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += (path("__debug__/", include(debug_toolbar.urls)),)
