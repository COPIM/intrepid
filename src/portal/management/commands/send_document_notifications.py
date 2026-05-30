from django.core.management.base import BaseCommand

from portal import notifications


class Command(BaseCommand):
    """Drain the portal notification queue (run every 15 minutes by cron)."""

    help = "Sends any pending document-portal notifications that are now due."

    def handle(self, *args, **options):
        sent = notifications.send_pending_notifications()
        print("Sent {} document notification(s).".format(sent))
