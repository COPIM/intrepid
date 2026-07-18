import contextlib
import datetime
import logging

import requests
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import models
from django.template import Template, Context
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

MESSAGE_STATUS = [
    ("no_information", "No Information"),
    ("accepted", "Sending"),
    ("delivered", "Delivered"),
    ("failed", "Failed"),
]


class EmailLog(models.Model):
    """
    A log of all emails sent through the system.
    """

    to = models.TextField(blank=True, null=True)
    from_email = models.EmailField(blank=True, null=True)
    subject = models.TextField(blank=True, null=True)
    body = models.TextField(blank=True, null=True)
    message_status = models.CharField(
        max_length=255, choices=MESSAGE_STATUS, default="no_information"
    )

    message_id = models.TextField(blank=True, null=True)
    date_sent = models.DateTimeField(default=datetime.datetime.now)


class EmailTemplate(models.Model):
    """
    A template for an email.
    """

    name = models.CharField(max_length=200)
    subject = models.CharField(max_length=200)
    body = models.TextField()

    def __str__(self):
        return self.name

    def render_email(self, context):
        """
        Render the email template with the given context.
        :param context: the context with which to render the template
        :return: the rendered email template
        """
        template = Template(self.body)
        html_content = template.render(Context(context))

        return html_content

    @staticmethod
    def _create_email_log(
        to, subject, html, message_id, from_email
    ) -> EmailLog:
        """
        Create an email log entry.
        :param to: the email recipient
        :param subject: the email subject
        :param html: the email body
        :param message_id: the email message id
        :param from_email: the email sender
        :return: the created email log entry
        """
        log_entry = EmailLog()
        log_entry.to = ",".join(to)
        log_entry.from_email = from_email
        log_entry.subject = subject
        log_entry.body = html
        log_entry.message_id = message_id
        log_entry.save()

        return log_entry

    def _send_email(
        self, to, subject, html, from_email=None, bcc=None, attachments=None
    ):
        """
        Send an email.
        :param to: the email recipient
        :param subject: the email subject
        :param html: the email body
        :param from_email: the email sender
        :param bcc: the email bcc
        :param attachments: the email attachments
        :return: the email response
        """
        if attachments is None:
            attachments = []

        if not from_email:
            from_email = settings.FROM_EMAIL

        if not subject:
            subject = self.subject

        if type(to) not in [list, tuple]:
            to = [to]

        logger.debug("Sending email with subject %r to %s.", subject, to)
        logger.debug("Email body: %s", html)

        if not settings.USE_MAILGUN:
            msg = EmailMultiAlternatives(
                subject, strip_tags(html), from_email, to
            )
            msg.attach_alternative(html, "text/html")
            for attachment in attachments:
                msg.attach_file(attachment)

            sent = msg.send()
            logger.info(
                "Sent email via Django backend to %s (sent=%s).", to, sent
            )
            return sent
        else:
            # Wrap both the attachment-opening loop and the POST in a single
            # ExitStack so that if opening a later attachment fails, every
            # handle already opened for an earlier one is still closed as
            # the exception propagates.
            with contextlib.ExitStack() as stack:
                mailgun_attachments = [
                    ("attachment", stack.enter_context(open(attachment, "rb")))
                    for attachment in attachments
                ]

                logger.debug(
                    "Posting email to Mailgun (%s) to %s.",
                    settings.MAILGUN_SERVER_NAME,
                    to,
                )
                response = requests.post(
                    settings.MAILGUN_SERVER_NAME + "/messages",
                    auth=("api", settings.MAILGUN_ACCESS_KEY),
                    files=mailgun_attachments,
                    data={
                        "from": settings.FROM_EMAIL,
                        "to": to,
                        "subject": subject,
                        "html": html,
                        "bcc": bcc,
                        "h:Reply-To": "info@openbookcollective.org",
                    },
                )

            logger.debug(
                "Mailgun HTTP status %s for email to %s.",
                response.status_code,
                to,
            )

            try:
                json_response = response.json()
            except requests.exceptions.JSONDecodeError:
                logger.error(
                    "Mailgun returned a non-JSON response (status %s) for "
                    "email to %s: %s",
                    response.status_code,
                    to,
                    response.text,
                )
                return ""

            logger.debug("Mailgun response for email to %s: %s", to, json_response)

            try:
                EmailTemplate._create_email_log(
                    to=to,
                    subject=subject,
                    html=html,
                    message_id=json_response["id"],
                    from_email=settings.FROM_EMAIL,
                )

                logger.info(
                    "Mailgun accepted email to %s (id=%s).",
                    to,
                    json_response["id"],
                )
                return json_response
            except KeyError:
                logger.error(
                    "Mailgun did NOT accept the email to %s — no message id in "
                    "response. This commonly means the recipient is not an "
                    "authorised recipient on a Mailgun sandbox domain, or the "
                    "domain/API key is wrong. Full response: %s",
                    to,
                    json_response,
                )
                return ""

    def send(
        self,
        to,
        context,
        subject=None,
        from_email=None,
        bcc=None,
        attachments=None,
    ):
        """
        Send an email.
        :param to: the email recipient
        :param context: the context with which to render the template
        :param subject: the email subject
        :param from_email: the email sender
        :param bcc: the email bcc
        :param attachments: the email attachments
        :return: the email response
        """
        if attachments is None:
            attachments = []

        html = self.render_email(context)
        return self._send_email(
            to=to,
            subject=subject,
            html=html,
            from_email=from_email,
            bcc=bcc,
            attachments=attachments,
        )
