"""Seed new portal SiteText keys and refresh the invitation email body.

Covers the responsive/contacts-toggle/manage-staff work and the
invite-by-email + confirm-email flow.
"""

from django.db import migrations

PORTAL_TEXT = {
    # Contacts edit-toggle
    "portal_contacts_add_button": ("Add contact", "Reveal the add-contact form."),
    "portal_contacts_first_name": ("First name", "Contact form placeholder."),
    "portal_contacts_last_name": ("Surname", "Contact form placeholder."),
    # Manage staff
    "portal_staff_heading": ("Manage site staff", "Heading."),
    "portal_staff_subhint": (
        "Choose which users can access the OBC backend.", "Hint."
    ),
    "portal_staff_current_heading": ("Current staff", "Section heading."),
    "portal_staff_empty": ("No staff users yet.", "Empty state."),
    "portal_staff_add_heading": ("Add a staff member", "Section heading."),
    "portal_staff_add_hint": (
        "Enter the email address of an existing user account to grant them "
        "backend access.",
        "Hint.",
    ),
    "portal_tile_staff_title": ("Manage staff", "Dashboard tile title."),
    "portal_tile_staff_desc": (
        "Choose which users can access the OBC backend.", "Tile description."
    ),
    "portal_form_staff_email": ("User's email address", "Form label."),
    "portal_form_add_staff": ("Make staff", "Submit button."),
    # Invite by email
    "portal_invite_email_heading": (
        "Invite someone by email", "Section heading."
    ),
    "portal_invite_email_hint": (
        "Just enter an email address — we'll email them a link to set up their "
        "account, and they fill in their own details when they arrive.",
        "Hint.",
    ),
    "portal_form_invite_email": ("Email address", "Form label."),
    "portal_form_invite_btn": ("Invite by email", "Submit button."),
    # Accept-invite confirm step
    "portal_invite_setup_hint": (
        "Set up your account below: tell us your name and choose a password.",
        "Accept page hint (new account).",
    ),
    "portal_invite_confirm_hint": (
        "Please confirm to accept this invitation.",
        "Accept page hint (already signed in).",
    ),
    "portal_invite_confirm_btn": ("Confirm email", "Confirm button."),
}


def seed(apps, schema_editor):
    SiteText = apps.get_model("cms", "SiteText")
    for key, (body, help_text) in PORTAL_TEXT.items():
        SiteText.objects.get_or_create(
            key=key,
            defaults={"body": body, "body_en": body, "help_text": help_text},
        )

    # Refresh the seeded invitation email body so existing installs get the
    # new "Confirm email" button + reassurance text.
    EmailTemplate = apps.get_model("mail", "EmailTemplate")
    try:
        from django.template.loader import get_template

        body = get_template(
            "portal/emails/provider_invite.html"
        ).template.source
        EmailTemplate.objects.filter(name="provider_invite").update(body=body)
    except Exception:
        pass


def unseed(apps, schema_editor):
    SiteText = apps.get_model("cms", "SiteText")
    SiteText.objects.filter(key__in=PORTAL_TEXT.keys()).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0007_portal_frequency_text"),
        ("cms", "0044_add_basket_message_site_texts"),
        ("mail", "0001_initial"),
    ]

    operations = [migrations.RunPython(seed, unseed)]
