"""Tests for the bulk-import ZIP parser and commit pipeline.

The real convention is a single ``YYYY-MM`` reporting-month folder containing
one file per Provider, named ``<date> ... - <Provider>.<ext>``. The Provider is
matched against an Initiative's name or one of its aliases.
"""

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
    InitiativeAlias,
    NotificationQueue,
    ProviderContact,
)


def report_path(provider, month="2026-04"):
    """Build a conforming archive path for a provider's monthly report."""
    return "{0}/{0} OBC Accounts Report - {1}.pdf".format(month, provider)


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
        cls.african_minds = Initiative.objects.create(name="African Minds")
        cls.obp = Initiative.objects.create(name="Open Book Publishers")
        InitiativeAlias.objects.create(initiative=cls.obp, alias="OBP")
        cls.lse = Initiative.objects.create(name="LSE Press")
        cls.remittance = DocumentType.objects.create(
            name="Remittance advice",
            slug="remittance",
            requires_reporting_month=True,
            default=True,
            ordering=1,
        )


class ParseZipTests(BulkImportSeedMixin, TestCase):
    def test_valid_entry_resolves_provider_month_and_type(self):
        zip_file = make_zip({report_path("African Minds"): b"data"})
        rows = bulk_import.parse_zip(zip_file)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row.status, "ok")
        self.assertEqual(row.initiative, self.african_minds)
        self.assertEqual(row.reporting_month, date(2026, 4, 1))
        self.assertEqual(row.document_type, self.remittance)
        self.assertEqual(
            row.original_filename,
            "2026-04 OBC Accounts Report - African Minds.pdf",
        )

    def test_alias_matches_provider(self):
        zip_file = make_zip({report_path("OBP"): b"data"})
        rows = bulk_import.parse_zip(zip_file)
        self.assertEqual(rows[0].status, "ok")
        self.assertEqual(rows[0].initiative, self.obp)

    def test_provider_and_extension_are_case_insensitive(self):
        zip_file = make_zip(
            {"2026-04/2026-04 OBC Accounts Report - oBp.PDF": b"data"}
        )
        rows = bulk_import.parse_zip(zip_file)
        self.assertEqual(rows[0].status, "ok")
        self.assertEqual(rows[0].initiative, self.obp)

    def test_unknown_provider_is_skipped(self):
        zip_file = make_zip({report_path("Nonexistent Press"): b"data"})
        rows = bulk_import.parse_zip(zip_file)
        self.assertEqual(rows[0].status, "skipped")
        self.assertIsNone(rows[0].initiative)
        self.assertIn("Nonexistent Press", rows[0].message)

    def test_non_conforming_filename_is_deferred(self):
        # The "OLD VERSION ..." file is in the month folder and names a real
        # provider, but its name does not start with the date, so it must be
        # deferred to the user rather than auto-imported.
        path = (
            "2026-04/OLD VERSION 2026-04 OBC Accounts Report - LSE Press.pdf"
        )
        rows = bulk_import.parse_zip(make_zip({path: b"data"}))
        self.assertEqual(rows[0].status, "skipped")
        self.assertIsNone(rows[0].initiative)

    def test_bad_date_is_error(self):
        path = "2026-13/2026-13 OBC Accounts Report - African Minds.pdf"
        rows = bulk_import.parse_zip(make_zip({path: b"data"}))
        self.assertEqual(rows[0].status, "error")

    def test_file_outside_month_folder_is_skipped(self):
        rows = bulk_import.parse_zip(make_zip({"loose-file.pdf": b"data"}))
        self.assertEqual(rows[0].status, "skipped")

    def test_multiple_providers_in_one_zip(self):
        zip_file = make_zip(
            {
                report_path("African Minds"): b"a",
                report_path("OBP"): b"b",
            }
        )
        rows = bulk_import.parse_zip(zip_file)
        by_initiative = {row.initiative: row for row in rows}
        self.assertIn(self.african_minds, by_initiative)
        self.assertIn(self.obp, by_initiative)

    def test_duplicate_is_flagged(self):
        Document.objects.create(
            initiative=self.african_minds,
            document_type=self.remittance,
            reporting_month=date(2026, 4, 1),
            original_filename="2026-04 OBC Accounts Report - African Minds.pdf",
        )
        rows = bulk_import.parse_zip(
            make_zip({report_path("African Minds"): b"data"})
        )
        self.assertEqual(rows[0].status, "duplicate")

    def test_system_junk_is_ignored(self):
        zip_file = make_zip(
            {
                report_path("African Minds"): b"data",
                "__MACOSX/2026-04/._x.pdf": b"junk",
                ".DS_Store": b"junk",
            }
        )
        rows = bulk_import.parse_zip(zip_file)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].status, "ok")

    def test_leading_underscore_conforming_file_resolves(self):
        # Some ZIPs contain a leading underscore before the date, e.g. from
        # export tooling that sorts underscored files first. It must parse
        # identically to the underscore-less equivalent.
        path = "2026-04/_2026-04 OBC Accounts Report - African Minds.pdf"
        rows = bulk_import.parse_zip(make_zip({path: b"data"}))
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row.status, "ok")
        self.assertEqual(row.initiative, self.african_minds)
        self.assertEqual(row.reporting_month, date(2026, 4, 1))
        self.assertEqual(
            row.original_filename,
            "_2026-04 OBC Accounts Report - African Minds.pdf",
        )

    def test_leading_underscore_non_conforming_filename_is_deferred(self):
        # A leading underscore does not excuse the rest of the naming
        # convention -- an underscore-prefixed "OLD VERSION ..." file must
        # still be deferred for manual review, not auto-imported.
        path = (
            "2026-04/_OLD VERSION 2026-04 OBC Accounts Report - "
            "LSE Press.pdf"
        )
        rows = bulk_import.parse_zip(make_zip({path: b"data"}))
        self.assertEqual(rows[0].status, "skipped")
        self.assertIsNone(rows[0].initiative)

    def test_apple_double_file_in_month_folder_is_ignored(self):
        # macOS AppleDouble resource forks (basename starting "._") must
        # never be treated as a conforming report, even though they sit
        # right next to a real one in the month folder and even though a
        # bare leading underscore is now tolerated.
        zip_file = make_zip(
            {
                report_path("African Minds"): b"data",
                "2026-04/._2026-04 OBC Accounts Report - OBP.pdf": b"junk",
            }
        )
        rows = bulk_import.parse_zip(zip_file)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].status, "ok")
        self.assertEqual(rows[0].initiative, self.african_minds)


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
        return bulk_import.stage_job(upload, notify_on_commit=notify_on_commit)

    def test_commit_creates_documents_and_no_notifications_when_silent(self):
        ProviderContact.objects.create(
            initiative=self.african_minds,
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.com",
            notification_frequency="immediate",
        )
        job = self._stage(
            {
                report_path("African Minds", "2026-03"): b"a",
                report_path("African Minds", "2026-04"): b"b",
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
            initiative=self.african_minds,
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.com",
            notification_frequency="immediate",
        )
        job = self._stage(
            {
                report_path("African Minds", "2026-03"): b"a",
                report_path("African Minds", "2026-04"): b"b",
            },
            notify_on_commit=True,
        )

        bulk_import.commit_job(job)

        self.assertEqual(NotificationQueue.objects.count(), 2)

    def test_commit_skips_non_ok_rows(self):
        job = self._stage(
            {
                report_path("African Minds"): b"a",
                report_path("Nonexistent Press"): b"b",  # unknown -> skipped
            }
        )

        created = bulk_import.commit_job(job)

        self.assertEqual(created, 1)
        self.assertEqual(Document.objects.count(), 1)

    def test_commit_preserves_original_filename(self):
        job = self._stage({report_path("African Minds"): b"a"})
        bulk_import.commit_job(job)
        document = Document.objects.get()
        self.assertEqual(
            document.original_filename,
            "2026-04 OBC Accounts Report - African Minds.pdf",
        )
