import os
import uuid
from pathlib import Path

import magic
from django.conf import settings
from django.contrib.auth.signals import user_logged_in
from django.core.files.storage import FileSystemStorage
from django.db import models
from django_bleach.models import BleachField

from package import models as pm


class SiteSetup(models.Model):
    """
    This is a singleton class to store site variables.
    There should only ever be one object in here
    """

    site_name = models.CharField(
        max_length=255,
        default="Open Book Collective",
        blank=True,
        null=True,
        verbose_name="Site Name",
    )
    enable_signup = models.BooleanField(
        default=True,
        help_text="Enables or Disables signup across all packages "
        "and initiatives.",
    )
    enable_meta_package_signup = models.BooleanField(
        default=True,
        help_text="Enables or Disables signup to meta (collective) packages.",
    )
    enable_individual_package_signup = models.BooleanField(
        default=True,
        help_text="Enables or Disables signup to individual "
        "(initiative) packages.",
    )
    signup_disabled_notification = BleachField(
        blank=True,
        null=True,
        default="<p>Signup is currently disabled.",
        help_text="Displayed to users when signup is disabled.",
    )
    base_copyright_notice = models.TextField(
        default="All content &copy; 2022 Open Book Collective",
        blank=True,
        null=True,
        verbose_name="Copyright statement to show in site footer",
    )
    twitter_url = models.URLField(
        blank=True, null=True, verbose_name="Twitter URL (full)"
    )
    contact_email = models.EmailField(
        blank=True, null=True, verbose_name="Platform Contact Email"
    )
    youtube_embed = models.CharField(
        blank=True,
        null=True,
        max_length=255,
        verbose_name="Youtube embed code for homepage video "
        "(e.g. //www.youtube.com/embed/Ut5_DA7Cihg)",
        default="//www.youtube.com/embed/Ut5_DA7Cihg",
    )
    last_thoth_log = models.TextField(default="")
    last_thoth_log_date = models.DateTimeField(
        default=None, blank=None, null=True
    )
    board_of_stewards_description = models.TextField(
        default="",
        blank=True,
        null=True,
        verbose_name="Description of the Board of Stewards",
    )
    membership_committee_description = models.TextField(
        default="",
        blank=True,
        null=True,
        verbose_name="Description of the Membership Committee",
    )
    management_team_description = models.TextField(
        default="",
        blank=True,
        null=True,
        verbose_name="Description of the Management Team",
    )
    secretariat_description = models.TextField(
        default="",
        blank=True,
        null=True,
        verbose_name="Description of the Secretariat",
    )
    enable_standards = models.BooleanField(
        default=True,
        help_text="If disabled standards attestation "
        "will be hidden on the frontend.",
    )
    fee_amount = models.PositiveIntegerField(
        default=5,
        help_text="Fee % added to each transaction.",
    )
    fallback_currency = models.CharField(
        max_length=3,
        default="GBP",
        help_text="This is used as a fallback if we cannot get a "
        "conversion rate for a user's currency",
    )
    enable_search_on_packages = models.BooleanField(
        default=True,
    )
    enable_your_quotes_link = models.BooleanField(
        default=True,
        help_text="If enabled a link for Your Quotes is displayed in the nav",
    )


def copy_session_baskets_to_user(sender, user, request, **kwargs):
    """
    When a user logs in, copy all their session baskets to their user account
    :param sender: the dispatcher
    :param user: the user who just logged in
    :param request: the request object
    :param kwargs: other arguments (unused)
    :return: None
    """
    pm.Basket.objects.filter(
        session_id=request.session.session_key,
    ).update(
        account=user,
        session_id=None,
    )


# wire up the signal
user_logged_in.connect(copy_session_baskets_to_user)

# setup the private image storage
private_image_storage = FileSystemStorage(
    location=os.path.join(settings.BASE_DIR, "files", "private_images")
)


def private_images_upload_path(instance, filename):
    """
    Generate a unique filename for a private image
    :param instance: unused (required by Django)
    :param filename: the original filename
    :return: a new path
    """

    try:
        filename = f"{str(uuid.uuid4())}.{Path(filename).suffix}"
    except IndexError:
        filename = str(uuid.uuid4())

    return filename


class PrivateImage(models.Model):
    """
    A private image is an image that is not publicly accessible
    """

    image = models.ImageField(
        storage=private_image_storage,
        upload_to=private_images_upload_path,
    )

    def mime(self):
        """
        Get the mime type of the image
        :return:
        """
        return magic.from_file(self.image.path, mime=True)

    def serve_image_file(self):
        """
        Serve the image file
        :return: an HttpResponse
        """

        from intrepid.utils import serve_file

        return serve_file(
            path=self.image.path, filename=self.image.name, mime=self.mime
        )
