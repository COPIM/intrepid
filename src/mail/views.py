from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from django.shortcuts import render

from mail import models
from mail.management.commands import update_email_status


@staff_member_required
def list_logs(request) -> HttpResponse:
    """
    List all email logs
    :param request: the request
    :return: the response
    """
    # set in middleware
    logs = models.EmailLog.objects.all().order_by("-date_sent")

    template = "mail/list_log_entries.html"
    context = {
        "logs": logs,
    }
    return render(
        request,
        template,
        context,
    )


@staff_member_required
def update_email_statuses(request) -> HttpResponse:
    """
    Update the email statuses
    :param request: the request
    :return: the response
    """
    update_email_status.Command.update_statuses()
    return list_logs(request)
