import datetime

import requests
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import models
from django.template import Template, Context
from django.utils.html import strip_tags

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

        if settings.DEBUG:
            print(f"Sending email with subject {subject} to {to}.")
            print(html)

        if not settings.USE_MAILGUN:
            msg = EmailMultiAlternatives(
                subject, strip_tags(html), from_email, to
            )
            msg.attach_alternative(html, "text/html")

            return msg.send()
        else:
            mailgun_attachments = []
            for attachment in attachments:
                mailgun_attachments.append(
                    ("attachment", open(attachment, "rb"))
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

            json_response = response.json()
            if settings.DEBUG:
                print(json_response)

            try:
                EmailTemplate._create_email_log(
                    to=to,
                    subject=subject,
                    html=html,
                    message_id=json_response["id"],
                    from_email=settings.FROM_EMAIL,
                )

                return json_response
            except KeyError:
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
