"""Shared test helpers for the portal test suite."""


def clear_seed_data():
    """Remove rows created by the 0004 seed data migration.

    The seed populates starter document types, the OBC Team / Provider Members
    groups and the email templates so the live portal works out of the box.
    Tests build their own fixtures, so they start from a clean baseline to
    avoid unique-name clashes with the seeded rows.
    """
    from django.contrib.auth.models import Group
    from mail.models import EmailTemplate

    from portal.models import DocumentType

    DocumentType.objects.all().delete()
    EmailTemplate.objects.all().delete()
    Group.objects.filter(
        name__in=["OBC Team", "Provider Members"]
    ).delete()
