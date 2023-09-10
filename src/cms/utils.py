import _io
import io

from PIL import Image
from django.contrib.auth.models import User
from django.shortcuts import reverse
from resizeimage import resizeimage

from mail import models as mm


def resize_image(width, height, image_upload):
    """
    Resize an image to the specified width and height
    :param width: the width to resize to
    :param height: the height to resize to
    :param image_upload: the image to resize
    :return: the resized image
    """
    # Unclear why this needs the type check, but sometimes
    # img.file is an image byte array, and sometimes it's a
    # temporary file wrapper. This function handles both of those
    # eventualities

    if not image_upload:
        return image_upload

    with Image.open(image_upload.file) as image:
        cover = resizeimage.resize_cover(
            image, [width, height], Image.ANTIALIAS
        )

        if type(image_upload.file) is _io.BytesIO:
            img_byte_arr = io.BytesIO()
            cover.save(img_byte_arr, image.format, quality=100)
            image_upload.file = img_byte_arr
        else:
            cover.save(image_upload.file.name, image.format, quality=100)

    return image_upload


def send_cms_change_notification(request, initiative, page_or_update, page):
    """
    Send a notification to the platform manager that a page has been updated
    :param request: the request object
    :param initiative: the initiative that the page belongs to
    :param page_or_update: either "page" or "update"
    :param page: the page that was updated
    :return: None
    """
    template = mm.EmailTemplate.objects.get(
        name="manager_cms_update",
    )
    for manager in User.objects.filter(is_staff=True):
        context = {
            "platform_manager": manager,
            "request": request,
            "initiative": initiative,
            "url": request.build_absolute_uri(
                reverse(
                    "page_detail",
                    kwargs={
                        "initiative": initiative.pk,
                        "page_or_update": page_or_update,
                        "page_id": page.pk,
                    },
                )
            ),
        }

        template.send(
            to=manager.email,
            context=context,
        )


def send_target_institution_notification(request, page):
    """
    Send a notification to the target institution that a page has been updated
    :param request: the request object
    :param page: the page that was updated
    :return: None
    """
    page.notification_sent = True
    page.save()
    users = User.objects.filter(
        profile__institution=page.target_institution,
        profile__notify_targeted_updates=True,
    )
    email_template = mm.EmailTemplate.objects.get(
        name="new_update",
    )
    url = request.build_absolute_uri(
        reverse(
            "public_initiative_page",
            kwargs={
                "initiative_id": page.initiative.pk,
                "page_id": page.pk,
            },
        )
    )
    for user in users:
        context = {
            "user": user,
            "url": url,
            "page": page,
            "request": request,
        }
        email_template.send(
            to=user.email,
            context=context,
        )
