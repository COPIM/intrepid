from django.urls import path

from access import views

urlpatterns = [
    path(
        "contacts/",
        views.contact_list,
        name="contact_list",
    ),
    path(
        "contacts/create/",
        views.create_contact,
        name="create_contact",
    ),
    path(
        "contacts/<int:contact_id>/edit/",
        views.create_contact,
        name="edit_contact",
    ),
    path(
        "contacts/<int:contact_id>/delete/",
        views.delete_contact,
        name="delete_contact",
    ),
]
