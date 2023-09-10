from django.conf import settings
from django.shortcuts import reverse

from initiatives import models as im
from mail import models as mm
from package import models as pm


def notify_initiatives_new_vocabs(banding_type, new_vocabs, request) -> None:
    """
    Notify initiatives of new vocabs
    :param banding_type: the banding type
    :param new_vocabs: the new vocabs
    :param request: the request
    :return: None
    """
    notifications = {}
    for package in pm.Package.objects.filter(banding_type=banding_type):
        if notifications.get(package.initiative):
            notifications[package.initiative].append(package)
        else:
            notifications[package.initiative] = [package]

    email_template = mm.EmailTemplate.objects.get(
        name="initiative_new_vocab_element"
    )
    for initiative, packages in notifications.items():
        context = {
            "packages": packages,
            "new_vocabs": new_vocabs,
            "request": request,
            "initiaitve": initiative,
        }
        to = [user.email for user in initiative.users.all()]
        email_template.send(
            to,
            context,
            subject="New Banding Vocabulary",
        )


def notify_initiatives_new_standards(standard, request) -> None:
    """
    Notify initiatives of new standards
    :param standard: the standard
    :param request: the request
    :return: None
    """
    users = []

    for initiative in im.Initiative.objects.all():
        for user in initiative.users.all():
            users.append(user)

    users = set(users)
    url = request.build_absolute_uri(
        reverse(
            "dashboard_index",
        )
    )
    context = {
        "standard": standard,
        "request": request,
        "url": url,
    }
    email_template = mm.EmailTemplate.objects.get(
        name="new_standard",
    )
    email_template.send(
        to=settings.FROM_EMAIL,
        context=context,
        bcc=[user.email for user in users],
    )
