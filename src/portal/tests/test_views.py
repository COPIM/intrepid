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
    InitiativeAlias,
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

    def test_upload_with_notification_ticked_enqueues_immediate_rows(self):
        ProviderContact.objects.create(
            initiative=self.initiative,
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.com",
            notification_frequency="immediate",
        )
        self.client.force_login(self.staff)
        url = reverse(
            "portal:obc_upload",
            kwargs={"initiative_id": self.initiative.pk},
        )
        response = self.client.post(
            url,
            {
                "document_type": str(self.contract.pk),
                "send_notification": "on",
                "file": [SimpleUploadedFile("notify-on.pdf", b"1")],
            },
        )
        self.assertEqual(response.status_code, 302)
        document = Document.objects.get(
            initiative=self.initiative, original_filename="notify-on.pdf"
        )
        row = NotificationQueue.objects.get(document=document)
        self.assertEqual(
            row.eligible_at,
            document.uploaded_at + settings.DOC_NOTIFICATION_DELAY,
        )

    def test_upload_with_notification_unticked_enqueues_nothing(self):
        ProviderContact.objects.create(
            initiative=self.initiative,
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.com",
            notification_frequency="immediate",
        )
        self.client.force_login(self.staff)
        url = reverse(
            "portal:obc_upload",
            kwargs={"initiative_id": self.initiative.pk},
        )
        response = self.client.post(
            url,
            {
                "document_type": str(self.contract.pk),
                "file": [SimpleUploadedFile("notify-off.pdf", b"1")],
            },
        )
        self.assertEqual(response.status_code, 302)
        document = Document.objects.get(
            initiative=self.initiative, original_filename="notify-off.pdf"
        )
        self.assertEqual(
            NotificationQueue.objects.filter(document=document).count(), 0
        )


class BulkImportViewTests(ViewTestBase):
    def _zip_upload(self):
        import io
        import zipfile

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr(
                "2024-03/2024-03 OBC Accounts Report - Punctum.pdf", b"a"
            )
            archive.writestr(
                "2024-04/2024-04 OBC Accounts Report - Punctum.pdf", b"b"
            )
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


class DocumentEditTests(ViewTestBase):
    def test_edit_form_does_not_render_notes_field(self):
        """The document edit form should not include a notes field."""
        self.client.force_login(self.staff)
        response = self.client.get(
            reverse(
                "portal:obc_document_edit",
                kwargs={"doc_id": self.document.pk},
            )
        )
        self.assertEqual(response.status_code, 200)
        # Check that the form in the response doesn't have a notes field
        self.assertNotIn("notes", response.context["form"].fields)

    def test_edit_saves_document_without_notes(self):
        """Submitting the edit form updates the document without notes."""
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse(
                "portal:obc_document_edit",
                kwargs={"doc_id": self.document.pk},
            ),
            {
                "display_name": "Updated Name",
                "document_type": str(self.contract.pk),
                "reporting_month": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.document.refresh_from_db()
        self.assertEqual(self.document.display_name, "Updated Name")


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

    def test_new_contacts_are_position_auto_numbered(self):
        self.client.force_login(self.provider)
        url = reverse(
            "portal:provider_manage_contacts",
            kwargs={"initiative_id": self.initiative.pk},
        )
        for n in range(2):
            self.client.post(
                url,
                {
                    "first_name": "Person{0}".format(n),
                    "last_name": "X",
                    "job_title": "",
                    "email": "person{0}@example.com".format(n),
                    "notification_frequency": "immediate",
                },
            )
        positions = list(
            ProviderContact.objects.filter(
                initiative=self.initiative
            ).values_list("position", flat=True).order_by("position")
        )
        self.assertEqual(positions, [1, 2])


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

    @patch("portal.views._send_invitation")
    def test_invite_not_sent_to_contact_with_active_account(self, mock_send):
        from django.utils import timezone

        # An accepted contact already has a working account; re-sending an
        # invitation to them must be refused.
        user = User.objects.create_user("ada", password="realpw")
        contact = self._contact()
        contact.user = user
        contact.accepted_at = timezone.now()
        contact.save()
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("portal:send_invite", kwargs={"contact_id": contact.pk})
        )
        self.assertEqual(response.status_code, 302)
        mock_send.assert_not_called()


class DeleteContactTests(ViewTestBase):
    def _contact(self, **kwargs):
        defaults = dict(
            initiative=self.initiative,
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.com",
            notification_frequency="immediate",
        )
        defaults.update(kwargs)
        return ProviderContact.objects.create(**defaults)

    def _url(self, contact):
        return reverse(
            "portal:delete_contact",
            kwargs={
                "initiative_id": self.initiative.pk,
                "contact_id": contact.pk,
            },
        )

    def test_manager_can_delete_another_contact(self):
        contact = self._contact()
        self.client.force_login(self.provider)
        response = self.client.post(self._url(contact))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            ProviderContact.objects.filter(pk=contact.pk).exists()
        )

    def test_cannot_delete_own_contact(self):
        contact = self._contact(user=self.provider)
        self.client.force_login(self.provider)
        response = self.client.post(self._url(contact))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            ProviderContact.objects.filter(pk=contact.pk).exists()
        )

    def test_non_manager_cannot_delete(self):
        contact = self._contact()
        self.client.force_login(self.outsider)
        response = self.client.post(self._url(contact))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(
            ProviderContact.objects.filter(pk=contact.pk).exists()
        )


