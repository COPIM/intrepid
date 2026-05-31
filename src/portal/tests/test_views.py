"""Behavioural tests for the portal views (permissions, uploads, downloads)."""

import shutil
import tempfile
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from initiatives.models import Initiative
from intrepid.models import SiteSetup
from package.models import upload_storage
from portal.tests._helpers import clear_seed_data
from portal.models import (
    ContactChangeLog,
    Document,
    DocumentType,
    NotificationQueue,
    ProviderContact,
)


class StorageRedirectMixin:
    @staticmethod
    def _point_storage(location):
        upload_storage._location = location
        upload_storage.__dict__.pop("location", None)
        upload_storage.__dict__.pop("base_location", None)

    def setUp(self):
        super().setUp()
        self._tmp = tempfile.mkdtemp()
        self._orig_location = upload_storage._location
        self._point_storage(self._tmp)

    def tearDown(self):
        self._point_storage(self._orig_location)
        shutil.rmtree(self._tmp, ignore_errors=True)
        super().tearDown()


class ViewTestBase(StorageRedirectMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        clear_seed_data()
        SiteSetup.objects.create(site_name="Test OBC")
        cls.initiative = Initiative.objects.create(
            name="Punctum", short_code="PUNC"
        )
        cls.other_initiative = Initiative.objects.create(
            name="Open", short_code="OPEN"
        )
        cls.remittance = DocumentType.objects.create(
            name="Remittance advice",
            slug="remittance",
            requires_reporting_month=True,
            default=True,
            ordering=1,
        )
        cls.contract = DocumentType.objects.create(
            name="Agreement contract", slug="contract", ordering=2
        )
        cls.obc_group = Group.objects.create(name="OBC Team")
        cls.staff = User.objects.create_user("staff", password="pw")
        cls.staff.groups.add(cls.obc_group)
        cls.provider = User.objects.create_user("provider", password="pw")
        cls.initiative.users.add(cls.provider)
        cls.outsider = User.objects.create_user("outsider", password="pw")

    def setUp(self):
        super().setUp()
        self.document = Document(
            initiative=self.initiative,
            document_type=self.contract,
            display_name="DocA",
        )
        self.document.file.save("DocA.pdf", ContentFile(b"hello"), save=True)


class ProviderScopingTests(ViewTestBase):
    def test_provider_cannot_view_other_initiative(self):
        self.client.force_login(self.provider)
        response = self.client.get(
            reverse(
                "portal:provider_initiative_documents",
                kwargs={"initiative_id": self.other_initiative.pk},
            )
        )
        self.assertEqual(response.status_code, 403)

    def test_provider_can_view_own_initiative(self):
        self.client.force_login(self.provider)
        response = self.client.get(
            reverse(
                "portal:provider_initiative_documents",
                kwargs={"initiative_id": self.initiative.pk},
            )
        )
        self.assertEqual(response.status_code, 200)

    def test_outsider_denied_obc_dashboard(self):
        self.client.force_login(self.outsider)
        response = self.client.get(reverse("portal:obc_dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_staff_can_view_obc_dashboard(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("portal:obc_dashboard"))
        self.assertEqual(response.status_code, 200)


class DownloadTests(ViewTestBase):
    def _download(self, user):
        self.client.force_login(user)
        return self.client.get(
            reverse(
                "portal:download_document",
                kwargs={"doc_id": self.document.pk},
            )
        )

    def test_obc_staff_can_download(self):
        response = self._download(self.staff)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"hello")

    def test_provider_in_initiative_can_download(self):
        self.assertEqual(self._download(self.provider).status_code, 200)

    def test_outsider_denied_download(self):
        self.assertEqual(self._download(self.outsider).status_code, 403)


class UploadTests(ViewTestBase):
    def test_upload_creates_documents(self):
        self.client.force_login(self.staff)
        url = reverse(
            "portal:obc_upload",
            kwargs={"initiative_id": self.initiative.pk},
        )
        before = Document.objects.filter(initiative=self.initiative).count()
        response = self.client.post(
            url,
            {
                "document_type": str(self.contract.pk),
                "file": [
                    SimpleUploadedFile("one.pdf", b"1"),
                    SimpleUploadedFile("two.pdf", b"2"),
                ],
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            Document.objects.filter(initiative=self.initiative).count(),
            before + 2,
        )

    def test_upload_remittance_requires_month(self):
        self.client.force_login(self.staff)
        url = reverse(
            "portal:obc_upload",
            kwargs={"initiative_id": self.initiative.pk},
        )
        before = Document.objects.count()
        response = self.client.post(
            url,
            {
                "document_type": str(self.remittance.pk),
                "file": [SimpleUploadedFile("one.pdf", b"1")],
            },
        )
        self.assertEqual(response.status_code, 200)  # re-rendered with errors
        self.assertEqual(Document.objects.count(), before)


class BulkImportViewTests(ViewTestBase):
    def _zip_upload(self):
        import io
        import zipfile

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("PUNC/2024-03/a.pdf", b"a")
            archive.writestr("PUNC/2024-04/b.pdf", b"b")
        return SimpleUploadedFile(
            "archive.zip", buffer.getvalue(), content_type="application/zip"
        )

    def test_preview_then_commit_creates_documents(self):
        self.client.force_login(self.staff)
        preview = self.client.post(
            reverse("portal:obc_bulk_import"),
            {"zip_file": self._zip_upload()},
        )
        self.assertEqual(preview.status_code, 200)
        job = preview.context["job"]
        self.assertEqual(job.rows.filter(status="ok").count(), 2)

        before = Document.objects.count()
        commit = self.client.post(
            reverse(
                "portal:obc_bulk_commit", kwargs={"job_id": job.pk}
            )
        )
        self.assertEqual(commit.status_code, 302)
        self.assertEqual(Document.objects.count(), before + 2)


class DocumentDeleteTests(ViewTestBase):
    def test_delete_removes_document_and_pending_notifications(self):
        ProviderContact.objects.create(
            initiative=self.initiative,
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.com",
            notification_frequency="immediate",
        )
        document = Document.objects.create(
            initiative=self.initiative,
            document_type=self.contract,
            display_name="ToDelete",
        )
        self.assertEqual(
            NotificationQueue.objects.filter(document=document).count(), 1
        )

        self.client.force_login(self.staff)
        response = self.client.post(
            reverse(
                "portal:obc_document_delete",
                kwargs={"doc_id": document.pk},
            )
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Document.objects.filter(pk=document.pk).exists())
        self.assertEqual(
            NotificationQueue.objects.filter(document_id=document.pk).count(),
            0,
        )


class ContactManagementTests(ViewTestBase):
    @patch("mail.models.EmailTemplate._send_email", return_value=1)
    def test_editing_contact_logs_change_and_emails_obc(self, mock_send):
        from mail.models import EmailTemplate

        EmailTemplate.objects.create(
            name="contact_change_notification",
            subject="Contact changed",
            body="{{ contact.email }} changed",
        )
        contact = ProviderContact.objects.create(
            initiative=self.initiative,
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.com",
            notification_frequency="immediate",
        )
        self.client.force_login(self.provider)
        response = self.client.post(
            reverse(
                "portal:provider_manage_contacts",
                kwargs={"initiative_id": self.initiative.pk},
            ),
            {
                "contact_id": str(contact.pk),
                "first_name": "Ada",
                "last_name": "Lovelace",
                "job_title": "",
                "email": "ada.new@example.com",
                "position": "1",
                "notification_frequency": "immediate",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ContactChangeLog.objects.count(), 1)
        recipients = [call.kwargs["to"] for call in mock_send.call_args_list]
        self.assertTrue(
            any(settings.FROM_EMAIL in to for to in recipients)
        )


class BulkImportPermissionTests(ViewTestBase):
    def test_readonly_doc_type_user_cannot_bulk_import(self):
        from portal.models import DocumentTypePermission

        readers = Group.objects.create(name="Readers")
        DocumentTypePermission.objects.create(
            document_type=self.contract,
            group=readers,
            can_read=True,
            can_write=False,
        )
        reader = User.objects.create_user("reader", password="pw")
        reader.groups.add(readers)

        self.client.force_login(reader)
        response = self.client.get(reverse("portal:obc_bulk_import"))
        self.assertEqual(response.status_code, 403)


class DateFilterRobustnessTests(ViewTestBase):
    def test_garbage_date_filter_does_not_500(self):
        self.client.force_login(self.staff)
        response = self.client.get(
            reverse(
                "portal:obc_initiative_detail",
                kwargs={"initiative_id": self.initiative.pk},
            ),
            {"uploaded_after": "not-a-date"},
        )
        self.assertEqual(response.status_code, 200)


class SendInviteTests(ViewTestBase):
    def _contact(self):
        return ProviderContact.objects.create(
            initiative=self.initiative,
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.com",
            notification_frequency="immediate",
        )

    @patch("mail.models.EmailTemplate._send_email", return_value=1)
    def test_obc_can_send_invitation(self, mock_send):
        from mail.models import EmailTemplate

        EmailTemplate.objects.create(
            name="provider_invite",
            subject="You are invited",
            body="Accept here: {{ url }}",
        )
        contact = self._contact()
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse(
                "portal:send_invite", kwargs={"contact_id": contact.pk}
            )
        )
        self.assertEqual(response.status_code, 302)
        contact.refresh_from_db()
        self.assertIsNotNone(contact.invited_at)
        recipients = [call.kwargs["to"] for call in mock_send.call_args_list]
        self.assertTrue(any("ada@example.com" in to for to in recipients))

    def test_provider_cannot_send_invitation(self):
        contact = self._contact()
        self.client.force_login(self.provider)
        response = self.client.post(
            reverse(
                "portal:send_invite", kwargs={"contact_id": contact.pk}
            )
        )
        self.assertEqual(response.status_code, 403)


class InitiativeUserManagementTests(ViewTestBase):
    def _url(self):
        return reverse(
            "portal:obc_initiative_users",
            kwargs={"initiative_id": self.initiative.pk},
        )

    def test_obc_can_add_user_to_initiative(self):
        newcomer = User.objects.create_user(
            "newcomer", email="newcomer@example.com", password="pw"
        )
        self.client.force_login(self.staff)
        response = self.client.post(
            self._url(), {"email": "newcomer@example.com"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(newcomer, self.initiative.users.all())

    def test_obc_can_remove_user_from_initiative(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            self._url(), {"remove_user": str(self.provider.pk)}
        )
        self.assertEqual(response.status_code, 302)
        self.assertNotIn(self.provider, self.initiative.users.all())

    def test_unknown_email_is_rejected(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            self._url(), {"email": "nobody@example.com"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.initiative.users.count(), 1)  # unchanged

    def test_provider_cannot_manage_users(self):
        self.client.force_login(self.provider)
        self.assertEqual(self.client.get(self._url()).status_code, 403)


class BulkDownloadTests(ViewTestBase):
    def test_bulk_download_streams_zip(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("portal:bulk_download"),
            {"document_ids": [str(self.document.pk)]},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/zip")
