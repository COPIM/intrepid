"""Seed translatable SiteText for the notification-frequency option labels."""

from django.db import migrations

PORTAL_FREQUENCY_TEXT = {
    "portal_freq_immediate": ("Immediate", "Notification frequency option."),
    "portal_freq_daily": ("Daily digest", "Notification frequency option."),
    "portal_freq_weekly": ("Weekly digest", "Notification frequency option."),
    "portal_freq_monthly": ("Monthly digest", "Notification frequency option."),
    "portal_freq_off": ("Off", "Notification frequency option."),
}


def seed(apps, schema_editor):
    SiteText = apps.get_model("cms", "SiteText")
    for key, (body, help_text) in PORTAL_FREQUENCY_TEXT.items():
        SiteText.objects.get_or_create(
            key=key,
            defaults={"body": body, "body_en": body, "help_text": help_text},
        )


def unseed(apps, schema_editor):
    SiteText = apps.get_model("cms", "SiteText")
    SiteText.objects.filter(key__in=PORTAL_FREQUENCY_TEXT.keys()).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0006_portal_form_text"),
        ("cms", "0044_add_basket_message_site_texts"),
    ]

    operations = [migrations.RunPython(seed, unseed)]
