"""
Bulk-import pipeline.

OBC uploads a ZIP laid out as a single reporting-month folder containing one
PDF per Provider, named so the Provider's name is the last ` - `-separated part
of the filename::

    2026-04/2026-04 OBC Accounts Report - African Minds.pdf
    2026-04/2026-04 OBC Accounts Report - OBP.pdf

* the top-level folder ``YYYY-MM`` is the reporting month;
* the Provider is the text after the final ` - ` in the filename, matched
  (case-insensitively) against an Initiative's **name or one of its aliases**
  (so ``OBP`` resolves to *Open Book Publishers*);
* the filename must start with the report date — anything else (e.g. an
  ``OLD VERSION ...`` file) is deferred to the user under "Skipped — review".

Parsing is a dry run that classifies every file (ok / skipped / error /
duplicate); committing then creates ``Document`` rows from the ``ok`` rows.
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
    InitiativeAlias,
)

# <YYYY-MM>/<filename>.<ext>
MONTH_DIR_RE = re.compile(
    r"^(?P<year>\d{4})-(?P<month>\d{2})/"
    r"(?P<basename>.+)\.(?:pdf|docx?|xlsx?|csv)$",
    re.IGNORECASE,
)
# A conforming report filename starts with the date and ends with " - <Provider>".
REPORT_NAME_RE = re.compile(r"^\d{4}-\d{2}.*\s-\s(?P<provider>.+)$")


@dataclasses.dataclass
class ParsedRow:
    archive_path: str
    original_filename: str
    provider: str
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


def resolve_initiative(provider_name):
    """Match a provider name to an Initiative by its name or an alias.

    Case-insensitive; aliases are admin-defined (``InitiativeAlias``).
    """
    name = (provider_name or "").strip()
    if not name:
        return None
    initiative = Initiative.objects.filter(name__iexact=name).first()
    if initiative is not None:
        return initiative
    alias = (
        InitiativeAlias.objects.filter(alias__iexact=name)
        .select_related("initiative")
        .first()
    )
    return alias.initiative if alias is not None else None


def _classify(archive_path, default_type):
    basename = os.path.basename(archive_path)
    if not basename or basename.startswith(".") or "__MACOSX" in archive_path:
        return None  # directory entry or system junk — ignore entirely

    path_match = MONTH_DIR_RE.match(archive_path)
    if not path_match:
        return ParsedRow(
            archive_path, basename, "", None, None, None, "skipped",
            "Not inside a YYYY-MM month folder, or not a supported file type.",
        )

    try:
        reporting_month = date(
            int(path_match.group("year")), int(path_match.group("month")), 1
        )
    except ValueError:
        return ParsedRow(
            archive_path, basename, "", None, None, default_type, "error",
            "Invalid reporting month {0}-{1}.".format(
                path_match.group("year"), path_match.group("month")
            ),
        )

    name_match = REPORT_NAME_RE.match(path_match.group("basename"))
    if not name_match:
        return ParsedRow(
            archive_path, basename, "", None, reporting_month, default_type,
            "skipped",
            "Filename does not follow the '<date> ... - <Provider>' "
            "convention — please review.",
        )

    provider = name_match.group("provider").strip()
    initiative = resolve_initiative(provider)
    if initiative is None:
        return ParsedRow(
            archive_path, basename, provider, None, reporting_month,
            default_type, "skipped",
            "No Provider matches '{0}'. Add it, or an alias, first.".format(
                provider
            ),
        )

    is_duplicate = Document.objects.filter(
        initiative=initiative,
        reporting_month=reporting_month,
        original_filename=basename,
    ).exists()

    return ParsedRow(
        archive_path, basename, provider, initiative, reporting_month,
        default_type,
        "duplicate" if is_duplicate else "ok",
        "Already imported." if is_duplicate else "",
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
            short_code="",  # legacy column, unused by the name-based convention
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
