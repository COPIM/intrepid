"""Tests for the bulk-import ZIP parser and commit pipeline."""

import io
import shutil
import tempfile
import zipfile
from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from initiatives.models import Initiative
from package.models import upload_storage
from portal import bulk_import
from portal.tests._helpers import clear_seed_data
from portal.models import (
    Document,
    DocumentType,
    NotificationQueue,
    ProviderContact,
)


def make_zip(entries):
    """Build an in-memory ZIP from a {archive_path: bytes} mapping."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for path, data in entries.items():
            archive.writestr(path, data)
    buffer.seek(0)
    return buffer


class BulkImportSeedMixin:
    @classmethod
    def setUpTestData(cls):
        clear_seed_data()
        cls.punctum = Initiative.objects.create(
            name="Punctum Books", short_code="PUNC"
        )
        cls.open_initiative = Initiative.objects.create(
            name="Open Initiative", short_code="OPEN"
        )
        cls.remittance = DocumentType.objects.create(
            name="Remittance advice",
            slug="remittance",
            requires_reporting_month=True,
            default=True,
            ordering=1,
        )


class ParseZipTests(BulkImportSeedMixin, TestCase):
    def test_valid_entry_resolves_initiative_month_and_type(self):
        zip_file = make_zip({"PUNC/2024-03/whatever name.pdf": b"data"})
        rows = bulk_import.parse_zip(zip_file)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row.status, "ok")
        self.assertEqual(row.initiative, self.punctum)
        self.assertEqual(row.reporting_month, date(2024, 3, 1))
        self.assertEqual(row.document_type, self.remittance)
        self.assertEqual(row.original_filename, "whatever name.pdf")

    def test_short_code_and_extension_are_case_insensitive(self):
        zip_file = make_zip({"punc/2024-03/STATEMENT.PDF": b"data"})
        rows = bulk_import.parse_zip(zip_file)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].status, "ok")
        self.assertEqual(rows[0].initiative, self.punctum)

    def test_unknown_short_code_is_skipped(self):
        zip_file = make_zip({"ZZZZ/2024-03/file.pdf": b"data"})
        rows = bulk_import.parse_zip(zip_file)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].status, "skipped")
        self.assertIsNone(rows[0].initiative)

    def test_bad_date_is_error(self):
        zip_file = make_zip({"PUNC/2024-13/file.pdf": b"data"})
        rows = bulk_import.parse_zip(zip_file)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].status, "error")

    def test_unrecognised_path_is_skipped(self):
        zip_file = make_zip({"loose-file.pdf": b"data"})
        rows = bulk_import.parse_zip(zip_file)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].status, "skipped")

    def test_multiple_initiatives_in_one_zip(self):
        zip_file = make_zip(
            {
                "PUNC/2024-03/a.pdf": b"a",
                "OPEN/2024-03/b.pdf": b"b",
            }
        )
        rows = bulk_import.parse_zip(zip_file)
        by_initiative = {row.initiative: row for row in rows}
        self.assertIn(self.punctum, by_initiative)
        self.assertIn(self.open_initiative, by_initiative)

    def test_duplicate_is_flagged(self):
        Document.objects.create(
            initiative=self.punctum,
            document_type=self.remittance,
            reporting_month=date(2024, 3, 1),
            original_filename="dup.pdf",
        )
        zip_file = make_zip({"PUNC/2024-03/dup.pdf": b"data"})
        rows = bulk_import.parse_zip(zip_file)
        self.assertEqual(rows[0].status, "duplicate")

    def test_system_junk_is_ignored(self):
        zip_file = make_zip(
            {
                "PUNC/2024-03/real.pdf": b"data",
                "__MACOSX/PUNC/2024-03/._real.pdf": b"junk",
                ".DS_Store": b"junk",
            }
        )
        rows = bulk_import.parse_zip(zip_file)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].status, "ok")


class CommitTests(BulkImportSeedMixin, TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._orig_location = upload_storage._location
        self._point_storage(self._tmp)

    def tearDown(self):
        self._point_storage(self._orig_location)
        shutil.rmtree(self._tmp, ignore_errors=True)

    @staticmethod
    def _point_storage(location):
        upload_storage._location = location
        upload_storage.__dict__.pop("location", None)
        upload_storage.__dict__.pop("base_location", None)

    def _stage(self, entries, notify_on_commit=False):
        zip_bytes = make_zip(entries).getvalue()
        upload = SimpleUploadedFile(
            "archive.zip", zip_bytes, content_type="application/zip"
        )
        return bulk_import.stage_job(
            upload, notify_on_commit=notify_on_commit
        )

    def test_commit_creates_documents_and_no_notifications_when_silent(self):
        # A contact exists, but a silent historical import must not notify.
        ProviderContact.objects.create(
            initiative=self.punctum,
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.com",
            notification_frequency="immediate",
        )
        job = self._stage(
            {
                "PUNC/2024-03/a.pdf": b"a",
                "PUNC/2024-04/b.pdf": b"b",
            },
            notify_on_commit=False,
        )

        created = bulk_import.commit_job(job)

        self.assertEqual(created, 2)
        self.assertEqual(Document.objects.count(), 2)
        self.assertEqual(NotificationQueue.objects.count(), 0)
        job.refresh_from_db()
        self.assertIsNotNone(job.committed_at)

    def test_commit_enqueues_when_notify_requested(self):
        ProviderContact.objects.create(
            initiative=self.punctum,
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.com",
            notification_frequency="immediate",
        )
        job = self._stage(
            {
                "PUNC/2024-03/a.pdf": b"a",
                "PUNC/2024-04/b.pdf": b"b",
            },
            notify_on_commit=True,
        )

        bulk_import.commit_job(job)

        self.assertEqual(NotificationQueue.objects.count(), 2)

    def test_commit_skips_non_ok_rows(self):
        job = self._stage(
            {
                "PUNC/2024-03/a.pdf": b"a",
                "ZZZZ/2024-03/b.pdf": b"b",  # unknown short code -> skipped
            }
        )

        created = bulk_import.commit_job(job)

        self.assertEqual(created, 1)
        self.assertEqual(Document.objects.count(), 1)

    def test_commit_preserves_original_filename(self):
        job = self._stage({"PUNC/2024-03/March Statement.pdf": b"a"})
        bulk_import.commit_job(job)
        document = Document.objects.get()
        self.assertEqual(document.original_filename, "March Statement.pdf")
