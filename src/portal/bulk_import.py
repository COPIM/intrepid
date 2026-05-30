"""
Bulk-import pipeline.

OBC uploads a ZIP whose folders follow the ``<short_code>/YYYY-MM/<anything>``
convention. Only the folder structure matters — the leaf filename can be
anything. Parsing is a dry run that classifies every file (ok / skipped /
error / duplicate) for review; committing then creates ``Document`` rows from
the rows marked ``ok``.
"""

import dataclasses
import os
import re
import zipfile
from datetime import date

from django.core.files.base import ContentFile
from django.utils import timezone

from initiatives.models import Initiative
from portal.models import (
    BulkImportJob,
    BulkImportRow,
    Document,
    DocumentType,
)

BULK_PATH_RE = re.compile(
    r"^(?P<short_code>[A-Za-z0-9]{1,4})/"
    r"(?P<year>\d{4})-(?P<month>\d{2})/"
    r".+\.(?:pdf|docx?|xlsx?|csv)$",
    re.IGNORECASE,
)


@dataclasses.dataclass
class ParsedRow:
    archive_path: str
    original_filename: str
    short_code: str
    initiative: object
    reporting_month: object
    document_type: object
    status: str
    message: str


def _default_document_type():
    return (
        DocumentType.objects.filter(default=True).order_by("ordering").first()
        or DocumentType.objects.order_by("ordering").first()
    )


def _classify(archive_path, default_type):
    basename = os.path.basename(archive_path)
    if not basename or basename.startswith(".") or "__MACOSX" in archive_path:
        return None  # directory entry or system junk — ignore entirely

    match = BULK_PATH_RE.match(archive_path)
    if not match:
        return ParsedRow(
            archive_path=archive_path,
            original_filename=basename,
            short_code="",
            initiative=None,
            reporting_month=None,
            document_type=None,
            status="skipped",
            message="Unrecognised folder structure or file type.",
        )

    short_code = match.group("short_code")
    initiative = Initiative.objects.filter(
        short_code__iexact=short_code
    ).first()
    if initiative is None:
        return ParsedRow(
            archive_path=archive_path,
            original_filename=basename,
            short_code=short_code,
            initiative=None,
            reporting_month=None,
            document_type=default_type,
            status="skipped",
            message="No Provider with short code '{0}'.".format(short_code),
        )

    try:
        reporting_month = date(
            int(match.group("year")), int(match.group("month")), 1
        )
    except ValueError:
        return ParsedRow(
            archive_path=archive_path,
            original_filename=basename,
            short_code=short_code,
            initiative=initiative,
            reporting_month=None,
            document_type=default_type,
            status="error",
            message="Invalid reporting month {0}-{1}.".format(
                match.group("year"), match.group("month")
            ),
        )

    is_duplicate = Document.objects.filter(
        initiative=initiative,
        reporting_month=reporting_month,
        original_filename=basename,
    ).exists()

    return ParsedRow(
        archive_path=archive_path,
        original_filename=basename,
        short_code=short_code,
        initiative=initiative,
        reporting_month=reporting_month,
        document_type=default_type,
        status="duplicate" if is_duplicate else "ok",
        message="Already imported." if is_duplicate else "",
    )


def parse_zip(zip_file):
    """Classify every file in ``zip_file`` (a path or file-like) for review."""
    default_type = _default_document_type()
    rows = []
    with zipfile.ZipFile(zip_file) as archive:
        for name in archive.namelist():
            if name.endswith("/"):
                continue  # directory entry
            parsed = _classify(name, default_type)
            if parsed is not None:
                rows.append(parsed)
    return rows


def stage_job(zip_file, user=None, notify_on_commit=False, original_filename=""):
    """Persist an uploaded ZIP and its parsed rows for later confirmation."""
    job = BulkImportJob.objects.create(
        zip_file=zip_file,
        uploaded_by=user,
        notify_on_commit=notify_on_commit,
        original_filename=original_filename or getattr(zip_file, "name", ""),
    )
    for parsed in parse_zip(job.zip_file.path):
        BulkImportRow.objects.create(
            job=job,
            archive_path=parsed.archive_path,
            original_filename=parsed.original_filename,
            short_code=parsed.short_code,
            initiative=parsed.initiative,
            document_type=parsed.document_type,
            reporting_month=parsed.reporting_month,
            status=parsed.status,
            message=parsed.message,
        )
    return job


def commit_job(job):
    """Create ``Document`` rows from the job's ``ok`` rows. Returns the count.

    Historical imports default to silent (``notify_on_commit=False``); the
    per-document silent flag suppresses the notification-enqueue signal.
    """
    if job.committed_at:
        return 0

    created = 0
    with zipfile.ZipFile(job.zip_file.path) as archive:
        rows = job.rows.filter(status="ok").select_related(
            "initiative", "document_type"
        )
        for row in rows:
            data = archive.read(row.archive_path)
            document = Document(
                initiative=row.initiative,
                document_type=row.document_type,
                reporting_month=row.reporting_month,
                original_filename=row.original_filename,
                uploaded_by=job.uploaded_by,
            )
            if not job.notify_on_commit:
                document._bulk_import_silent = True
            document.file.save(
                row.original_filename, ContentFile(data), save=False
            )
            document.save()
            created += 1

    job.committed_at = timezone.now()
    job.save()
    return created
