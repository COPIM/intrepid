from django.urls import path

from vocab import views

urlpatterns = [
    path("bandings/", views.vocab_list, name="vocab_list"),
    path("banding/add/", views.vocab_new, name="vocab_new"),
    path(
        "banding/<int:vocab_to_edit>/edit/", views.vocab_new, name="vocab_edit"
    ),
    path(
        "banding/<int:vocab_id>/delete/",
        views.vocab_delete,
        name="vocab_delete",
    ),
    path("standards/", views.standards_vocab_list, name="standards_vocab_list"),
    path("standards/add/", views.standard_new, name="standard_new"),
    path(
        "standard/<int:vocab_to_edit>/edit/",
        views.standard_new,
        name="standard_edit",
    ),
    path(
        "standard/<int:vocab_id>/delete/",
        views.standard_delete,
        name="standard_delete",
    ),
    path("subjects/", views.subjects, name="subjects"),
    path("subjects/new/", views.new_edit_subject, name="new_subject"),
    path(
        "subjects/<int:subject_id>/",
        views.new_edit_subject,
        name="edit_subject",
    ),
]
