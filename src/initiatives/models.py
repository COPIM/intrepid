import os
from uuid import uuid4

from django.contrib.auth.models import User
from django.db import models
from django_bleach.models import BleachField


def profile_images_upload_path(instance, filename):
    """
    Upload path for initiative profile images.
    :param instance: unused
    :param filename: the filename of the uploaded file
    :return: a new filename
    """
    try:
        filename = str(uuid4()) + "." + str(filename.split(".")[1])
    except IndexError:
        filename = str(uuid4())

    path = "profile/images/"
    return os.path.join(path, filename)


def highlights_images_upload_path(instance, filename):
    """
    Upload path for initiative highlights images.
    :param instance: unused
    :param filename: the filename of the uploaded file
    :return: a new filename
    """
    try:
        filename = str(uuid4()) + "." + str(filename.split(".")[1])
    except IndexError:
        filename = str(uuid4())

    path = "highlights/"
    return os.path.join(path, filename)


class Initiative(models.Model):
    """
    An initiative is an organisation working in the OA books space, i.e.
    a publisher or infrastructure provider
    """

    name = models.CharField(
        max_length=255,
    )
    users = models.ManyToManyField(User, blank=True, related_name="Initiatives")
    description = BleachField(
        null=True,
        help_text="Description of the initiative.",
    )
    more_info = BleachField(
        null=True,
        blank=True,
        help_text="Appears on the Initiative/Package more info page.",
    )
    active = models.BooleanField(
        default=False,
    )
    contact_email = models.EmailField(
        null=True,
        help_text="Default contact email address for this initiative.",
    )
    short_code = models.CharField(
        max_length=4,
        help_text="Four letter short code.",
        null=True,
    )

    image = models.ImageField(
        upload_to=profile_images_upload_path,
        null=True,
        blank=True,
        verbose_name="Logo image. Should be 335 x 100",
    )

    website = models.URLField(
        blank=True,
        null=True,
    )

    thoth_id = models.CharField(
        max_length=36,
        blank=True,
        null=True,
        default=None,
        verbose_name="Thoth ID "
        "(a UUID4 e.g. 9c41b13c-cecc-4f6a-a151-be4682915ef5)",
    )

    thoth_endpoint = models.URLField(
        verbose_name="A custom Thoth endpoint. You do not need to set "
        "this if using the primary Thoth server.",
        blank=True,
        null=True,
        default=None,
    )

    indexed_books = models.IntegerField(
        verbose_name="The number of books indexed by your service. If you are "
        "a publisher, leave this field at zero. If you are an "
        "index provider, like the DOAB, enter the number of books "
        "that you cover",
        default=0,
    )

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name

    def pk_str(self) -> str:
        """
        Return the primary key as a string.
        :return: string of primary key
        """
        return str(self.pk)

    def active_display(self):
        # TODO: this is not compatible with translation/multilingualism
        """
        Return a string representation of the active field.
        :return: "Yes" or "No"
        """
        if self.active:
            return "Yes"
        return "No"

    def highlights(self):
        """
        Return the highlights for this initiative.
        :return: a queryset of highlights
        """
        return Highlights.objects.filter(package__initiative=self)


class Highlights(models.Model):
    """
    Highlights for an initiative.
    """

    package = models.ForeignKey(
        "package.BasePackage",
        on_delete=models.CASCADE,
    )
    title = models.CharField(
        max_length=255,
    )
    body = BleachField()
    icon = models.ImageField(
        upload_to=highlights_images_upload_path,
        null=True,
        blank=True,
        verbose_name="Highlights images, should have a transparent background",
    )

    class Meta:
        ordering = ("pk",)
