import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q
from requests import Response

from mail import models


class Command(BaseCommand):
    """
    A management command that syncs Mailgun statuses to the database
    """

    help = "Syncs mailgun statuses"

    @staticmethod
    def _get_logs(message_id) -> Response:
        """
        Get the logs for a message
        :param message_id: The message id to get logs for
        :return: The logs
        """
        return requests.get(
            "{0}/events".format(settings.MAILGUN_SERVER_NAME),
            auth=("api", settings.MAILGUN_ACCESS_KEY),
            params={"message-id": message_id},
        )

    @staticmethod
    def _check_for_perm_failure(event_dict) -> bool:
        """
        Check if there is a permanent failure in the event dict
        :param event_dict: The event dict to check
        :return: True if there is a permanent failure, False otherwise
        """
        for event in event_dict.get("items"):
            severity = event.get("severity", None)
            if severity == "permanent":
                return True

        return False

    @staticmethod
    def update_statuses() -> None:
        """
        Update the statuses of all logs
        :return: None
        """
        logs = models.EmailLog.objects.filter(
            Q(message_status="no_information") | Q(message_status="accepted")
        )

        for log in logs:
            logs = Command._get_logs(
                log.message_id.replace("<", "").replace(">", "")
            )
            event_dict = logs.json()
            print("Processing ", log.message_id, "...", end="")

            events = []
            for event in event_dict.get("items"):
                events.append(event["event"])

            if "delivered" in events:
                log.message_status = "delivered"
                log.status_checks_complete = True
            elif "failed" in events:
                if Command._check_for_perm_failure(event_dict):
                    log.message_status = "failed"
                    log.status_checks_complete = True
                else:
                    log.message_status = "accepted"

            elif "accepted" in events:
                log.message_status = "accepted"

            print(" status {0}".format(log.message_status))

            log.save()

    def handle(self, *args, **options):
        Command.update_statuses()
