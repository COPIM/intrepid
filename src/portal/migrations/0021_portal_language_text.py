"""Seed SiteText for the per-contact email-language field.

Adds the "Add a contact" form label and the read-only contacts table column
header for the new language preference, following the 0017/0018 seeding pattern.
"""

from django.db import migrations

PORTAL_TEXT = {
    "portal_form_language": (
        "Email language",
        "Label for the contact email-language field on the Add-a-contact form.",
    ),
    "portal_th_language": (
        "Email language",
        "Column header for the contact's email-language preference.",
    ),
}


def seed(apps, schema_editor):
    SiteText = apps.get_model("cms", "SiteText")
    for key, (body, help_text) in PORTAL_TEXT.items():
        SiteText.objects.get_or_create(
            key=key,
            defaults={"body": body, "body_en": body, "help_text": help_text},
        )


def unseed(apps, schema_editor):
    SiteText = apps.get_model("cms", "SiteText")
    SiteText.objects.filter(key__in=PORTAL_TEXT.keys()).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0020_providercontact_language"),
    ]

    operations = [migrations.RunPython(seed, unseed)]
