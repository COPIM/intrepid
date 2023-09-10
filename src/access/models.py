import uuid
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from uuid import uuid4


class Contact(models.Model):
    """
    A contact is a person who is affiliated with an initiative.
    """
    # the affiliated initiative
    initiative = models.ForeignKey(
        "initiatives.Initiative",
        on_delete=models.CASCADE,
    )

    # user's name
    name = models.CharField(
        max_length=300,
        help_text="Please enter this contact's full name.",
    )

    # user's email
    email = models.EmailField(
        max_length=255,
    )

    # an access code used to allow immediate access to signups etc.
    access_code = models.UUIDField(default=uuid.uuid4)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


def access_choices() -> tuple:
    """
    Returns the choices for the access log
    :return: a tuple of choices
    """
    return (
        ("grant", "Grant"),
        ("revoke", "Revoke"),
    )


class AccessLog(models.Model):
    """
    The access log is a record of when access was granted or revoked
    """
    signup = models.ForeignKey(
        "package.PackageSignup",
        on_delete=models.CASCADE,
    )
    access_type = models.CharField(
        choices=access_choices(),
        max_length=10,
    )
    date_stamp = models.DateTimeField(
        default=timezone.now,
    )
    ip_range = models.TextField(
        blank=True,
        null=True,
    )
    user = models.ForeignKey(
        User,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    payment_handler = models.TextField(
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ("-date_stamp",)

    def __str__(self) -> str:
        return "{} {}".format(
            self.access_type,
            self.date_stamp,
        )


class AccessLogExportCode(models.Model):
    """
    An export code is a code that can be used to export data
    """
    organisation = models.ForeignKey(
        "initiatives.Initiative",
        default=1,
        on_delete=models.CASCADE,
    )
    issued_to = models.CharField(max_length=255)
    uuid = models.UUIDField(default=uuid4)
    active = models.BooleanField(default=True)

    affiliated_email = models.EmailField(
        blank=True,
        null=True,
        max_length=255,
    )

    class Meta:
        ordering = ("-active",)


@receiver(post_save, sender=AccessLog)
def send_access_update_message(sender, instance, created, **kwargs):
    """
    This function is for OtF style presses using the access log
    It's not a functional requirement of OBC so has been postponed for v2
    """
    return

    # TODO: implement in v2

    if created:
        access_managers = Contact.objects.filter(
            contact_type="access",
            organisation=instance.signup.package.organisation,
        )

        for manager in access_managers:
            manager.send_access_message(instance)
