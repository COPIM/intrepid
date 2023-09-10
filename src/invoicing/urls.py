from django.urls import path

from invoicing import views


urlpatterns = [
    path(
        "processor/<int:payment_processor_id>/",
        views.list_order_invoices,
        name="list_order_invoices",
    ),
    path(
        "processor/<int:payment_processor_id>/<int:order_id>/detail/",
        views.detail_invoice,
        name="detail_invoice",
    ),
    path(
        "initiative/<int:initiative_id>/",
        views.list_order_invoices_initiative,
        name="list_order_invoices_initiative",
    ),
    path(
        "initiative/<int:initiative_id>/<int:order_id>/detail/",
        views.detail_invoice_initiative,
        name="detail_invoice_initiative",
    ),
    path(
        "processors/",
        views.list_payment_processors,
        name="list_payment_processors",
    ),
    path(
        "processors/<int:processor_id>/edit/",
        views.edit_payment_processor,
        name="edit_payment_processor",
    ),
    path(
        "processors/new/",
        views.edit_payment_processor,
        name="new_payment_processor",
    ),
]
