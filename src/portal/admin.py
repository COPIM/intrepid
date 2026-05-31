"""
Minimal Django admin registrations for the portal models.

The portal's primary UI is its bespoke screens; the admin is a developer
fallback for emergency database fixes only.
"""

from django.contrib import admin

from portal import models


class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "requires_reporting_month",
        "default",
        "ordering",
    )


class DocumentAdmin(admin.ModelAdmin):
    raw_id_fields = ("initiative", "document_type", "uploaded_by")
    list_display = (
        "display_name",
        "initiative",
        "document_type",
        "reporting_month",
        "uploaded_at",
    )
    list_filter = ("document_type", "initiative")
    search_fields = ("display_name", "original_filename")


class ProviderContactAdmin(admin.ModelAdmin):
    list_display = (
        "first_name",
        "last_name",
        "email",
        "initiative",
        "position",
        "notification_frequency",
        "accepted_at",
    )
    list_filter = ("initiative", "notification_frequency")
    search_fields = ("first_name", "last_name", "email")


class ContactChangeLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "initiative", "provider_contact", "actor")
    list_filter = ("initiative",)
    readonly_fields = (
        "provider_contact",
        "initiative",
        "actor",
        "field_changes",
        "created_at",
    )


class DocumentTypePermissionAdmin(admin.ModelAdmin):
    list_display = ("document_type", "group", "can_read", "can_write")
    list_filter = ("document_type", "group")


class NotificationQueueAdmin(admin.ModelAdmin):
    list_display = (
        "document",
        "recipient",
        "frequency",
        "eligible_at",
        "sent_at",
        "cancelled_at",
    )
    list_filter = ("frequency", "sent_at")
    raw_id_fields = ("document", "recipient")
    # Read-only debugging aid — the queue is managed by the app, not by hand.
    readonly_fields = (
        "document",
        "recipient",
        "eligible_at",
        "frequency",
        "sent_at",
        "cancelled_at",
    )

    def has_add_permission(self, request):
        return False


admin_list = [
    (models.DocumentType, DocumentTypeAdmin),
    (models.Document, DocumentAdmin),
    (models.ProviderContact, ProviderContactAdmin),
    (models.ContactChangeLog, ContactChangeLogAdmin),
    (models.DocumentTypePermission, DocumentTypePermissionAdmin),
    (models.NotificationQueue, NotificationQueueAdmin),
]

[admin.site.register(*registration) for registration in admin_list]
