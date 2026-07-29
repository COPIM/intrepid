"""Seed the starter document types, groups and email templates."""

from django.db import migrations

EMAIL_TEMPLATES = [
    (
        "document_notification_immediate",
        "A new document is available",
        "portal/emails/document_notification_immediate.html",
    ),
    (
        "document_notification_digest",
        "Your Open Book Collective document digest",
        "portal/emails/document_notification_digest.html",
    ),
    (
        "contact_change_notification",
        "Provider contact details changed",
        "portal/emails/contact_change_notification.html",
    ),
    (
        "provider_invite",
        "Your invitation to the Open Book Collective portal",
        "portal/emails/provider_invite.html",
    ),
]

DOCUMENT_TYPES = [
    {
        "name": "Remittance advice",
        "slug": "remittance-advice",
        "requires_reporting_month": True,
        "default": True,
        "ordering": 1,
    },
    {
        "name": "Agreement contract",
        "slug": "agreement-contract",
        "requires_reporting_month": False,
        "default": False,
        "ordering": 2,
    },
]

GROUPS = ["OBC Team", "Provider Members"]


def _template_body(path, fallback):
    try:
        from django.template.loader import get_template

        return get_template(path).template.source
    except Exception:
        return fallback


def seed(apps, schema_editor):
    DocumentType = apps.get_model("portal", "DocumentType")
    Group = apps.get_model("auth", "Group")
    EmailTemplate = apps.get_model("mail", "EmailTemplate")

    for data in DOCUMENT_TYPES:
        DocumentType.objects.get_or_create(
            slug=data["slug"],
            defaults={
                "name": data["name"],
                "name_en": data["name"],
                "requires_reporting_month": data["requires_reporting_month"],
                "default": data["default"],
                "ordering": data["ordering"],
            },
        )

    for name in GROUPS:
        Group.objects.get_or_create(name=name)

    for name, subject, template_path in EMAIL_TEMPLATES:
        body = _template_body(
            template_path, "<p>{{ recipient }}</p>"
        )
        EmailTemplate.objects.get_or_create(
            name=name,
            defaults={"subject": subject, "body": body},
        )


def unseed(apps, schema_editor):
    """Seeded data is intentionally left in place on reverse (idempotent)."""


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0003_auto_20260530_1006"),
        ("mail", "0001_initial"),
        ("auth", "0001_initial"),
    ]

    operations = [migrations.RunPython(seed, unseed)]
