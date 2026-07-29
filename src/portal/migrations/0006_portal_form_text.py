"""Seed translatable SiteText for portal form labels and buttons."""

from django.db import migrations

PORTAL_FORM_TEXT = {
    "portal_form_display_name": ("Display name", "Form label."),
    "portal_form_document_type": ("Document type", "Form label."),
    "portal_form_reporting_month": ("Reporting month", "Form label."),
    "portal_form_notes": ("Notes", "Form label."),
    "portal_form_save_changes": ("Save changes", "Submit button."),
    "portal_form_zip_archive": ("ZIP archive", "Form label."),
    "portal_form_notify_commit": (
        "Send notifications for these documents", "Form label."
    ),
    "portal_form_upload_preview": ("Upload and preview", "Submit button."),
    "portal_form_first_name": ("First name", "Form label."),
    "portal_form_last_name": ("Surname", "Form label."),
    "portal_form_job_title": ("Job title", "Form label."),
    "portal_form_email": ("Email address", "Form label."),
    "portal_form_position": ("Position", "Form label."),
    "portal_form_notification_frequency": (
        "Notification frequency", "Form label."
    ),
    "portal_form_save_contact": ("Save contact", "Submit button."),
    "portal_form_choose_password": ("Choose a password", "Form label."),
    "portal_form_confirm_password": ("Confirm password", "Form label."),
    "portal_form_activate": ("Activate my account", "Submit button."),
    "portal_form_user_email": ("User's email address", "Form label."),
    "portal_form_add_user": ("Add user", "Submit button."),
}


def seed(apps, schema_editor):
    SiteText = apps.get_model("cms", "SiteText")
    for key, (body, help_text) in PORTAL_FORM_TEXT.items():
        SiteText.objects.get_or_create(
            key=key,
            defaults={"body": body, "body_en": body, "help_text": help_text},
        )


def unseed(apps, schema_editor):
    SiteText = apps.get_model("cms", "SiteText")
    SiteText.objects.filter(key__in=PORTAL_FORM_TEXT.keys()).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0005_portal_site_text"),
        ("cms", "0044_add_basket_message_site_texts"),
    ]

    operations = [migrations.RunPython(seed, unseed)]
