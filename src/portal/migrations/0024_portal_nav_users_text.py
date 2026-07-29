"""Seed the SiteText label for the per-initiative "Users" sub-nav tab.

Provider managers now reach the Manage-Users page from the shared sub-nav, so
the tab needs a short, translatable label.
"""

from django.db import migrations

PORTAL_TEXT = {
    "portal_nav_users": (
        "Users",
        "Provider sub-nav label for the Manage Users page.",
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
        ("portal", "0023_refresh_contacts_notify_only_note"),
        ("cms", "0044_add_basket_message_site_texts"),
    ]

    operations = [migrations.RunPython(seed, unseed)]
