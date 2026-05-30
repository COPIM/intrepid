"""
Signal wiring for the portal.

Creating a ``Document`` enqueues notifications for the owning Provider's
contacts, unless the document was created by a silent bulk import (the importer
sets ``_bulk_import_silent`` on the instance). Deletion is handled by the
``NotificationQueue`` foreign-key cascade.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from portal import notifications
from portal.models import Document


@receiver(post_save, sender=Document)
def enqueue_document_notifications(sender, instance, created, **kwargs):
    if created and not getattr(instance, "_bulk_import_silent", False):
        notifications.enqueue_for_document(instance)
