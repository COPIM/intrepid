"""Rename "Agreement contract" to "Contract" and add an "Other" document type.

Covers user-requested items 4a/4b: the "Agreement contract" DocumentType
(slug ``agreement-contract``, a stable permission key left unchanged) is
relabelled "Contract", and a new "Other" DocumentType is seeded for
uploads that do not fit an existing category.
"""

from django.db import migrations

OTHER_DEFAULTS = {
    "name": "Other",
    "name_en": "Other",
    "requires_reporting_month": False,
    "default": False,
    "ordering": 3,
}


def rename_contract_and_add_other(apps, schema_editor):
    DocumentType = apps.get_model("portal", "DocumentType")

    DocumentType.objects.filter(slug="agreement-contract").update(
        name="Contract", name_en="Contract"
    )
    DocumentType.objects.get_or_create(slug="other", defaults=OTHER_DEFAULTS)


def revert_contract_and_remove_other(apps, schema_editor):
    DocumentType = apps.get_model("portal", "DocumentType")
    Document = apps.get_model("portal", "Document")

    DocumentType.objects.filter(slug="agreement-contract").update(
        name="Agreement contract", name_en="Agreement contract"
    )

    other = DocumentType.objects.filter(slug="other").first()
    if other is not None and not Document.objects.filter(
        document_type=other
    ).exists():
        other.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0011_portal_contact_user_split"),
    ]

    operations = [
        migrations.RunPython(
            rename_contract_and_add_other, revert_contract_and_remove_other
        )
    ]
