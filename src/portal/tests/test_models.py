"""Behavioural tests for the portal data models."""

import importlib
from datetime import date

from django.apps import apps as django_apps
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from initiatives.models import Initiative
from portal.tests._helpers import clear_seed_data
from portal.models import (
    ContactChangeLog,
    Document,
    DocumentType,
    ProviderContact,
    portal_documents_upload_path,
)

_contract_other_migration = importlib.import_module(
    "portal.migrations.0012_rename_contract_add_other"
)
_refresh_name_de_migration = importlib.import_module(
    "portal.migrations.0019_refresh_stale_contract_name_de"
)


class DocumentTypeSeedMigrationTests(TestCase):
    """The seed migrations rename "Agreement contract" and add "Other".

    Deliberately does NOT call ``clear_seed_data`` -- this exercises the
    actual rows left behind by the portal migrations (0004 + the later
    rename/"Other" migration), not hand-built fixtures.
    """

    def test_agreement_contract_slug_renamed_to_contract(self):
        contract = DocumentType.objects.get(slug="agreement-contract")
        self.assertEqual(contract.name, "Contract")
        self.assertNotEqual(contract.name, "Agreement contract")

    def test_other_document_type_seeded(self):
        other = DocumentType.objects.get(slug="other")
        self.assertEqual(other.name, "Other")
        self.assertFalse(other.requires_reporting_month)
        self.assertFalse(other.default)


class ContractOtherMigrationReverseTests(TestCase):
    """The 0012 migration's reverse function is guarded and idempotent.

    Calls the migration's forward/reverse RunPython callables directly
    (against the real ``apps`` registry, which satisfies the
    ``apps.get_model(app_label, model_name)`` contract the functions use) so
    the guard logic is exercised regardless of whether the kept test
    database has already recorded 0012 as applied.
    """

    def setUp(self):
        clear_seed_data()
        self.initiative = Initiative.objects.create(
            name="Reverse Migration Press", short_code="RMP"
        )
        DocumentType.objects.create(
            name="Agreement contract",
            slug="agreement-contract",
            requires_reporting_month=False,
            ordering=2,
        )

    def _forward(self):
        _contract_other_migration.rename_contract_and_add_other(
            django_apps, None
        )

    def _reverse(self):
        _contract_other_migration.revert_contract_and_remove_other(
            django_apps, None
        )

    def test_reverse_renames_contract_back_to_agreement_contract(self):
        self._forward()
        self._reverse()

        contract = DocumentType.objects.get(slug="agreement-contract")
        self.assertEqual(contract.name, "Agreement contract")

    def test_reverse_deletes_other_when_unreferenced(self):
        self._forward()
        self.assertTrue(DocumentType.objects.filter(slug="other").exists())

        self._reverse()

        self.assertFalse(DocumentType.objects.filter(slug="other").exists())

    def test_reverse_keeps_other_when_referenced_by_a_document(self):
        self._forward()
        other = DocumentType.objects.get(slug="other")
        Document.objects.create(
            initiative=self.initiative,
            document_type=other,
        )

        self._reverse()

        self.assertTrue(DocumentType.objects.filter(slug="other").exists())

    def test_forward_is_idempotent_and_does_not_duplicate_other(self):
        self._forward()
        self._forward()

        self.assertEqual(
            DocumentType.objects.filter(slug="other").count(), 1
        )


class RefreshStaleNameDeMigrationTests(TestCase):
    """0019 refreshes ``name_de`` for the renamed Contract DocumentType, but
    only when it is blank or still holds the pre-rename English label --
    a deliberately-set German translation must survive untouched.

    Calls the migration's forward/reverse RunPython callables directly
    (against the real ``apps`` registry) following the same pattern as
    ``ContractOtherMigrationReverseTests`` above.
    """

    def setUp(self):
        clear_seed_data()
        self.initiative = Initiative.objects.create(
            name="Stale Label Press", short_code="SLP"
        )

    def _forward(self):
        _refresh_name_de_migration.refresh_stale_name_de(django_apps, None)

    def _reverse(self):
        _refresh_name_de_migration.noop_reverse(django_apps, None)

    def test_blank_name_de_is_set_to_contract(self):
        contract = DocumentType.objects.create(
            name="Contract",
            slug="agreement-contract",
            requires_reporting_month=False,
            ordering=2,
            name_de="",
        )

        self._forward()

        contract.refresh_from_db()
        self.assertEqual(contract.name_de, "Contract")

    def test_old_agreement_contract_name_de_is_refreshed(self):
        contract = DocumentType.objects.create(
            name="Contract",
            slug="agreement-contract",
            requires_reporting_month=False,
            ordering=2,
            name_de="Agreement contract",
        )

        self._forward()

        contract.refresh_from_db()
        self.assertEqual(contract.name_de, "Contract")

    def test_deliberate_german_translation_is_not_overwritten(self):
        contract = DocumentType.objects.create(
            name="Contract",
            slug="agreement-contract",
            requires_reporting_month=False,
            ordering=2,
            name_de="Vertrag",
        )

        self._forward()

        contract.refresh_from_db()
        self.assertEqual(contract.name_de, "Vertrag")

    def test_missing_document_type_does_not_crash(self):
        DocumentType.objects.filter(slug="agreement-contract").delete()

        self._forward()  # must not raise

    def test_reverse_is_a_safe_no_op(self):
        contract = DocumentType.objects.create(
            name="Contract",
            slug="agreement-contract",
            requires_reporting_month=False,
            ordering=2,
            name_de="",
        )

        self._forward()
        self._reverse()

        contract.refresh_from_db()
        self.assertEqual(contract.name_de, "Contract")


class PortalModelTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        clear_seed_data()
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


class ProviderContactLanguageTests(PortalModelTestBase):
    def _make_contact(self, **kwargs):
        data = dict(
            initiative=self.initiative,
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.com",
            notification_frequency="immediate",
        )
        data.update(kwargs)
        return ProviderContact.objects.create(**data)

    def test_language_defaults_to_en(self):
        contact = self._make_contact()
        self.assertEqual(contact.language, "en")
        contact.refresh_from_db()
        self.assertEqual(contact.language, "en")

    def test_language_change_is_logged(self):
        contact = self._make_contact()
        contact.language = "de"
        contact.save()
        self.assertEqual(ContactChangeLog.objects.count(), 1)
        log = ContactChangeLog.objects.get()
        self.assertIn("language", log.field_changes)
        self.assertEqual(log.field_changes["language"]["from"], "en")
        self.assertEqual(log.field_changes["language"]["to"], "de")

    def test_no_log_when_language_unchanged(self):
        contact = self._make_contact(language="de")
        contact.position = 7  # untracked change only
        contact.save()
        self.assertEqual(ContactChangeLog.objects.count(), 0)
