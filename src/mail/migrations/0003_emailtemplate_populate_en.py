"""Populate the English translation columns from the untranslated fields.

When ``EmailTemplate`` gains ``django-modeltranslation`` support, reads of
``subject``/``body`` return the active language's column with a fallback to the
default language (English). Existing rows only have data in the original
``subject``/``body`` fields, so we copy that into ``subject_en``/``body_en``
(the default-language columns) wherever they are still empty. Without this,
every existing send path would render blank emails until someone re-saved each
template.

This is deliberately self-contained (rather than relying on
``manage.py update_translation_fields``) so it runs automatically as part of
``migrate`` on every deploy.

It also depends on ``portal.0004_seed`` so that, on a *fresh* database, the four
portal templates are seeded (into the untranslated ``subject``/``body`` columns,
because seed migrations use historical models without modeltranslation
descriptors) *before* this migration copies them into the English columns. On an
existing deploy the ordering is irrelevant — the seed already ran long ago.
"""

from django.db import migrations


def populate_en(apps, schema_editor):
    EmailTemplate = apps.get_model("mail", "EmailTemplate")
    for template in EmailTemplate.objects.all():
        changed = False
        if not template.subject_en:
            template.subject_en = template.subject
            changed = True
        if not template.body_en:
            template.body_en = template.body
            changed = True
        if changed:
            template.save(update_fields=["subject_en", "body_en"])


def unpopulate(apps, schema_editor):
    """Copying values back is a no-op; the source columns are untouched."""


class Migration(migrations.Migration):

    dependencies = [
        ("mail", "0002_emailtemplate_translation_fields"),
        # Ensure the portal templates are seeded before we copy them into the
        # English columns (matters only on a fresh database — see module docstring).
        ("portal", "0004_seed"),
    ]

    operations = [migrations.RunPython(populate_en, unpopulate)]