class ResendInviteVisibilityTests(ViewTestBase):
    """The invite action on the contacts page reflects acceptance state."""

    def _obc_manager(self):
        # is_staff satisfies both the initiative-manager gate on the contacts
        # page and the OBC-staff check that renders the invite controls.
        return User.objects.create_user("obcmgr", password="pw", is_staff=True)

    def _contacts_url(self):
        return reverse(
            "portal:provider_manage_contacts",
            kwargs={"initiative_id": self.initiative.pk},
        )

    def _contact(self, **kwargs):
        defaults = dict(
            initiative=self.initiative,
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.com",
            notification_frequency="immediate",
        )
        defaults.update(kwargs)
        return ProviderContact.objects.create(**defaults)

    def _invite_action(self, contact):
        return reverse("portal:send_invite", kwargs={"contact_id": contact.pk})

    def test_invite_action_offered_for_pending_contact(self):
        from django.utils import timezone

        contact = self._contact(invited_at=timezone.now())
        self.client.force_login(self._obc_manager())
        response = self.client.get(self._contacts_url())
        self.assertContains(response, self._invite_action(contact))

    def test_invite_action_hidden_once_contact_has_accepted(self):
        from django.utils import timezone

        contact = self._contact(
            invited_at=timezone.now(), accepted_at=timezone.now()
        )
        self.client.force_login(self._obc_manager())
        response = self.client.get(self._contacts_url())
        self.assertNotContains(response, self._invite_action(contact))


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

    def test_invite_by_email_form_is_on_manage_users_page(self):
        self.client.force_login(self.staff)
        invite_action = reverse(
            "portal:invite_by_email",
            kwargs={"initiative_id": self.initiative.pk},
        )
        self.assertContains(self.client.get(self._url()), invite_action)

    def test_provider_cannot_invite_by_email(self):
        self.client.force_login(self.provider)
        response = self.client.post(
            reverse(
                "portal:invite_by_email",
                kwargs={"initiative_id": self.initiative.pk},
            ),
            {"email": "someone@example.com"},
        )
        self.assertEqual(response.status_code, 403)


