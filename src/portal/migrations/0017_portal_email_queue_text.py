"""Seed SiteText for the OBC email-queue management page.

Adds the dashboard tile, the table column headers, status labels, action
buttons and confirmation prompts for the page listing every notification
email (pending, sent and cancelled).
"""

from django.db import migrations

PORTAL_TEXT = {
    # Dashboard tile
    "portal_tile_emails_title": (
        "Email queue",
        "Title for the email-queue tile on the portal dashboard.",
    ),
    "portal_tile_emails_desc": (
        "Review sent and pending notification emails; cancel or re-send them.",
        "Description for the email-queue tile on the portal dashboard.",
    ),
    # Page heading
    "portal_emails_title": (
        "Notification emails",
        "Heading for the email-queue management page.",
    ),
    "portal_emails_hint": (
        "Every document-notification email, pending or already sent. Cancel a "
        "pending email to stop it going out (the document is kept), or re-send "
        "one that has already been sent.",
        "Sub-heading hint on the email-queue management page.",
    ),
    "portal_emails_empty": (
        "There are no notification emails.",
        "Empty-state message on the email-queue management page.",
    ),
    # Column headers
    "portal_th_recipient": (
        "Recipient",
        "Email-queue table column header for the recipient email address.",
    ),
    "portal_th_contact_name": (
        "Contact",
        "Email-queue table column header for the contact's name.",
    ),
    "portal_th_user": (
        "Portal user",
        "Email-queue table column header for the linked portal user.",
    ),
    "portal_th_frequency": (
        "Frequency",
        "Email-queue table column header for the notification frequency.",
    ),
    "portal_th_date": (
        "Date",
        "Email-queue table column header for the relevant date.",
    ),
    "portal_th_status": (
        "Status",
        "Email-queue table column header for the email status.",
    ),
    "portal_th_actions": (
        "Actions",
        "Email-queue table column header for the per-row actions.",
    ),
    # Status labels
    "portal_status_pending": (
        "Pending",
        "Status label for a notification email that has not yet been sent.",
    ),
    "portal_status_sent": (
        "Sent",
        "Status label for a notification email that has been sent.",
    ),
    "portal_status_cancelled": (
        "Cancelled",
        "Status label for a cancelled notification email.",
    ),
    # Actions
    "portal_email_cancel": (
        "Cancel",
        "Button label to cancel a pending notification email.",
    ),
    "portal_email_resend": (
        "Re-send",
        "Button label to re-send a sent notification email.",
    ),
    "portal_email_cancel_confirm": (
        "Cancel this pending email? The document will be kept.",
        "Confirm prompt before cancelling a pending notification email.",
    ),
    "portal_email_resend_confirm": (
        "Re-send this email now?",
        "Confirm prompt before re-sending a notification email.",
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
        ("portal", "0016_providercontact_is_login_invite"),
    ]

    operations = [migrations.RunPython(seed, unseed)]
