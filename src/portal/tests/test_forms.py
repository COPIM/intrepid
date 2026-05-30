"""Tests for portal form validation behaviour."""

import io
import zipfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils.datastructures import MultiValueDict

from initiatives.models import Initiative
from portal import forms
from portal.tests._helpers import clear_seed_data
from portal.models import DocumentType


class FormTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        clear_seed_data()
        cls.initiative = Initiative.objects.create(
            name="Punctum", short_code="PUNC"
        )
        cls.remittance = DocumentType.objects.create(
            name="Remittance advice",
            slug="remittance",
            requires_reporting_month=True,
            default=True,
            ordering=1,
        )
        cls.contract = DocumentType.objects.create(
            name="Agreement contract",
            slug="contract",
            requires_reporting_month=False,
            ordering=2,
        )


class DocumentUploadFormTests(FormTestBase):
    def _files(self, count):
        return MultiValueDict(
            {
                "file": [
                    SimpleUploadedFile(
                        "doc{0}.pdf".format(n), b"data%d" % n
                    )
                    for n in range(count)
                ]
            }
        )

    def test_requires_reporting_month_for_remittance(self):
        form = forms.DocumentUploadForm(
            data={"document_type": str(self.remittance.pk)},
            files=self._files(1),
        )
        self.assertFalse(form.is_valid())
        self.assertIn("reporting_month", form.errors)

    def test_no_month_required_for_contract(self):
        form = forms.DocumentUploadForm(
            data={"document_type": str(self.contract.pk)},
            files=self._files(1),
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_accepts_multiple_files(self):
        form = forms.DocumentUploadForm(
            data={"document_type": str(self.contract.pk)},
            files=self._files(3),
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(len(form.cleaned_data["file"]), 3)

    def test_month_string_parses(self):
        form = forms.DocumentUploadForm(
            data={
                "document_type": str(self.remittance.pk),
                "reporting_month": "2024-03",
            },
            files=self._files(1),
        )
        self.assertTrue(form.is_valid(), form.errors)


class DocumentEditFormTests(FormTestBase):
    def test_requires_reporting_month_for_remittance(self):
        form = forms.DocumentEditForm(
            data={
                "display_name": "March",
                "document_type": str(self.remittance.pk),
                "reporting_month": "",
                "notes": "",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("reporting_month", form.errors)


class BulkImportZipFormTests(FormTestBase):
    def _zip_upload(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("PUNC/2024-03/a.pdf", b"a")
        return SimpleUploadedFile(
            "archive.zip", buffer.getvalue(), content_type="application/zip"
        )

    def test_rejects_non_zip(self):
        not_a_zip = SimpleUploadedFile("file.txt", b"not a zip")
        form = forms.BulkImportZipForm(
            data={}, files={"zip_file": not_a_zip}
        )
        self.assertFalse(form.is_valid())
        self.assertIn("zip_file", form.errors)

    def test_accepts_zip(self):
        form = forms.BulkImportZipForm(
            data={"notify_on_commit": False},
            files={"zip_file": self._zip_upload()},
        )
        self.assertTrue(form.is_valid(), form.errors)


class AcceptInviteFormTests(FormTestBase):
    def test_password_mismatch_invalid(self):
        form = forms.AcceptInviteForm(
            data={
                "first_name": "Ada",
                "last_name": "Lovelace",
                "password1": "secret-pass-123",
                "password2": "different-pass-456",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors)

    def test_weak_password_rejected(self):
        form = forms.AcceptInviteForm(
            data={
                "first_name": "Ada",
                "last_name": "Lovelace",
                "password1": "1",
                "password2": "1",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("password1", form.errors)

    def test_matching_passwords_valid(self):
        form = forms.AcceptInviteForm(
            data={
                "first_name": "Ada",
                "last_name": "Lovelace",
                "password1": "secret-pass-123",
                "password2": "secret-pass-123",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)


class ProviderContactFormTests(FormTestBase):
    def test_valid_contact(self):
        form = forms.ProviderContactForm(
            data={
                "first_name": "Ada",
                "last_name": "Lovelace",
                "job_title": "Director",
                "email": "ada@example.com",
                "position": "1",
                "notification_frequency": "immediate",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
