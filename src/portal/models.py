"""
Data models for the document management portal.

Six models back the portal:

* :class:`DocumentType` — the admin-editable list of document types.
* :class:`Document` — a single uploaded file owned by one Provider (Initiative).
* :class:`DocumentTypePermission` — per-type read/write granularity for OBC groups.
* :class:`ProviderContact` — the editable per-Provider directory of people.
* :class:`ContactChangeLog` — an audit trail of provider-edited contact details.
* :class:`NotificationQueue` — the pending-email queue drained by cron.

Behavioural methods are stubbed with ``NotImplementedError`` until implemented
under test (red/green TDD); the fields are defined up-front so the database can
be built for the tests.
"""

import os
import uuid

import magic
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django_bleach.models import BleachField

from package.models import upload_storage

NOTIFICATION_FREQUENCY_CHOICES = (
    ("immediate", "Immediate"),
    ("daily", "Daily digest"),
    ("weekly", "Weekly digest"),
    ("monthly", "Monthly digest"),
    ("off", "Off"),
)

# Fields whose change by a Provider must be logged and notified to OBC.
CONTACT_TRACKED_FIELDS = (
    "first_name",
    "last_name",
    "job_title",
    "email",
    "notification_frequency",
)

BULK_ROW_STATUS_CHOICES = (
    ("ok", "OK"),
    ("skipped", "Skipped — please review"),
    ("error", "Error"),
    ("duplicate", "Duplicate"),
)


def portal_bulk_zip_upload_path(instance, filename):
    """Storage path for an uploaded bulk-import ZIP."""
    return os.path.join("bulk_import_zips", "{0}.zip".format(uuid.uuid4()))


def portal_documents_upload_path(instance, filename):
    """
    Build a UUID-renamed storage path for an uploaded document, namespaced by
    the owning Initiative — mirroring ``initiatives.profile_images_upload_path``.
    """
    extension = os.path.splitext(filename)[1]
    new_filename = "{0}{1}".format(uuid.uuid4(), extension)
    return os.path.join(
        "provider_documents", str(instance.initiative_id), new_filename
    )


class DocumentType(models.Model):
    """An admin-editable document type (e.g. "Remittance advice")."""

    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(unique=True)
    description = BleachField(blank=True)
    requires_reporting_month = models.BooleanField(default=False)
    default = models.BooleanField(default=False)
    ordering = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("ordering", "name")

    def __str__(self):
        return self.name


class Document(models.Model):
    """A single uploaded file belonging to one Provider (Initiative)."""

    initiative = models.ForeignKey(
        "initiatives.Initiative",
        on_delete=models.CASCADE,
        related_name="documents",
    )
    document_type = models.ForeignKey(
        DocumentType,
        on_delete=models.PROTECT,
    )
    file = models.FileField(
        upload_to=portal_documents_upload_path,
        storage=upload_storage,
    )
    display_name = models.CharField(max_length=255, blank=True)
    original_filename = models.CharField(max_length=255, blank=True)
    reporting_month = models.DateField(null=True, blank=True)
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    uploaded_at = models.DateTimeField(default=timezone.now)
    notification_eligible_at = models.DateTimeField(null=True, blank=True)
    notes = BleachField(blank=True, null=True)

    class Meta:
        ordering = ("-uploaded_at",)

    def __str__(self):
        return self.display_name or self.original_filename

    def clean(self):
        """Require a reporting month when the document type demands one."""
        super().clean()
        if (
            self.document_type_id
            and self.document_type.requires_reporting_month
            and not self.reporting_month
        ):
            raise ValidationError(
                {
                    "reporting_month": (
                        "A reporting month is required for "
                        "{0} documents.".format(self.document_type)
                    )
                }
            )

    def save(self, *args, **kwargs):
        """Capture filename metadata and set the notification grace window."""
        if self.file and not self.original_filename:
            self.original_filename = os.path.basename(self.file.name)
        if self.original_filename and not self.display_name:
            self.display_name = os.path.splitext(self.original_filename)[0]
        if self.reporting_month:
            # Reporting months are always stored as the first of the month.
            self.reporting_month = self.reporting_month.replace(day=1)
        if not self.uploaded_at:
            self.uploaded_at = timezone.now()
        if self.notification_eligible_at is None:
            self.notification_eligible_at = (
                self.uploaded_at + settings.DOC_NOTIFICATION_DELAY
            )
        super().save(*args, **kwargs)

    @property
    def file_size(self):
        return self.file.size

    @property
    def mime_type(self):
        return magic.from_file(self.file.path, mime=True)


class DocumentTypePermission(models.Model):
    """Per-document-type read/write permission for an OBC ``auth.Group``."""

    document_type = models.ForeignKey(
        DocumentType,
        on_delete=models.CASCADE,
        related_name="permissions",
    )
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    can_read = models.BooleanField(default=True)
    can_write = models.BooleanField(default=False)

    class Meta:
        unique_together = ("document_type", "group")

    def __str__(self):
        return "{0} / {1}".format(self.document_type, self.group)


