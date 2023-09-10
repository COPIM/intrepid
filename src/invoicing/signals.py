from django.db.models.signals import post_save
from django.dispatch import receiver

from invoicing import models


@receiver(post_save, sender=models.SignupInvoice)
def add_log_entry(sender, instance, created, **kwargs):
    """
    When the status of an Invoice changes the log should add an entry.
    :param sender: unused
    :param instance: the invoice instance
    :param created: unused
    :param kwargs: unused
    :return:
    """
    models.InvoiceLog.objects.create(
        invoice=instance,
        status=instance.status,
    )
