"""Seed SiteText for the individual-upload "Send notification" checkbox.

Covers user requirement items 5/6: bulk import's "Send notifications"
defaults to ticked, and the individual upload form gains its own "Send
notification" checkbox (also ticked by default).
"""

from django.db import migrations

PORTAL_TEXT = {
    "portal_form_send_notification": (
        "Send notification",
        "Label for the individual-upload checkbox controlling whether "
        "Provider contacts are notified about the uploaded document(s).",
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
        ("portal", "0013_portal_clear_filter_text"),
    ]

    operations = [migrations.RunPython(seed, unseed)]
