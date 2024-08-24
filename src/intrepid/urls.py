import debug_toolbar
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from intrepid import views
from package import manage_views, order_management

urlpatterns = [
    path("", views.index, name="site_index"),
    path("test/", views.test_index, name="test_index"),
    path("who/", views.who_we_are, name="who_we_are"),
    path("admin/", admin.site.urls),
    path("view/", include("summary.urls")),
    path("backups/", include("backup.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("accounts/", include("accounts.urls")),
    path("initiatives/", include("initiatives.urls")),
    path("packages/", include("package.urls")),
    path("summernote/", include("django_summernote.urls")),
    path("cms/", include("cms.urls")),
    path("mail/", include("mail.urls")),
    path("access/", include("access.urls")),
    path("invoicing/", include("invoicing.urls")),
    path(
        "export/csv/<str:target>/",
        views.export,
        name="export_csv",
    ),
    path(
        "manage/initiative/<int:initiative>/package/<int:package_id>/",
        manage_views.manage_package,
        name="manage_package",
    ),
    path(
        "manage/initiative/<int:initiative>/banding_typ/select/",
        manage_views.start_package,
        name="start_package",
    ),
    path(
        "manage/initiative/<int:initiative>/banding_type/"
        "<int:banding_type_id>/package/new/",
        manage_views.create_package,
        name="create_package",
    ),
    path(
        "manage/meta_packages/",
        manage_views.list_meta_packages,
        name="list_meta_packages",
    ),
    path(
        "manage/meta_package/create/",
        manage_views.manage_meta_package,
        name="create_meta_package",
    ),
    path(
        "manage/meta_package/<int:package_id>/manage/",
        manage_views.manage_meta_package,
        name="manage_meta_package",
    ),
    # Order URLs
    path("orders/", order_management.order_list, name="order_list"),
    path(
        "orders/<int:order_id>/",
        order_management.order_detail,
        name="order_detail",
    ),
    path(
        "orders/<int:order_id>/edit/",
        order_management.order_edit_create,
        name="order_edit",
    ),
    path(
        "orders/create/",
        order_management.order_edit_create,
        name="order_create",
    ),
    path(
        "orders/<int:order_id>/add_package/",
        order_management.order_add_package,
        name="order_add_package",
    ),
    path(
        "orders/<int:order_id>/image/add/",
        order_management.order_add_image,
        name="order_add_image",
    ),
    path(
        "orders/<int:order_id>/image/<int:image_id>/serve/",
        order_management.order_serve_image,
        name="order_serve_image",
    ),
    # Initiative order urls
    path(
        "orders/initiative/<int:initiative>/",
        order_management.initiative_order_list,
        name="initiative_order_list",
    ),
    path(
        "orders/initiative/<int:initiative>/new/",
        order_management.initiative_order_create,
        name="initiative_order_create",
    ),
    path(
        "orders/initiative/<int:initiative>/order/<int:order_id>/",
        order_management.initiative_order_detail,
        name="initiative_order_detail",
    ),
    path(
        "orders/initiative/<int:initiative>/order/<int:order_id>/edit/",
        order_management.initiative_order_create,
        name="initiative_order_edit",
    ),
    path(
        "orders/initiative/<int:initiative>/order/<int:order_id>/add_package/",
        order_management.order_add_package,
        name="initiative_order_add_package",
    ),
    path("api/", include("api.urls")),
    path("books/", include("thoth.urls")),
    path("manage/vocabs/", include("vocab.urls")),
    path("nav/<str:page_name>", views.nav, name="nav"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += (path("__debug__/", include(debug_toolbar.urls)),)
