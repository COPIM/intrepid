from django.core.management.base import BaseCommand

from thoth.models import (
    WorkNotification,
)


class Command(BaseCommand):
    """
    A management command that syncs Thoth entries to the local database
    """

    help = "Notifies users of new books"

    def handle(self, *args, **options):
        """
        A management command that syncs Thoth entries to the local database
        :param args: command line arguments
        :param options: command line options
        """
        # delete any stats from the database and regenerate
        WorkNotification.notify()
