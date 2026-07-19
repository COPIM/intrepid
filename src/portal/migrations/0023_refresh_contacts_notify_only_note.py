"""Correct the stale "contacts cannot sign in" SiteText copy.

0011_portal_contact_user_split seeded ``portal_contacts_notify_only_note``
claiming Contacts "cannot sign in to the portal". Since the three-tier
permission model, invited Contacts CAN sign in to view and download their
Provider's documents -- they just cannot manage users or contacts. Overwrite
the row's body/body_en/body_de with corrected copy.
"""

from django.db import migrations

NOTE_KEY = "portal_contacts_notify_only_note"

BODY_EN = (
    "Contacts receive email notifications about documents. Once they accept "
    "an invitation they can sign in to view and download this Provider's "
    "documents, but they cannot manage users or contacts. To give someone "
    "full management access, add them as a User on the Manage Users page."
)

BODY_DE = (
    "Kontakte erhalten E-Mail-Benachrichtigungen zu Dokumenten. Nach "
    "Annahme ihrer Einladung können sie sich anmelden, um die "
    "Dokumente dieses Anbieters einzusehen und herunterzuladen; sie "
    "können jedoch weder Benutzer noch Kontakte verwalten. Um "
    "jemandem vollen Verwaltungszugriff zu geben, fügen Sie ihn auf "
    'der Seite „Benutzer verwalten" als Benutzer hinzu.'
)


def refresh_contacts_notify_only_note(apps, schema_editor):
    SiteText = apps.get_model("cms", "SiteText")
    SiteText.objects.filter(key=NOTE_KEY).update(
        body=BODY_EN, body_en=BODY_EN, body_de=BODY_DE
    )


def noop_reverse(apps, schema_editor):
    """Deliberately a no-op -- see module docstring / migration 0019 for the
    same reasoning: the pre-refresh copy isn't recorded anywhere, so a
    faithful reverse can't restore it, and restoring the old (wrong) English
    copy unconditionally on reverse risks clobbering later edits.
    """


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0022_portal_details_text"),
    ]

    operations = [
        migrations.RunPython(refresh_contacts_notify_only_note, noop_reverse)
    ]
