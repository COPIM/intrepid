from django.urls import path

from portal import views

app_name = "portal"

urlpatterns = [
    path("", views.index, name="index"),
    # OBC team
    path("obc/", views.obc_dashboard, name="obc_dashboard"),
    path(
        "obc/initiative/<int:initiative_id>/",
        views.obc_initiative_detail,
        name="obc_initiative_detail",
    ),
    path(
        "obc/initiative/<int:initiative_id>/upload/",
        views.obc_upload,
        name="obc_upload",
    ),
    path(
        "obc/initiative/<int:initiative_id>/users/",
        views.obc_manage_initiative_users,
        name="obc_initiative_users",
    ),
    path(
        "obc/initiative/<int:initiative_id>/aliases/",
        views.obc_manage_aliases,
        name="obc_initiative_aliases",
    ),
    path("obc/staff/", views.obc_manage_staff, name="obc_manage_staff"),
    path("obc/bulk-import/", views.obc_bulk_import, name="obc_bulk_import"),
    path(
        "obc/bulk-import/<int:job_id>/commit/",
        views.obc_bulk_commit,
        name="obc_bulk_commit",
    ),
    path(
        "obc/document/<int:doc_id>/edit/",
        views.obc_document_edit,
        name="obc_document_edit",
    ),
    path(
        "obc/document/<int:doc_id>/delete/",
        views.obc_document_delete,
        name="obc_document_delete",
    ),
    path(
        "obc/contact-changes/",
        views.obc_contact_changes,
        name="obc_contact_changes",
    ),
    path("obc/emails/", views.obc_emails, name="obc_emails"),
    path(
        "obc/emails/<int:queue_id>/cancel/",
        views.obc_email_cancel,
        name="obc_email_cancel",
    ),
    path(
        "obc/emails/<int:queue_id>/resend/",
        views.obc_email_resend,
        name="obc_email_resend",
    ),
    # Provider members
    path(
        "provider/",
        views.provider_initiative_picker,
        name="provider_initiative_picker",
    ),
    path(
        "provider/initiative/<int:initiative_id>/",
        views.provider_initiative_documents,
        name="provider_initiative_documents",
    ),
    path(
        "provider/initiative/<int:initiative_id>/contacts/",
        views.provider_manage_contacts,
        name="provider_manage_contacts",
    ),
    path(
        "provider/initiative/<int:initiative_id>/invite-by-email/",
        views.invite_by_email,
        name="invite_by_email",
    ),
    path(
        "provider/initiative/<int:initiative_id>/contact/"
        "<int:contact_id>/delete/",
        views.delete_contact,
        name="delete_contact",
    ),
    path(
        "provider/initiative/<int:initiative_id>/notifications/",
        views.provider_notification_prefs,
        name="provider_notification_prefs",
    ),
    path(
        "obc/contact/<int:contact_id>/invite/",
        views.send_invite,
        name="send_invite",
    ),
    # Shared
    path(
        "document/<int:doc_id>/download/",
        views.download_document,
        name="download_document",
    ),
    path("bulk-download/", views.bulk_download, name="bulk_download"),
    path(
        "invite/accept/<uuid:token>/",
        views.accept_invite,
        name="accept_invite",
    ),
]
