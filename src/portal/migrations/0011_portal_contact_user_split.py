"""Seed SiteText for the Contact/User split, contact deletion and the
Aliases tab.

Covers the reorganisation that distinguishes notifications-only Contacts from
portal-login Users, the new per-contact Delete action, and the relocated
Aliases tab.
"""

from django.db import migrations

PORTAL_TEXT = {
    # Aliases tab
    "portal_nav_aliases": ("Aliases", "Provider sub-nav label for aliases."),
    # Contact deletion
    "portal_contacts_delete_confirm": (
        "Delete this contact? They will stop receiving notifications.",
        "JavaScript confirm prompt before deleting a contact.",
    ),
    # Contacts-are-notifications-only clarification
    "portal_contacts_notify_only_note": (
        "Contacts only receive email notifications about documents — they "
        "cannot sign in to the portal. To give someone portal access, add "
        "them as a User on the Manage Users page instead.",
        "Note clarifying that contacts are notifications-only.",
    ),
    # Manage Users: two add panels
    "portal_users_add_existing_heading": (
        "Add a user (existing OBC account)",
        "Manage Users panel heading.",
    ),
    "portal_users_add_existing_desc": (
        "Enter the email address of someone who already has an OBC account to "
        "grant them portal access to this Provider.",
        "Manage Users panel description.",
    ),
    "portal_users_invite_heading": (
        "Invite someone by email (new person)",
        "Manage Users panel heading.",
    ),
    "portal_users_invite_desc": (
        "No account yet? Enter an email address and we'll send them a link to "
        "set up their account and password. This also grants portal access.",
        "Manage Users panel description.",
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
        ("portal", "0010_portal_alias_text"),
        ("cms", "0044_add_basket_message_site_texts"),
    ]

    operations = [migrations.RunPython(seed, unseed)]