class ProviderContact(models.Model):
    """A person in a Provider's editable contact directory."""

    initiative = models.ForeignKey(
        "initiatives.Initiative",
        on_delete=models.CASCADE,
        related_name="provider_contacts",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    job_title = models.CharField(max_length=255, blank=True)
    email = models.EmailField()
    position = models.PositiveSmallIntegerField(default=1)
    notification_frequency = models.CharField(
        max_length=20,
        choices=NOTIFICATION_FREQUENCY_CHOICES,
        default="immediate",
    )
    invite_token = models.UUIDField(default=uuid.uuid4, editable=False)
    invited_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("position", "last_name")

    def __str__(self):
        return "{0} {1}".format(self.first_name, self.last_name).strip()

    def save(self, *args, **kwargs):
        """Persist a ContactChangeLog row when tracked fields change.

        The acting user, when known, is supplied by the view as ``_actor``.
        """
        changes = {}
        if self.pk:
            previous = type(self).objects.filter(pk=self.pk).first()
            if previous is not None:
                for field in CONTACT_TRACKED_FIELDS:
                    old_value = getattr(previous, field)
                    new_value = getattr(self, field)
                    if old_value != new_value:
                        changes[field] = {"from": old_value, "to": new_value}
        super().save(*args, **kwargs)
        if changes:
            ContactChangeLog.objects.create(
                provider_contact=self,
                initiative=self.initiative,
                actor=getattr(self, "_actor", None),
                field_changes=changes,
            )
            self._notify_obc_of_change(changes)

    def _notify_obc_of_change(self, changes):
        """Email the OBC team that this contact's details changed."""
        from mail.models import EmailTemplate

        try:
            template = EmailTemplate.objects.get(
                name="contact_change_notification"
            )
        except EmailTemplate.DoesNotExist:
            return
        template.send(
            to=settings.FROM_EMAIL,
            context={
                "contact": self,
                "initiative": self.initiative,
                "changes": changes,
            },
        )


class ContactChangeLog(models.Model):
    """An audit-log entry for a provider-edited contact."""

    provider_contact = models.ForeignKey(
        ProviderContact,
        on_delete=models.SET_NULL,
        null=True,
        related_name="change_logs",
    )
    initiative = models.ForeignKey(
        "initiatives.Initiative",
        on_delete=models.CASCADE,
    )
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    field_changes = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return "Change to {0} at {1:%Y-%m-%d %H:%M}".format(
            self.provider_contact, self.created_at
        )


class NotificationQueue(models.Model):
    """A pending notification email, drained by the cron command."""

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    recipient = models.ForeignKey(
        ProviderContact,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    eligible_at = models.DateTimeField()
    frequency = models.CharField(max_length=20)
    sent_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["eligible_at", "sent_at"]),
            models.Index(fields=["document"]),
        ]

    def __str__(self):
        return "Notify {0} re {1}".format(self.recipient, self.document)


class BulkImportJob(models.Model):
    """A staged bulk import: an uploaded ZIP awaiting OBC confirmation."""

    zip_file = models.FileField(
        upload_to=portal_bulk_zip_upload_path,
        storage=upload_storage,
    )
    original_filename = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    created_at = models.DateTimeField(default=timezone.now)
    notify_on_commit = models.BooleanField(default=False)
    committed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return "Bulk import {0} ({1})".format(
            self.pk, self.original_filename
        )


class BulkImportRow(models.Model):
    """A single staged file within a :class:`BulkImportJob`."""

    job = models.ForeignKey(
        BulkImportJob,
        on_delete=models.CASCADE,
        related_name="rows",
    )
    archive_path = models.CharField(max_length=500)
    original_filename = models.CharField(max_length=255)
    short_code = models.CharField(max_length=10, blank=True)
    initiative = models.ForeignKey(
        "initiatives.Initiative",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    document_type = models.ForeignKey(
        DocumentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    reporting_month = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=BULK_ROW_STATUS_CHOICES, default="ok"
    )
    message = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ("status", "archive_path")

    def __str__(self):
        return "{0} ({1})".format(self.archive_path, self.status)


class InitiativeAlias(models.Model):
    """An alternative name for a Provider (Initiative), admin-editable.

    Bulk import matches a document's provider (taken from the filename) against
    the Initiative's name OR any of its aliases, so e.g. "OBP" can resolve to
    "Open Book Publishers".
    """

    initiative = models.ForeignKey(
        "initiatives.Initiative",
        on_delete=models.CASCADE,
        related_name="aliases",
    )
    alias = models.CharField(max_length=255)

    class Meta:
        ordering = ("alias",)
        unique_together = ("initiative", "alias")
        verbose_name_plural = "Initiative aliases"

    def __str__(self):
        return self.alias
