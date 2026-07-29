"""Seed SiteText for the admin dashboard tile on the portal homepage.

Adds a tile link to the main admin dashboard (/staff/) visible only to staff users.
"""

from django.db import migrations

PORTAL_TEXT = {
    "portal_tile_admin_dashboard_title": (
        "Admin Dashboard",
        "Title for the admin dashboard shortcut tile on the portal homepage.",
    ),
    "portal_tile_admin_dashboard_desc": (
        "Access the main configuration dashboard",
        "Description for the admin dashboard shortcut tile on the portal homepage.",
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
        ("portal", "0014_portal_send_notification_text"),
    ]

    operations = [migrations.RunPython(seed, unseed)]
