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
from django.contrib.auth.models import User
from django.db import transaction
from django.template import Context, Template
from django.urls import reverse
from django.utils import timezone, translation

from mail.models import EmailTemplate
from portal.models import NotificationQueue, ProviderContact

logger = logging.getLogger(__name__)


def notify_admin_change(initiative, subject_user, action, request=None):
    """Notify a Provider's other admins and OBC staff of an admin change.

    ``action`` is ``"added"`` or ``"removed"``: ``subject_user`` has just been
    added to (or removed from) ``initiative.users``. The recipients are the
    Provider's OTHER admins (never the person just added or removed) plus all
    OBC staff accounts, deduplicated, skipping anyone without an email
    address. Each email is rendered in the recipient's language when a linked
    ``ProviderContact`` for this initiative declares one (English otherwise).

    A missing ``provider_admin_change`` template must never break the request
    that changed the membership, so it is logged and swallowed.
    """
    try:
        template = EmailTemplate.objects.get(name="provider_admin_change")
    except EmailTemplate.DoesNotExist:
        logger.error("Missing provider_admin_change email template.")
        return

    path = reverse(
        "portal:obc_initiative_users",
        kwargs={"initiative_id": initiative.pk},
    )
    url = request.build_absolute_uri(path) if request is not None else path

    recipients = {user.pk: user for user in initiative.users.all()}
    for user in User.objects.filter(is_staff=True):
        recipients.setdefault(user.pk, user)
    # The person who was just added/removed never needs telling.
    recipients.pop(subject_user.pk, None)

    admin_label = (
        subject_user.get_full_name()
        or subject_user.email
        or subject_user.username
    )
    # A recipient's language preference lives on their linked contact row.
    languages = dict(
        ProviderContact.objects.filter(
            initiative=initiative, user_id__in=recipients.keys()
        ).values_list("user_id", "language")
    )

    for user in recipients.values():
        if not user.email:
            continue
        context = {
            "recipient": user,
            "initiative": initiative,
            "action": action,
            "admin_label": admin_label,
            "admin_email": subject_user.email,
            "url": url,
        }
        with translation.override(languages.get(user.pk) or "en"):
            # The subject is a template too, so "{{ initiative.name }}"
            # resolves; the body is rendered by ``template.send`` itself.
            subject = Template(template.subject).render(Context(context))
            template.send(to=user.email, subject=subject, context=context)


def notify_access_granted(initiative, user, request=None):
    """Tell an existing account it was granted admin access to a Provider.

    When invite-by-email matches an existing, working account, that person is
    added straight to ``initiative.users`` with no invitation email — so this
    tells them it happened and where to sign in. The email is rendered in
    their language when a linked ``ProviderContact`` for this initiative
    declares one (English otherwise).

    A missing ``provider_access_granted`` template must never break the
    request that granted the access, so it is logged and swallowed.
    """
    try:
        template = EmailTemplate.objects.get(name="provider_access_granted")
    except EmailTemplate.DoesNotExist:
        logger.error("Missing provider_access_granted email template.")
        return
    if not user.email:
        return

    path = reverse("portal:index")
    url = request.build_absolute_uri(path) if request is not None else path

    # The recipient's language preference lives on their linked contact row.
    language = (
        ProviderContact.objects.filter(initiative=initiative, user=user)
        .values_list("language", flat=True)
        .first()
    )
    context = {
        "recipient": user,
        "initiative": initiative,
        "url": url,
    }
    with translation.override(language or "en"):
        # The subject is a template too, so "{{ initiative.name }}"
        # resolves; the body is rendered by ``template.send`` itself.
        subject = Template(template.subject).render(Context(context))
        template.send(to=user.email, subject=subject, context=context)


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
    # Render the template's subject/body in the recipient's chosen language.
    # ``EmailTemplate.subject``/``body`` are modeltranslation fields with an
    # English fallback, so a blank/unknown preference safely resolves to
    # English.
    with translation.override(recipient.language or "en"):
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


def resend_row(row):
    """Immediately re-send the email for a single queue ``row``.

    A thin public wrapper over :func:`_send_group` so the email-queue view can
    re-send one already-sent notification without reaching into the private
    rendering helper. Reuses the same template selection and attachment
    behaviour as the cron drain (a single-document group).
    """
    return _send_group(row.recipient, row.frequency, [row.document])


def send_pending_notifications():
    """Drain due notification rows, grouping digests. Returns emails sent.

    Rows are grouped by ``(recipient, frequency, eligible_at)``: digest rows
    that share a send window collapse into one email, while immediate rows
    (each carrying its own document's grace time) are sent individually.
    """
    now = timezone.now()
    pending = (
        NotificationQueue.objects.filter(
            sent_at__isnull=True,
            cancelled_at__isnull=True,
            eligible_at__lte=now,
        )
        .select_related(
            "recipient",
            "document",
            "document__initiative",
            "document__document_type",
        )
        # Deterministic drain order so groups are processed predictably.
        .order_by("eligible_at", "id")
    )

    groups = {}
    for row in pending:
        key = (row.recipient_id, row.frequency, row.eligible_at)
        groups.setdefault(key, []).append(row)

    emails_sent = 0
    for (_recipient_id, frequency, _eligible_at_value), rows in groups.items():
        recipient = rows[0].recipient
        try:
            with transaction.atomic():
                # Re-claim the group's rows inside the transaction, skipping any
                # that were cancelled or already sent between the initial
                # selection and now (e.g. an admin cancelling in the safety
                # window). ``skip_locked`` avoids blocking on rows a concurrent
                # drain is handling.
                claimed = list(
                    NotificationQueue.objects.select_for_update(
                        skip_locked=True
                    )
                    .select_related(
                        "document",
                        "document__initiative",
                        "document__document_type",
                    )
                    .filter(
                        id__in=[row.id for row in rows],
                        sent_at__isnull=True,
                        cancelled_at__isnull=True,
                    )
                )
                if not claimed:
                    # Every row in this group vanished (cancelled/sent); nothing
                    # left to send.
                    continue
                documents = [row.document for row in claimed]
                _send_group(recipient, frequency, documents)
                NotificationQueue.objects.filter(
                    id__in=[row.id for row in claimed]
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
