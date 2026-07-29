"""Seed SiteText keys for the OBC Provider-alias management section."""

from django.db import migrations

PORTAL_TEXT = {
    "portal_aliases_heading": ("Alternative names (aliases)", "Section heading."),
    "portal_aliases_hint": (
        "Bulk import matches an uploaded file to a Provider by the name in its "
        "filename. Add any alternative names here — for example an abbreviation "
        "like “OBP” for Open Book Publishers — so those files are "
        "recognised too.",
        "Hint.",
    ),
    "portal_aliases_empty": ("No aliases yet.", "Empty state."),
    "portal_th_alias": ("Alias", "Table column heading."),
    "portal_form_alias": ("Alias (alternative name)", "Form label."),
    "portal_form_add_alias": ("Add alias", "Submit button."),
}

# The bulk-import convention changed from "<short_code>/YYYY-MM/" to a single
# "YYYY-MM/" month folder with the Provider's name in each filename. Refresh the
# explanatory copy on existing installs (0005 only seeds it on a fresh DB).
BODY_REFRESH = {
    "portal_bulk_body1": (
        "Upload a ZIP file containing one folder per reporting month, named "
        "<code>YYYY-MM</code> — for example <code>2026-04/</code>. Inside each "
        "month folder, put one file per Provider, named so the Provider's name "
        "comes last after a dash, e.g. "
        "<code>2026-04 OBC Accounts Report - Open Book Publishers.pdf</code>. "
        "The Provider is matched on its name <strong>or any alias</strong> you "
        "have added (so <code>OBP</code> resolves to Open Book Publishers)."
    ),
    "portal_bulk_body2": (
        "Nothing is saved until you review the preview and confirm. Anything "
        "that can't be matched — an unknown Provider name (add the Provider, or "
        "an alias, first), a bad date, or a file that doesn't follow the naming "
        "convention — is listed for you to review, and is never imported "
        "silently."
    ),
}


def seed(apps, schema_editor):
    SiteText = apps.get_model("cms", "SiteText")
    for key, (body, help_text) in PORTAL_TEXT.items():
        SiteText.objects.get_or_create(
            key=key,
            defaults={"body": body, "body_en": body, "help_text": help_text},
        )
    for key, body in BODY_REFRESH.items():
        SiteText.objects.filter(key=key).update(body=body, body_en=body)


def unseed(apps, schema_editor):
    SiteText = apps.get_model("cms", "SiteText")
    SiteText.objects.filter(key__in=PORTAL_TEXT.keys()).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0009_initiativealias"),
        ("cms", "0044_add_basket_message_site_texts"),
    ]

    operations = [migrations.RunPython(seed, unseed)]
