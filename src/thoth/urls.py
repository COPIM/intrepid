from django.urls import path

from thoth import views

urlpatterns = [
    path("", views.all_books, name="all_books"),
    path("book/<int:book_id>/", views.book, name="book"),
    path("search/", views.advanced_search, name="advanced_search"),
    path("ror/<int:ror_id>/", views.books_by_ror, name="books_by_ror"),
    path("ror_ajax/", views.ror_ajax, name="ror_ajax"),
    path("sync/", views.driver, name="thoth_driver"),
    path("saved_searches/", views.saved_searches, name="saved_searches"),
    path(
        "delete_search/<int:search_id>/",
        views.delete_search,
        name="delete_search",
    ),
    path(
        "run_search/<int:search_id>/",
        views.run_search,
        name="run_search",
    ),
    path(
        "toggle_email/<int:search_id>/",
        views.toggle_email,
        name="toggle_search_email",
    ),
]
