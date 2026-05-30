"""Behavioural tests for the portal data models."""

from datetime import date

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from initiatives.models import Initiative
from portal.models import (
    ContactChangeLog,
    Document,
    DocumentType,
    ProviderContact,
    portal_documents_upload_path,
)


class PortalModelTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.initiative = Initiative.objects.create(
            name="Punctum Books", short_code="PUNC"
        )
        cls.user = User.objects.create_user(
            username="obc", email="obc@example.com", password="pw"
        )
        cls.remittance = DocumentType.objects.create(
            name="Remittance advice",
            slug="remittance-advice",
            requires_reporting_month=True,
            default=True,
            ordering=1,
        )
        cls.contract = DocumentType.objects.create(
            name="Agreement contract",
            slug="agreement-contract",
            requires_reporting_month=False,
            ordering=2,
        )


class DocumentUploadPathTests(PortalModelTestBase):
    def test_path_is_uuid_namespaced_by_initiative(self):
        doc = Document(initiative=self.initiative, document_type=self.contract)
        path = portal_documents_upload_path(doc, "Original Statement.pdf")
        self.assertTrue(
            path.startswith(
                "provider_documents/{0}/".format(self.initiative.pk)
            )
        )
        self.assertTrue(path.endswith(".pdf"))
        # The original (human) filename must not leak into the stored path.
        self.assertNotIn("Original", path)
        self.assertNotIn("Statement", path)

    def test_path_handles_extensionless_filename(self):
        doc = Document(initiative=self.initiative, document_type=self.contract)
        path = portal_documents_upload_path(doc, "noextension")
        self.assertTrue(
            path.startswith(
                "provider_documents/{0}/".format(self.initiative.pk)
            )
        )


class DocumentSaveTests(PortalModelTestBase):
    def test_notification_eligible_at_is_upload_plus_delay(self):
        doc = Document.objects.create(
            initiative=self.initiative, document_type=self.contract
        )
        self.assertIsNotNone(doc.notification_eligible_at)
        self.assertEqual(
            doc.notification_eligible_at,
            doc.uploaded_at + settings.DOC_NOTIFICATION_DELAY,
        )

    def test_reporting_month_coerced_to_first_of_month(self):
        doc = Document.objects.create(
            initiative=self.initiative,
            document_type=self.remittance,
            reporting_month=date(2024, 3, 15),
        )
        doc.refresh_from_db()
        self.assertEqual(doc.reporting_month, date(2024, 3, 1))

    def test_display_name_defaults_from_original_filename(self):
        doc = Document.objects.create(
            initiative=self.initiative,
            document_type=self.contract,
            original_filename="March Statement.pdf",
        )
        doc.refresh_from_db()
        self.assertEqual(doc.display_name, "March Statement")


class DocumentCleanTests(PortalModelTestBase):
    def test_clean_requires_reporting_month_for_remittance(self):
        doc = Document(
            initiative=self.initiative,
            document_type=self.remittance,
            reporting_month=None,
        )
        with self.assertRaises(ValidationError):
            doc.clean()

    def test_clean_passes_when_reporting_month_supplied(self):
        doc = Document(
            initiative=self.initiative,
            document_type=self.remittance,
            reporting_month=date(2024, 3, 1),
        )
        doc.clean()  # should not raise

    def test_clean_passes_when_type_does_not_require_month(self):
        doc = Document(
            initiative=self.initiative,
            document_type=self.contract,
            reporting_month=None,
        )
        doc.clean()  # should not raise


class ProviderContactChangeLogTests(PortalModelTestBase):
    def _make_contact(self):
        return ProviderContact.objects.create(
            initiative=self.initiative,
            first_name="Ada",
            last_name="Lovelace",
            job_title="Director",
            email="ada@example.com",
            notification_frequency="immediate",
        )

    def test_no_log_on_initial_create(self):
        self._make_contact()
        self.assertEqual(ContactChangeLog.objects.count(), 0)

    def test_log_written_on_tracked_change(self):
        contact = self._make_contact()
        contact.email = "ada.lovelace@example.com"
        contact.save()
        self.assertEqual(ContactChangeLog.objects.count(), 1)
        log = ContactChangeLog.objects.get()
        self.assertIn("email", log.field_changes)
        self.assertEqual(log.field_changes["email"]["from"], "ada@example.com")
        self.assertEqual(
            log.field_changes["email"]["to"], "ada.lovelace@example.com"
        )
        self.assertEqual(log.initiative_id, self.initiative.pk)

    def test_no_log_on_untracked_change(self):
        contact = self._make_contact()
        contact.position = 4
        contact.save()
        self.assertEqual(ContactChangeLog.objects.count(), 0)

    def test_actor_recorded_when_set(self):
        contact = self._make_contact()
        contact.first_name = "Augusta"
        contact._actor = self.user
        contact.save()
        log = ContactChangeLog.objects.get()
        self.assertEqual(log.actor_id, self.user.pk)
