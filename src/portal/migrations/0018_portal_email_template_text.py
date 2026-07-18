"""Seed SiteText for the OBC email-template editing screens.

Adds the dashboard tile, the list-page headings and column headers, and the
edit-form labels, hint and template-safety warning for the interface that lets
OBC staff translate and edit the four portal notification emails.
"""

from django.db import migrations

PORTAL_TEXT = {
    # Dashboard tile
    "portal_tile_email_tpls_title": (
        "Email copy",
        "Title for the email-template editing tile on the portal dashboard.",
    ),
    "portal_tile_email_tpls_desc": (
        "Edit and translate the wording of the portal notification emails.",
        "Description for the email-template editing tile on the dashboard.",
    ),
    # List page
    "portal_email_tpls_title": (
        "Notification email copy",
        "Heading for the email-template list page.",
    ),
    "portal_email_tpls_hint": (
        "Edit the wording of each portal notification email. Choose a language "
        "to edit that language's version.",
        "Sub-heading hint on the email-template list page.",
    ),
    "portal_email_tpls_th_name": (
        "Template",
        "Column header for the email template's internal name.",
    ),
    "portal_email_tpls_th_subject": (
        "Subject",
        "Column header for the email template's subject line.",
    ),
    "portal_email_tpls_th_edit": (
        "Edit language",
        "Column header for the per-language edit links.",
    ),
    "portal_email_tpls_empty": (
        "There are no notification email templates.",
        "Empty-state message on the email-template list page.",
    ),
    # Edit form
    "portal_email_tpl_edit_hint": (
        "Edit the subject and body for this language, then save.",
        "Sub-heading hint on the email-template edit page.",
    ),
    "portal_email_tpl_warning": (
        "The body is a template. Keep the variable tags (for example "
        "{{ recipient }} and {{ documents }}) exactly as they are — they are "
        "replaced with real values when the email is sent. Removing or altering "
        "them will break the email.",
        "Warning shown above the email-template body field.",
    ),
    "portal_email_tpl_subject": (
        "Subject",
        "Label for the email-template subject field.",
    ),
    "portal_email_tpl_body": (
        "Body (HTML)",
        "Label for the email-template body field.",
    ),
    "portal_email_tpl_save": (
        "Save",
        "Button label to save an email template.",
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
        ("portal", "0017_portal_email_queue_text"),
    ]

    operations = [migrations.RunPython(seed, unseed)]
