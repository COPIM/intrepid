"""Seed SiteText for the contact-tier "Details" pane.

A Contact-tier user sees only their own row on the contacts pane, which is
labelled "Details" for them (managers and OBC staff keep "Contacts").
"""

from django.db import migrations

PORTAL_TEXT = {
    "portal_nav_details": (
        "Details",
        "Provider sub-nav label shown to contact-tier users instead of "
        "Contacts.",
    ),
    "portal_details_heading": (
        "Your details",
        "Contacts pane heading shown to contact-tier users.",
    ),
    "portal_details_subhint": (
        "Edit your own contact details below.",
        "Contacts pane subhint shown to contact-tier users.",
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
        ("portal", "0021_portal_language_text"),
        ("cms", "0044_add_basket_message_site_texts"),
    ]

    operations = [migrations.RunPython(seed, unseed)]
