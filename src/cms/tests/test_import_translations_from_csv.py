"""Behavioural tests for the import_translations_from_csv command.

The command reads a CSV of site text translations (Key / English /
German columns), writes the German column into the ``body_de``
modeltranslation field of the matching SiteText row, and snapshots the
whole SiteText table to JSON beforehand so any import can be reverted
with ``--restore``.
"""

import csv
import json
import os
import tempfile

from django.core.management import call_command
from django.test import TestCase

from cms.models import SiteText

CSV_FIELDS = ["ID", "Key", "Is Frontend?", "English", "German"]


class ImportTranslationsFromCsvTestBase(TestCase):
    def setUp(self):
        self.workdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.workdir.cleanup)
        self.snapshot_dir = os.path.join(self.workdir.name, "snapshots")

    def write_csv(self, rows, encoding="utf-8"):
        """Write CSV rows (list of dicts) and return the file path."""
        path = os.path.join(self.workdir.name, "translations.csv")
        with open(path, "w", newline="", encoding=encoding) as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
            writer.writeheader()
            for index, row in enumerate(rows, start=1):
                full_row = {"ID": str(index), "Is Frontend?": "FALSE"}
                full_row.update(row)
                writer.writerow(full_row)
        return path

    def run_command(self, *args, **kwargs):
        kwargs.setdefault("snapshot_dir", self.snapshot_dir)
        from io import StringIO

        out = StringIO()
        call_command("import_translations_from_csv", *args, stdout=out, **kwargs)
        return out.getvalue()

    def snapshot_files(self):
        if not os.path.isdir(self.snapshot_dir):
            return []
        return sorted(
            os.path.join(self.snapshot_dir, name)
            for name in os.listdir(self.snapshot_dir)
        )


class ImportBehaviourTests(ImportTranslationsFromCsvTestBase):
    def setUp(self):
        super().setUp()
        self.text = SiteText.objects.create(
            key="index_header",
            body="Hello",
            body_en="Hello",
            help_text="The index header.",
        )

    def test_german_column_is_written_to_de_field(self):
        path = self.write_csv(
            [{"Key": "index_header", "English": "Hello", "German": "Hallo"}]
        )
        self.run_command(path)
        self.text.refresh_from_db()
        self.assertEqual(self.text.body_de, "Hallo")

    def test_english_column_does_not_overwrite_existing_english(self):
        path = self.write_csv(
            [
                {
                    "Key": "index_header",
                    "English": "Different English",
                    "German": "Hallo",
                }
            ]
        )
        self.run_command(path)
        self.text.refresh_from_db()
        self.assertEqual(self.text.body_en, "Hello")
        self.assertEqual(self.text.body, "Hello")

    def test_empty_german_cell_leaves_existing_translation_alone(self):
        self.text.body_de = "Bestehende"
        self.text.save()
        path = self.write_csv(
            [{"Key": "index_header", "English": "Hello", "German": ""}]
        )
        self.run_command(path)
        self.text.refresh_from_db()
        self.assertEqual(self.text.body_de, "Bestehende")

    def test_unknown_key_is_skipped_and_reported(self):
        path = self.write_csv(
            [
                {"Key": "index_header", "English": "Hello", "German": "Hallo"},
                {"Key": "no_such_key", "English": "X", "German": "Y"},
            ]
        )
        output = self.run_command(path)
        self.text.refresh_from_db()
        self.assertEqual(self.text.body_de, "Hallo")
        self.assertIn("no_such_key", output)

    def test_utf8_bom_csv_is_handled(self):
        path = self.write_csv(
            [{"Key": "index_header", "English": "Hello", "German": "Hallo"}],
            encoding="utf-8-sig",
        )
        self.run_command(path)
        self.text.refresh_from_db()
        self.assertEqual(self.text.body_de, "Hallo")

    def test_dry_run_changes_nothing_and_writes_no_snapshot(self):
        path = self.write_csv(
            [{"Key": "index_header", "English": "Hello", "German": "Hallo"}]
        )
        self.run_command(path, dry_run=True)
        self.text.refresh_from_db()
        self.assertIsNone(self.text.body_de)
        self.assertEqual(self.snapshot_files(), [])


class SnapshotAndRestoreTests(ImportTranslationsFromCsvTestBase):
    def setUp(self):
        super().setUp()
        self.text = SiteText.objects.create(
            key="index_header",
            body="Hello",
            body_en="Hello",
            body_de="Alte Fassung",
            help_text="The index header.",
        )

    def test_snapshot_written_before_import_contains_previous_state(self):
        path = self.write_csv(
            [{"Key": "index_header", "English": "Hello", "German": "Neu"}]
        )
        self.run_command(path)
        files = self.snapshot_files()
        self.assertEqual(len(files), 1)
        with open(files[0], encoding="utf-8") as handle:
            snapshot = json.load(handle)
        records = {
            item["fields"]["key"]: item["fields"] for item in snapshot
        }
        self.assertEqual(records["index_header"]["body_de"], "Alte Fassung")

    def test_restore_reverts_an_import(self):
        path = self.write_csv(
            [{"Key": "index_header", "English": "Hello", "German": "Neu"}]
        )
        self.run_command(path)
        self.text.refresh_from_db()
        self.assertEqual(self.text.body_de, "Neu")

        snapshot_path = self.snapshot_files()[0]
        self.run_command(restore=snapshot_path)
        self.text.refresh_from_db()
        self.assertEqual(self.text.body_de, "Alte Fassung")

    def test_restore_and_csv_path_together_is_an_error(self):
        from django.core.management.base import CommandError

        path = self.write_csv([])
        with self.assertRaises(CommandError):
            self.run_command(path, restore="whatever.json")

    def test_missing_csv_path_without_restore_is_an_error(self):
        from django.core.management.base import CommandError

        with self.assertRaises(CommandError):
            self.run_command()

    def test_nonexistent_csv_file_is_an_error(self):
        from django.core.management.base import CommandError

        with self.assertRaises(CommandError):
            self.run_command(
                os.path.join(self.workdir.name, "does_not_exist.csv")
            )
