import os
from uuid import uuid4

from django.contrib.auth.models import User
from django.core.files.storage import FileSystemStorage
from django.db import models

fs = FileSystemStorage(location="/media/")


def profile_images_upload_path(instance, filename):
    try:
        filename = str(uuid4()) + "." + str(filename.split(".")[1])
    except IndexError:
        filename = str(uuid4())

    path = "profile/images/"
    return os.path.join(path, filename)


class Profile(models.Model):
    account = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
    )
    image = models.ImageField(
        upload_to=profile_images_upload_path,
        null=True,
        blank=True,
    )
    uuid = models.UUIDField(
        default=uuid4,
        editable=False,
    )
    fte = models.PositiveIntegerField(
        default="10000",
        help_text="Please enter your institution's full time equivalent "
        "so we can calculate basket costs.",
    )
    institution = models.ForeignKey(
        "thoth.RORRecord", on_delete=models.CASCADE, null=True, blank=True
    )
    default_currency = models.ForeignKey(
        "package.Country", on_delete=models.CASCADE, null=True, blank=True
    )

    # put email preferences here
    notify_new_books = models.BooleanField(
        default=False,
        verbose_name="Receive new book "
        "notifications for "
        "your institution "
        "(this is separate to "
        "your search feed)",
    )
    notify_targeted_updates = models.BooleanField(
        default=False,
        verbose_name="Receive initiative update notifications "
        "where your institution "
        "is targeted",
    )
    notify_new_attestations = models.BooleanField(
        default=True,
        verbose_name="If you are an initiative manager you will receive "
        "updates when new Standards are created.",
    )
    activation_code = models.CharField(
        max_length=100,
        default=uuid4,
        null=True,
        blank=True,
    )

    def full_name(self):
        return "{} {}".format(
            self.account.first_name,
            self.account.last_name,
        )

    @property
    def active_baskets(self):
        return self.account.basket_set.filter(
            active=True,
        )

    def __str__(self):
        return self.full_name()


class AccountBandingChoices(models.Model):
    account = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
    )
    banding_type = models.ForeignKey(
        "package.BandingType",
        on_delete=models.CASCADE,
    )
    banding_type_vocab = models.ForeignKey(
        "vocab.BandingVocab",
        on_delete=models.CASCADE,
    )

    class Meta:
        unique_together = ("account", "banding_type")
