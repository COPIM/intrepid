"""Import SiteText translations from a CSV file.

The CSV is expected to have the columns "Key", "English", and "German".
The German column is written into the ``body_de`` modeltranslation field
of the matching :class:`cms.models.SiteText` row. Before any change is
made, a JSON snapshot of every SiteText row is written to disk so the
import can be reverted with ``--restore``.
"""

import csv
import os

from django.conf import settings
from django.core import serializers
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from cms.models import SiteText


class Command(BaseCommand):
    help = (
        "Import SiteText translations from a CSV file with Key/English/"
        "German columns, snapshotting the current state first. Use "
        "--restore <snapshot> to revert a previous import."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_path",
            nargs="?",
            default=None,
            help="Path to the CSV file of translations.",
        )
        parser.add_argument(
            "--snapshot-dir",
            default=None,
            help="Directory in which to write the pre-import snapshot "
            "(default: <BASE_DIR>/translation_snapshots).",
        )
        parser.add_argument(
            "--restore",
            default=None,
            help="Path to a snapshot JSON file to restore, instead of "
            "importing.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change without writing anything.",
        )

    def handle(self, *args, **options):
        csv_path = options["csv_path"]
        restore_path = options["restore"]

        if restore_path and csv_path:
            raise CommandError(
                "Pass either a CSV file to import or --restore, not both."
            )

        if restore_path:
            self.restore_snapshot(restore_path)
            return

        if not csv_path:
            raise CommandError(
                "Pass the path to a CSV file to import, or --restore "
                "<snapshot> to revert a previous import."
            )

        if not os.path.isfile(csv_path):
            raise CommandError(
                f"CSV file not found: {csv_path}"
            )

        self.import_csv(
            csv_path,
            snapshot_dir=options["snapshot_dir"],
            dry_run=options["dry_run"],
        )

    def import_csv(self, csv_path, snapshot_dir=None, dry_run=False):
        """
        Import German translations from the CSV into SiteText.body_de,
        snapshotting the current table state first.
        :param csv_path: path to the CSV file
        :param snapshot_dir: directory for the pre-import snapshot
        :param dry_run: if True, report without writing anything
        """
        updates = []
        missing_keys = []
        skipped_empty = 0

        with open(csv_path, newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            field_names = reader.fieldnames or []
            for required in ("Key", "German"):
                if required not in field_names:
                    raise CommandError(
                        'CSV is missing the required column "{}". Found '
                        "columns: {}".format(required, ", ".join(field_names))
                    )

            for row in reader:
                key = (row.get("Key") or "").strip()
                german = (row.get("German") or "").strip()

                if not key:
                    continue

                if not german:
                    skipped_empty += 1
                    continue

                try:
                    site_text = SiteText.objects.get(key=key)
                except SiteText.DoesNotExist:
                    missing_keys.append(key)
                    continue

                updates.append((site_text, german))

        if dry_run:
            self.report(updates, missing_keys, skipped_empty, dry_run=True)
            return

        snapshot_path = self.write_snapshot(snapshot_dir)
        self.stdout.write(
            f"Snapshot of {SiteText.objects.count()} SiteText rows written to {snapshot_path}"
        )
        self.stdout.write(
            "To revert this import, run: manage.py "
            f"import_translations_from_csv --restore {snapshot_path}"
        )

        with transaction.atomic():
            for site_text, german in updates:
                site_text.body_de = german
                site_text.save()

        self.report(updates, missing_keys, skipped_empty, dry_run=False)

    def write_snapshot(self, snapshot_dir=None):
        """
        Serialize every SiteText row to a timestamped JSON file.
        :param snapshot_dir: directory for the snapshot file
        :return: the path of the snapshot file
        """
        if snapshot_dir is None:
            snapshot_dir = os.path.join(
                settings.BASE_DIR, "translation_snapshots"
            )
        os.makedirs(snapshot_dir, exist_ok=True)

        timestamp = timezone.now().strftime("%Y%m%d-%H%M%S")
        snapshot_path = os.path.join(
            snapshot_dir, f"site_text_snapshot_{timestamp}.json"
        )

        with open(snapshot_path, "w", encoding="utf-8") as handle:
            serializers.serialize(
                "json",
                SiteText.objects.all(),
                indent=2,
                stream=handle,
            )

        return snapshot_path

    def restore_snapshot(self, snapshot_path):
        """
        Restore SiteText rows from a snapshot JSON file.
        :param snapshot_path: path to the snapshot file
        """
        if not os.path.isfile(snapshot_path):
            raise CommandError(
                f"Snapshot file not found: {snapshot_path}"
            )

        with open(snapshot_path, encoding="utf-8") as handle:
            objects = list(serializers.deserialize("json", handle.read()))

        with transaction.atomic():
            for deserialized in objects:
                deserialized.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"Restored {len(objects)} SiteText rows from {snapshot_path}"
            )
        )

    def report(self, updates, missing_keys, skipped_empty, dry_run):
        """
        Print a summary of the import.
        :param updates: list of (SiteText, german) pairs applied
        :param missing_keys: CSV keys with no matching SiteText row
        :param skipped_empty: count of rows with an empty German cell
        :param dry_run: whether this was a dry run
        """
        prefix = "Would update" if dry_run else "Updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"{prefix} {len(updates)} translation(s). Skipped {skipped_empty} row(s) with an empty "
                "German cell."
            )
        )
        if missing_keys:
            self.stdout.write(
                self.style.WARNING(
                    "Skipped {} key(s) with no matching SiteText row: "
                    "{}".format(len(missing_keys), ", ".join(missing_keys))
                )
            )