class InitiativeAliasManagementTests(ViewTestBase):
    def _url(self):
        return reverse(
            "portal:obc_initiative_aliases",
            kwargs={"initiative_id": self.initiative.pk},
        )

    def test_obc_can_view_aliases_page(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(self._url()).status_code, 200)

    def test_obc_can_add_alias_to_initiative(self):
        self.client.force_login(self.staff)
        response = self.client.post(self._url(), {"alias": "OBP"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            InitiativeAlias.objects.filter(
                initiative=self.initiative, alias="OBP"
            ).exists()
        )

    def test_adding_duplicate_alias_does_not_error(self):
        InitiativeAlias.objects.create(initiative=self.initiative, alias="OBP")
        self.client.force_login(self.staff)
        response = self.client.post(self._url(), {"alias": "OBP"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            InitiativeAlias.objects.filter(
                initiative=self.initiative, alias="OBP"
            ).count(),
            1,
        )

    def test_obc_can_remove_alias_from_initiative(self):
        alias = InitiativeAlias.objects.create(
            initiative=self.initiative, alias="OBP"
        )
        self.client.force_login(self.staff)
        response = self.client.post(
            self._url(), {"remove_alias": str(alias.pk)}
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            InitiativeAlias.objects.filter(pk=alias.pk).exists()
        )

    def test_provider_cannot_access_aliases(self):
        self.client.force_login(self.provider)
        self.assertEqual(self.client.get(self._url()).status_code, 403)
        response = self.client.post(self._url(), {"alias": "OBP"})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            InitiativeAlias.objects.filter(initiative=self.initiative).exists()
        )

    def test_aliases_tab_visible_to_obc_not_to_provider(self):
        alias_url = self._url()
        # OBC staff (is_staff) see the Aliases tab in the provider sub-nav.
        obc = User.objects.create_user("obcmgr2", password="pw", is_staff=True)
        self.client.force_login(obc)
        contacts_url = reverse(
            "portal:provider_manage_contacts",
            kwargs={"initiative_id": self.initiative.pk},
        )
        self.assertContains(self.client.get(contacts_url), alias_url)
        # A provider member never sees the Aliases tab.
        self.client.force_login(self.provider)
        docs_url = reverse(
            "portal:provider_initiative_documents",
            kwargs={"initiative_id": self.initiative.pk},
        )
        self.assertNotContains(self.client.get(docs_url), alias_url)


class BulkDownloadTests(ViewTestBase):
    def test_bulk_download_streams_zip(self):
        import io
        import zipfile

        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("portal:bulk_download"),
            {"document_ids": [str(self.document.pk)]},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/zip")
        archive = zipfile.ZipFile(
            io.BytesIO(b"".join(response.streaming_content))
        )
        self.assertEqual(len(archive.namelist()), 1)
        self.assertEqual(archive.read(archive.namelist()[0]), b"hello")


class DocumentsTableUXTests(ViewTestBase):
    """Structural coverage for the clear-filter link, the Provider table's
    DataTables wiring and its select-all checkbox (items 4c/4d/4e)."""

    def test_provider_documents_page_has_clear_filter_link(self):
        self.client.force_login(self.provider)
        url = reverse(
            "portal:provider_initiative_documents",
            kwargs={"initiative_id": self.initiative.pk},
        )
        response = self.client.get(url, {"q": "something"})
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('id="clear-filters"', content)
        self.assertIn('href="{0}"'.format(url), content)

    def test_obc_documents_page_has_clear_filter_link(self):
        self.client.force_login(self.staff)
        url = reverse(
            "portal:obc_initiative_detail",
            kwargs={"initiative_id": self.initiative.pk},
        )
        response = self.client.get(url, {"q": "something"})
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('id="clear-filters"', content)
        self.assertIn('href="{0}"'.format(url), content)

    def test_provider_documents_table_has_id_for_datatables_init(self):
        self.client.force_login(self.provider)
        response = self.client.get(
            reverse(
                "portal:provider_initiative_documents",
                kwargs={"initiative_id": self.initiative.pk},
            )
        )
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('id="documents-table"', content)

    def test_provider_documents_page_loads_jquery_and_datatables(self):
        self.client.force_login(self.provider)
        response = self.client.get(
            reverse(
                "portal:provider_initiative_documents",
                kwargs={"initiative_id": self.initiative.pk},
            )
        )
        content = response.content.decode().lower()
        self.assertIn("jquery", content)
        self.assertIn("datatables", content)

    def test_provider_documents_table_checkbox_and_action_columns_not_orderable(
        self,
    ):
        self.client.force_login(self.provider)
        response = self.client.get(
            reverse(
                "portal:provider_initiative_documents",
                kwargs={"initiative_id": self.initiative.pk},
            )
        )
        content = response.content.decode()
        self.assertIn("orderable", content)
        self.assertIn("false", content)

    def test_provider_documents_page_has_select_all_checkbox(self):
        self.client.force_login(self.provider)
        response = self.client.get(
            reverse(
                "portal:provider_initiative_documents",
                kwargs={"initiative_id": self.initiative.pk},
            )
        )
        content = response.content.decode()
        self.assertIn('id="select-all-documents"', content)

    def test_obc_documents_page_has_no_select_all_checkbox(self):
        # Per the brief, only the Provider table gets the DataTables /
        # select-all treatment; the OBC table is left as a plain list.
        self.client.force_login(self.staff)
        response = self.client.get(
            reverse(
                "portal:obc_initiative_detail",
                kwargs={"initiative_id": self.initiative.pk},
            )
        )
        content = response.content.decode()
        self.assertNotIn('id="select-all-documents"', content)


class StaffManagementTests(ViewTestBase):
    def _url(self):
        return reverse("portal:obc_manage_staff")

    def test_obc_can_add_user_as_staff(self):
        newcomer = User.objects.create_user(
            "newstaff", email="newstaff@example.com", password="pw"
        )
        self.client.force_login(self.staff)
        response = self.client.post(
            self._url(), {"email": "newstaff@example.com"}
        )
        self.assertEqual(response.status_code, 302)
        newcomer.refresh_from_db()
        self.assertTrue(newcomer.is_staff)
        self.assertIn(newcomer, self.obc_group.user_set.all())

    def test_obc_can_remove_staff(self):
        target = User.objects.create_user(
            "removeme", email="removeme@example.com", password="pw"
        )
        target.is_staff = True
        target.save()
        target.groups.add(self.obc_group)
        self.client.force_login(self.staff)
        response = self.client.post(
            self._url(), {"remove_user": str(target.pk)}
        )
        self.assertEqual(response.status_code, 302)
        target.refresh_from_db()
        self.assertFalse(target.is_staff)
        self.assertNotIn(target, self.obc_group.user_set.all())

    def test_provider_denied_staff_screen(self):
        self.client.force_login(self.provider)
        self.assertEqual(self.client.get(self._url()).status_code, 403)

    def test_outsider_denied_staff_screen(self):
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(self._url()).status_code, 403)

    def test_unknown_email_is_rejected(self):
        self.client.force_login(self.staff)
        before = list(
            User.objects.filter(is_staff=True).values_list("pk", flat=True)
        )
        response = self.client.post(
            self._url(), {"email": "nobody@example.com"}
        )
        self.assertEqual(response.status_code, 200)
        after = list(
            User.objects.filter(is_staff=True).values_list("pk", flat=True)
        )
        self.assertEqual(before, after)
