"""Seed SiteText for the documents-table "Clear filters" control.

Covers user-requested item 4c: a link beside "Filter" on both the Provider
and OBC document-list filter forms that resets the query string and shows
the unfiltered list.
"""

from django.db import migrations

PORTAL_TEXT = {
    "portal_clear_filter": (
        "Clear filters",
        "Label for the button/link that resets the document list filters.",
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
        ("portal", "0012_rename_contract_add_other"),
    ]

    operations = [migrations.RunPython(seed, unseed)]
