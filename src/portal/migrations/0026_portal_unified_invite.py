"""Refresh Manage-Users SiteText for the unified invite flow.

The Manage Users page used to offer two panels: "Add a user (existing OBC
account)" and "Invite someone by email (new person)". These are now a single
invite-by-email flow that adds an existing active account directly and
otherwise sends an invitation. Update the invite panel copy (seeded in
0011_portal_contact_user_split) and the section heading/hint (seeded in
0005_portal_site_text, whose hint referenced the two separate routes), and
delete the now-unused add-existing panel rows.
"""

from django.db import migrations

UPDATED_TEXT = {
    "portal_users_invite_heading": {
        "en": "Invite someone by email",
        "de": "Jemanden per E-Mail einladen",
    },
    "portal_users_invite_desc": {
        "en": (
            "Enter an email address. If they already have an OBC account "
            "they will be given access to this Provider straight away; "
            "otherwise we'll send them a link to set up their account and "
            "password."
        ),
        "de": (
            "Geben Sie eine E-Mail-Adresse ein. Wenn die Person bereits "
            "ein OBC-Konto hat, erhält sie sofort Zugriff auf diesen "
            "Anbieter; andernfalls senden wir ihr einen Link, über den "
            "sie ihr Konto und Passwort einrichten kann."
        ),
    },
    "portal_users_add_heading": {
        "en": "Add a user",
        "de": "Benutzer hinzufügen",
    },
    "portal_users_add_hint": {
        "en": (
            "Use the form below to give someone access to this Provider's "
            "portal."
        ),
        "de": (
            "Nutzen Sie das folgende Formular, um jemandem Zugriff auf "
            "das Portal dieses Anbieters zu geben."
        ),
    },
}

REMOVED_KEYS = [
    "portal_users_add_existing_heading",
    "portal_users_add_existing_desc",
]


def refresh_unified_invite_text(apps, schema_editor):
    SiteText = apps.get_model("cms", "SiteText")
    for key, bodies in UPDATED_TEXT.items():
        SiteText.objects.filter(key=key).update(
            body=bodies["en"], body_en=bodies["en"], body_de=bodies["de"]
        )
    SiteText.objects.filter(key__in=REMOVED_KEYS).delete()


def noop_reverse(apps, schema_editor):
    """Deliberately a no-op -- see migration 0023 for the same reasoning:
    the pre-refresh copy isn't recorded anywhere, so a faithful reverse
    can't restore it, and restoring the old copy unconditionally on reverse
    risks clobbering later edits.
    """


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0025_portal_text_refresh"),
    ]

    operations = [
        migrations.RunPython(refresh_unified_invite_text, noop_reverse)
    ]
