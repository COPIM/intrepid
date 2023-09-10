from django import dispatch
from django.db.models.signals import post_save
from django.dispatch import receiver
from django_middleware_global_request.middleware import get_request

from package import models, utils


@receiver(post_save, sender=models.PackageSignup)
def update_order_status(sender, instance, **kwargs) -> None:
    """
    When all PackageSignup objects have been approved by Org and Inits
    update the package status.

    :param sender: the sender
    :param instance: the instance
    :param kwargs: the kwargs
    :return: None
    """

    all_signups_count = models.PackageSignup.objects.filter(
        associated_order=instance.associated_order,
        status="provisional",
    ).count()
    approved_signups_count = models.PackageSignup.objects.filter(
        associated_order=instance.associated_order,
        organisation_approved__isnull=False,
        initiative_approved__isnull=False,
        status="provisional",
    ).count()

    if (all_signups_count == approved_signups_count) and all_signups_count > 0:
        instance.associated_order.status = "complete"
        instance.associated_order.save()
        utils.send_order_complete_notification(
            order=instance.associated_order,
            request=get_request(),
        )


price_cleanup_required = dispatch.Signal()
