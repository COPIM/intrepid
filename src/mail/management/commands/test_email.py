from django.core.management.base import BaseCommand

from mail import models


class Command(BaseCommand):
    """
    A management command that sends a test email
    """

    help = "Sends a test email"

    def handle(self, *args, **options):
        email = models.EmailTemplate()
        email.body = (
            "<h1>Hello</h1><p>If you are reading this, then "
            "Intrepid's email system is working.</p>"
        )
        json_response = email.send(
            to="martin@martineve.com",
            subject="A Test Email from Intrepid",
            context={},
        )

        print(json_response["id"])
