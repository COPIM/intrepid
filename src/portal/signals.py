"""
Signal wiring for the portal.

Creating a ``Document`` enqueues notifications for the owning Provider's
contacts, unless the caller has opted out of notifications for this save (the
bulk importer, or an individual upload with the notification checkbox
unticked, sets ``_suppress_notifications`` on the instance). Deletion is
handled by the ``NotificationQueue`` foreign-key cascade.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from portal import notifications
from portal.models import Document


@receiver(post_save, sender=Document)
def enqueue_document_notifications(sender, instance, created, **kwargs):
    if created and not getattr(instance, "_suppress_notifications", False):
        notifications.enqueue_for_document(instance)
