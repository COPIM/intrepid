"""Seed SiteText for the login form's username-field label.

The client wants the login page to say "Email address" above the
username box instead of the AuthenticationForm's default "Username"
label. Routing the label through a SiteText keeps it editable and
translatable like the rest of the login page copy.
"""

from django.db import migrations

LOGIN_TEXT = {
    "login_username_label": (
        "Email address",
        "Label shown above the username box on the login form.",
    ),
}


def seed(apps, schema_editor):
    SiteText = apps.get_model("cms", "SiteText")
    for key, (body, help_text) in LOGIN_TEXT.items():
        SiteText.objects.get_or_create(
            key=key,
            defaults={"body": body, "body_en": body, "help_text": help_text},
        )


def unseed(apps, schema_editor):
    SiteText = apps.get_model("cms", "SiteText")
    SiteText.objects.filter(key__in=LOGIN_TEXT.keys()).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("cms", "0044_add_basket_message_site_texts"),
    ]

    operations = [migrations.RunPython(seed, unseed)]
