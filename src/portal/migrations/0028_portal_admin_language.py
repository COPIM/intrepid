"""Rename portal-facing "user" copy to "admin" and "staff" to "super admin".

The three-tier portal vocabulary is renamed for clarity:

* People who manage a Provider's portal (``initiative.users``) are now
  called "admins" everywhere in the UI ("Manage Users" becomes "Manage
  Admins", "Add a user" becomes "Add an admin", and so on). Contacts keep
  their name.
* The OBC tier that manages Providers' admins and the OBC backend is now
  called "super admins" ("Manage site staff" becomes "Manage super
  admins", the "Make staff" button becomes "Make super admin", etc.).
* The portal-homepage tile linking to the backend becomes the "Super
  Admin Dashboard".

``portal_staff_subhint`` and ``portal_tile_staff_desc`` keep the copy set
in 0025_portal_text_refresh verbatim, at the client's request.

Overwrites body/body_en/body_de following the 0023 pattern.
"""

from django.db import migrations

UPDATED_TEXT = {
    # Provider admins (initiative.users) — formerly "users"
    "portal_tile_documents_desc": {
        "en": (
            "Open a Provider to view, upload and download their documents "
            "— and manage which admins can access them."
        ),
        "de": (
            "Öffnen Sie einen Anbieter, um dessen Dokumente einzusehen, "
            "hochzuladen und herunterzuladen — und um zu verwalten, "
            "welche Admins darauf zugreifen können."
        ),
    },
    "portal_btn_manage_users": {
        "en": "Manage admins",
        "de": "Admins verwalten",
    },
    "portal_nav_users": {
        "en": "Admins",
        "de": "Admins",
    },
    "portal_users_subhint_pre": {
        "en": (
            "These admin accounts can sign in and see the Provider side "
            "of the portal for"
        ),
        "de": (
            "Diese Admin-Konten können sich anmelden und sehen die "
            "Anbieterseite des Portals für"
        ),
    },
    "portal_users_current_heading": {
        "en": "Current admins",
        "de": "Aktuelle Admins",
    },
    "portal_users_empty": {
        "en": "No admins have access to this Provider yet.",
        "de": "Bisher haben keine Admins Zugriff auf diesen Anbieter.",
    },
    "portal_users_add_heading": {
        "en": "Add an admin",
        "de": "Admin hinzufügen",
    },
    "portal_form_user_email": {
        "en": "Admin's email address",
        "de": "E-Mail-Adresse des Admins",
    },
    "portal_form_add_user": {
        "en": "Add admin",
        "de": "Admin hinzufügen",
    },
    "portal_contacts_notify_only_note": {
        "en": (
            "Contacts receive email notifications about documents. Once "
            "they accept an invitation they can sign in to view and "
            "download this Provider's documents, but they cannot manage "
            "admins or contacts. To give someone full management access, "
            "add them as an Admin on the Manage Admins page."
        ),
        "de": (
            "Kontakte erhalten E-Mail-Benachrichtigungen zu Dokumenten. "
            "Nach Annahme ihrer Einladung können sie sich anmelden, um "
            "die Dokumente dieses Anbieters einzusehen und "
            "herunterzuladen; sie können jedoch weder Admins noch "
            "Kontakte verwalten. Um jemandem vollen Verwaltungszugriff "
            "zu geben, fügen Sie ihn auf der Seite „Admins verwalten\" "
            "als Admin hinzu."
        ),
    },
    # OBC super admins — formerly "staff"
    "portal_staff_heading": {
        "en": "Manage super admins",
        "de": "Super-Admins verwalten",
    },
    "portal_staff_current_heading": {
        "en": "Current super admins",
        "de": "Aktuelle Super-Admins",
    },
    "portal_staff_empty": {
        "en": "No super admins yet.",
        "de": "Noch keine Super-Admins.",
    },
    "portal_staff_add_heading": {
        "en": "Add a super admin",
        "de": "Super-Admin hinzufügen",
    },
    "portal_staff_add_hint": {
        "en": (
            "Enter the email address of an existing account to grant "
            "them super admin access."
        ),
        "de": (
            "Geben Sie die E-Mail-Adresse eines bestehenden Kontos ein, "
            "um ihm Super-Admin-Zugriff zu gewähren."
        ),
    },
    "portal_tile_staff_title": {
        "en": "Manage super admins",
        "de": "Super-Admins verwalten",
    },
    "portal_form_staff_email": {
        "en": "Admin's email address",
        "de": "E-Mail-Adresse des Admins",
    },
    "portal_form_add_staff": {
        "en": "Make super admin",
        "de": "Zum Super-Admin machen",
    },
    # Portal-homepage backend tile
    "portal_tile_admin_dashboard_title": {
        "en": "Super Admin Dashboard",
        "de": "Super-Admin-Dashboard",
    },
}


def rename_to_admin_language(apps, schema_editor):
    SiteText = apps.get_model("cms", "SiteText")
    for key, bodies in UPDATED_TEXT.items():
        SiteText.objects.filter(key=key).update(
            body=bodies["en"], body_en=bodies["en"], body_de=bodies["de"]
        )


def noop_reverse(apps, schema_editor):
    """Deliberately a no-op -- see migration 0023 for the same reasoning:
    the pre-rename copy isn't recorded anywhere, so a faithful reverse
    can't restore it, and restoring the old copy unconditionally on
    reverse risks clobbering later edits.
    """


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0027_portal_admin_change_email"),
    ]

    operations = [
        migrations.RunPython(rename_to_admin_language, noop_reverse)
    ]
