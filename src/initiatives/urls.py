from django.urls import path

from cms import views as cms_views
from initiatives import views

urlpatterns = [
    path("list/", views.initiative_list, name="initiative_list"),
    path(
        "<int:initiative_id>/detail/",
        views.initiative_detail,
        name="initiative_detail",
    ),
    path("create/", views.initiative_edit_or_create, name="initiative_create"),
    path(
        "<int:initiative_id>/edit/",
        views.initiative_edit_or_create,
        name="initiative_edit",
    ),
    path(
        "<int:initiative_id>/delete/",
        views.initiative_delete,
        name="initiative_delete",
    ),
    path("", views.user_initiatives, name="initiative_user_initiatives"),
    path(
        "<int:initiative>/packages/",
        views.initiative_packages,
        name="initiative_packages",
    ),
    path(
        "active_initiatives/",
        views.public_initiative_list,
        name="public_initiative_list",
    ),
    path(
        "initiative/<int:initiative_id>/",
        views.public_initiative,
        name="public_initiative",
    ),
    path(
        "initiative/<int:initiative_id>/page/<int:page_id>/",
        views.public_initiative,
        name="public_initiative_page",
    ),
    path(
        "initiative/<int:initiative_id>/pages/order/",
        cms_views.initiative_pages_order,
        name="initiative_pages_order",
    ),
]
