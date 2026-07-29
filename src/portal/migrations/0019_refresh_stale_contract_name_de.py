"""Refresh a stale German label left over from the Contract rename.

0012_rename_contract_add_other renamed the "Agreement contract"
DocumentType's base ``name``/``name_en`` to "Contract" but left ``name_de``
untouched. If a deployment already had ``name_de`` set to "Agreement
contract" (or never set it at all), the German UI would keep showing the
old label. Refresh ``name_de`` to "Contract" only when it is blank or
still holds that old pre-rename value -- a deliberately-set German
translation must not be overwritten.
"""

from django.db import migrations

# Values that mean "nobody has deliberately translated this field yet" --
# safe to refresh. Anything else is assumed to be a real translation.
STALE_NAME_DE_VALUES = ("", None, "Agreement contract")


def refresh_stale_name_de(apps, schema_editor):
    DocumentType = apps.get_model("portal", "DocumentType")

    contract = DocumentType.objects.filter(slug="agreement-contract").first()
    if contract is None:
        return

    if contract.name_de in STALE_NAME_DE_VALUES:
        contract.name_de = "Contract"
        contract.save(update_fields=["name_de"])


def noop_reverse(apps, schema_editor):
    """Deliberately a no-op.

    A faithful reverse would need to know what ``name_de`` held before this
    migration ran (blank, or "Agreement contract") to restore it exactly,
    and that information isn't recorded anywhere. Restoring "Agreement
    contract" unconditionally on reverse risks clobbering a translation
    that was added after this migration ran. Leaving the refreshed value in
    place is the safer choice.
    """


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0018_portal_email_template_text"),
    ]

    operations = [
        migrations.RunPython(refresh_stale_name_de, noop_reverse)
    ]
