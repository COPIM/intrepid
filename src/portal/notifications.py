"""
Notification queue/digest helpers.

A document upload enqueues one pending row per active contact; a 15-minute cron
job drains rows whose ``eligible_at`` has passed, grouping digest recipients
into a single email. Deleting a document removes its pending rows (the queue FK
cascades); ``cancel_for_document`` provides an explicit cancellation path.
"""

import logging
import os
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from mail.models import EmailTemplate
from portal.models import NotificationQueue, ProviderContact

logger = logging.getLogger(__name__)


def _next_daily(reference):
    local = timezone.localtime(reference)
    target = local.replace(
        hour=settings.DOC_DIGEST_DAILY_HOUR, minute=0, second=0, microsecond=0
    )
    if target <= local:
        target += timedelta(days=1)
    return target


def _next_weekly(reference):
    local = timezone.localtime(reference)
    target = local.replace(
        hour=settings.DOC_DIGEST_DAILY_HOUR, minute=0, second=0, microsecond=0
    )
    days_ahead = (settings.DOC_DIGEST_WEEKLY_DAY - local.weekday()) % 7
    target += timedelta(days=days_ahead)
    if target <= local:
        target += timedelta(days=7)
    return target


def _next_monthly(reference):
    local = timezone.localtime(reference)
    if local.month == 12:
        year, month = local.year + 1, 1
    else:
        year, month = local.year, local.month + 1
    return local.replace(
        year=year,
        month=month,
        day=settings.DOC_DIGEST_MONTHLY_DAY,
        hour=settings.DOC_DIGEST_DAILY_HOUR,
        minute=0,
        second=0,
        microsecond=0,
    )


def _eligible_at(document, frequency, reference):
    """Return when a notification for ``document`` is due, given ``frequency``."""
    if frequency == "immediate":
        return document.notification_eligible_at
    if frequency == "daily":
        return _next_daily(reference)
    if frequency == "weekly":
        return _next_weekly(reference)
    if frequency == "monthly":
        return _next_monthly(reference)
    return None


def enqueue_for_document(document):
    """Enqueue one notification row per active contact of the document's owner."""
    reference = timezone.now()
    contacts = ProviderContact.objects.filter(
        initiative=document.initiative
    ).exclude(notification_frequency="off")

    rows = []
    for contact in contacts:
        eligible = _eligible_at(
            document, contact.notification_frequency, reference
        )
        if eligible is None:
            continue
        rows.append(
            NotificationQueue(
                document=document,
                recipient=contact,
                eligible_at=eligible,
                frequency=contact.notification_frequency,
            )
        )
    if rows:
        NotificationQueue.objects.bulk_create(rows)
    return rows


def cancel_for_document(document):
    """Cancel all unsent notification rows for ``document``."""
    return NotificationQueue.objects.filter(
        document=document,
        sent_at__isnull=True,
        cancelled_at__isnull=True,
    ).update(cancelled_at=timezone.now())


def _document_attachments(documents):
    """Return the on-disk file paths for ``documents`` that actually exist.

    A document with no file, or whose file has gone missing from disk, is
    skipped rather than raised — a single broken attachment must not stop the
    notification email (or the cron drain) from going out.
    """
    paths = []
    for document in documents:
        try:
            path = document.file.path
        except ValueError:
            # No file associated with this document's FileField.
            continue
        if os.path.exists(path):
            paths.append(path)
        else:
            logger.warning(
                "Document %s file missing on disk (%s); sending "
                "notification without this attachment.",
                document.pk,
                path,
            )
    return paths


def _send_group(recipient, frequency, documents):
    attachments = _document_attachments(documents)
    if frequency == "immediate":
        template = EmailTemplate.objects.get(
            name="document_notification_immediate"
        )
        context = {
            "recipient": recipient,
            "document": documents[0],
            "documents": documents,
        }
    else:
        template = EmailTemplate.objects.get(
            name="document_notification_digest"
        )
        context = {
            "recipient": recipient,
            "documents": documents,
            "frequency": frequency,
        }
    return template.send(
        to=recipient.email, context=context, attachments=attachments
    )


def send_pending_notifications():
    """Drain due notification rows, grouping digests. Returns emails sent.

    Rows are grouped by ``(recipient, frequency, eligible_at)``: digest rows
    that share a send window collapse into one email, while immediate rows
    (each carrying its own document's grace time) are sent individually.
    """
    now = timezone.now()
    pending = NotificationQueue.objects.filter(
        sent_at__isnull=True,
        cancelled_at__isnull=True,
        eligible_at__lte=now,
    ).select_related(
        "recipient",
        "document",
        "document__initiative",
        "document__document_type",
    )

    groups = {}
    for row in pending:
        key = (row.recipient_id, row.frequency, row.eligible_at)
        groups.setdefault(key, []).append(row)

    emails_sent = 0
    for (_recipient_id, frequency, _eligible_at_value), rows in groups.items():
        recipient = rows[0].recipient
        documents = [row.document for row in rows]
        try:
            with transaction.atomic():
                _send_group(recipient, frequency, documents)
                NotificationQueue.objects.filter(
                    id__in=[row.id for row in rows]
                ).update(sent_at=now)
            emails_sent += 1
        except EmailTemplate.DoesNotExist:
            # Template not seeded yet — leave the rows for a later run.
            continue
        except Exception:
            # Any other failure (e.g. an attachment file vanishing between
            # the existence check and the actual open) must not abort the
            # whole drain. sent_at is only set inside the atomic block
            # above, so this group's rows are still pending and will be
            # retried on the next cron run.
            logger.exception(
                "Failed to send notification group for recipient %s "
                "(frequency=%s); rows left pending for retry.",
                recipient.pk,
                frequency,
            )
            continue
    return emails_sent
