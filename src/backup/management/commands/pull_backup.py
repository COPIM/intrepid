from pathlib import Path

import boto3
from django.conf import settings
from django.core.management.base import BaseCommand
from rich import print


class Command(BaseCommand):
    """
    Installs cron tasks.
    """

    help = "Pulls a specific backup from the S3 store"

    def add_arguments(self, parser):
        parser.add_argument("--backup-version")
        parser.add_argument("--out-file")
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

        s3.download_file(
            Filename=options.get("out_file"),
            Bucket=settings.BACKUP_BUCKET,
            Key=options.get("remote_key"),
            ExtraArgs={"VersionId": options.get("backup_version")},
        )

        print(
            "Saved version {} of {} to {}".format(
                options.get("backup_version"),
                options.get("remote_key"),
                Path(options.get("out_file")),
            )
        )
