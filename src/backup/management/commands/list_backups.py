import boto3
import humanize
from django.conf import settings
from django.core.management.base import BaseCommand
from rich import print


class Command(BaseCommand):
    """
    Installs cron tasks.
    """

    help = "Lists available backups"

    def add_arguments(self, parser):
        parser.add_argument("--remote-key", default="backup.sql")

    def handle(self, *args, **options):
        """Pushes the backup to S3

        :param args: None
        :param options: None
        :return: None
        """
        s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )

        versions = s3.list_object_versions(
            Bucket=settings.BACKUP_BUCKET, Prefix=options.get("remote_key")
        )

        for item in versions["Versions"]:
            print(
                "Backup from {}: {} [{}]".format(
                    item["LastModified"],
                    item["VersionId"],
                    humanize.naturalsize(item["Size"]),
                )
            )
