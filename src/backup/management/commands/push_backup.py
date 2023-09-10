import filecmp
import os
import tempfile

import boto3
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """
    Installs cron tasks.
    """

    help = "Pushes the backup to the S3 store"

    def add_arguments(self, parser):
        parser.add_argument(
            "--backup-local-file", default="/home/obc/backup.sql"
        )
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

        try:
            with tempfile.TemporaryDirectory() as tmp:
                path = os.path.join(tmp, "latest")

                s3.download_file(
                    Filename=path,
                    Bucket=settings.BACKUP_BUCKET,
                    Key=options.get("remote_key"),
                )

                if filecmp.cmp(path, options.get("backup_local_file")):
                    print("Latest backup is equal to remote S3 version")
                    return
        except FileNotFoundError:
            pass
        except Exception:
            # TODO: narrow exception catching here
            pass

        s3.upload_file(
            Filename=options.get("backup_local_file"),
            Bucket=settings.BACKUP_BUCKET,
            Key=options.get("remote_key"),
        )

        print("Backup stored")
