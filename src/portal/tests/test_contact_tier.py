"""Behavioural tests for the Contact tier (item 2 of the portal revisions).

A Contact is a ``ProviderContact`` whose ``user`` is set but who is NOT a
member of ``initiative.users``. Contacts may log in, view and download their
initiative's documents, and edit only their own contact/notification row; they
may not manage the initiative, add contacts, or reach other initiatives.
"""

import shutil
import tempfile

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from initiatives.models import Initiative
from intrepid.models import SiteSetup
from package.models import upload_storage
from portal.tests._helpers import clear_seed_data
from django.core.files.base import ContentFile
from portal.models import Document, DocumentType, ProviderContact


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


class ContactTierTestBase(StorageRedirectMixin, TestCase):
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
        cls.contract = DocumentType.objects.create(
            name="Agreement contract", slug="contract", ordering=1
        )

        # Manager: in initiative.users.
        cls.manager = User.objects.create_user("manager", password="pw")
        cls.initiative.users.add(cls.manager)

        # Contact: linked ProviderContact, NOT in initiative.users.
        cls.contact_user = User.objects.create_user("contact", password="pw")
        cls.contact = ProviderContact.objects.create(
            initiative=cls.initiative,
            first_name="Con",
            last_name="Tact",
            email="contact@example.com",
            user=cls.contact_user,
            notification_frequency="immediate",
        )
        # A second contact on the same initiative, not the logged-in one.
        cls.other_contact = ProviderContact.objects.create(
            initiative=cls.initiative,
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.com",
            notification_frequency="daily",
        )
        # Contact on a different initiative to check cross-scope isolation.
        cls.foreign_contact = ProviderContact.objects.create(
            initiative=cls.other_initiative,
            first_name="Far",
            last_name="Away",
            email="far@example.com",
            notification_frequency="immediate",
        )

    def setUp(self):
        super().setUp()
        self.document = Document(
            initiative=self.initiative,
            document_type=self.contract,
            display_name="DocA",
        )
        self.document.file.save("DocA.pdf", ContentFile(b"hello"), save=True)
        self.other_document = Document(
            initiative=self.other_initiative,
            document_type=self.contract,
            display_name="DocB",
        )
        self.other_document.file.save(
            "DocB.pdf", ContentFile(b"secret"), save=True
        )


class ContactDocumentAccessTests(ContactTierTestBase):
    def test_contact_can_view_own_initiative_documents(self):
        self.client.force_login(self.contact_user)
        response = self.client.get(
            reverse(
                "portal:provider_initiative_documents",
                kwargs={"initiative_id": self.initiative.pk},
            )
        )
        self.assertEqual(response.status_code, 200)

    def test_contact_cannot_view_other_initiative_documents(self):
        self.client.force_login(self.contact_user)
        response = self.client.get(
            reverse(
                "portal:provider_initiative_documents",
                kwargs={"initiative_id": self.other_initiative.pk},
            )
        )
        self.assertEqual(response.status_code, 403)

    def test_contact_can_download_own_initiative_document(self):
        self.client.force_login(self.contact_user)
        response = self.client.get(
            reverse(
                "portal:download_document",
                kwargs={"doc_id": self.document.pk},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"hello")

    def test_contact_cannot_download_other_initiative_document(self):
        self.client.force_login(self.contact_user)
        response = self.client.get(
            reverse(
                "portal:download_document",
                kwargs={"doc_id": self.other_document.pk},
            )
        )
        self.assertEqual(response.status_code, 403)


class ContactContactsPaneTests(ContactTierTestBase):
    def _url(self):
        return reverse(
            "portal:provider_manage_contacts",
            kwargs={"initiative_id": self.initiative.pk},
        )

    def test_contact_can_get_contacts_page(self):
        self.client.force_login(self.contact_user)
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)

    def test_contact_does_not_see_add_contact_form(self):
        self.client.force_login(self.contact_user)
        response = self.client.get(self._url())
        self.assertNotContains(response, 'id="add-contact-form"')

    def test_manager_sees_add_contact_form(self):
        self.client.force_login(self.manager)
        response = self.client.get(self._url())
        self.assertContains(response, 'id="add-contact-form"')

    def test_contact_can_edit_own_row(self):
        self.client.force_login(self.contact_user)
        response = self.client.post(
            self._url(),
            {
                "contact_id": str(self.contact.pk),
                "first_name": "Con",
                "last_name": "Tact",
                "job_title": "Updated Title",
                "email": "contact@example.com",
                "notification_frequency": "immediate",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.contact.refresh_from_db()
        self.assertEqual(self.contact.job_title, "Updated Title")

    def test_contact_cannot_edit_another_contact_row(self):
        self.client.force_login(self.contact_user)
        response = self.client.post(
            self._url(),
            {
                "contact_id": str(self.other_contact.pk),
                "first_name": "Hacked",
                "last_name": "Lovelace",
                "job_title": "",
                "email": "ada@example.com",
                "notification_frequency": "daily",
            },
        )
        self.assertEqual(response.status_code, 403)
        self.other_contact.refresh_from_db()
        self.assertEqual(self.other_contact.first_name, "Ada")

    def test_contact_cannot_create_contact(self):
        self.client.force_login(self.contact_user)
        before = ProviderContact.objects.filter(
            initiative=self.initiative
        ).count()
        response = self.client.post(
            self._url(),
            {
                "first_name": "New",
                "last_name": "Person",
                "job_title": "",
                "email": "new@example.com",
                "notification_frequency": "immediate",
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            ProviderContact.objects.filter(initiative=self.initiative).count(),
            before,
        )

    def test_manager_can_still_create_contact(self):
        self.client.force_login(self.manager)
        response = self.client.post(
            self._url(),
            {
                "first_name": "New",
                "last_name": "Person",
                "job_title": "",
                "email": "new@example.com",
                "notification_frequency": "immediate",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            ProviderContact.objects.filter(
                initiative=self.initiative, email="new@example.com"
            ).exists()
        )


class ContactNotificationPrefsTests(ContactTierTestBase):
    def _url(self):
        return reverse(
            "portal:provider_notification_prefs",
            kwargs={"initiative_id": self.initiative.pk},
        )

    def test_contact_sees_only_own_row(self):
        self.client.force_login(self.contact_user)
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)
        contacts = list(response.context["contacts"])
        self.assertEqual(contacts, [self.contact])

    def test_manager_sees_all_rows(self):
        self.client.force_login(self.manager)
        response = self.client.get(self._url())
        contacts = set(response.context["contacts"])
        self.assertEqual(
            contacts, {self.contact, self.other_contact}
        )

    def test_contact_can_update_own_frequency(self):
        self.client.force_login(self.contact_user)
        response = self.client.post(
            self._url(),
            {"frequency_{0}".format(self.contact.pk): "weekly"},
        )
        self.assertEqual(response.status_code, 302)
        self.contact.refresh_from_db()
        self.assertEqual(self.contact.notification_frequency, "weekly")

    def test_contact_cannot_update_another_contacts_frequency(self):
        self.client.force_login(self.contact_user)
        self.client.post(
            self._url(),
            {"frequency_{0}".format(self.other_contact.pk): "off"},
        )
        self.other_contact.refresh_from_db()
        # Unchanged: the contact may not touch another row via a forged key.
        self.assertEqual(self.other_contact.notification_frequency, "daily")


class ContactManagerOnlyEndpointTests(ContactTierTestBase):
    def test_contact_cannot_delete_contact(self):
        self.client.force_login(self.contact_user)
        response = self.client.post(
            reverse(
                "portal:delete_contact",
                kwargs={
                    "initiative_id": self.initiative.pk,
                    "contact_id": self.other_contact.pk,
                },
            )
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(
            ProviderContact.objects.filter(pk=self.other_contact.pk).exists()
        )


class ContactIndexRoutingTests(ContactTierTestBase):
    def test_single_initiative_contact_routed_to_documents(self):
        self.client.force_login(self.contact_user)
        response = self.client.get(reverse("portal:index"))
        self.assertRedirects(
            response,
            reverse(
                "portal:provider_initiative_documents",
                kwargs={"initiative_id": self.initiative.pk},
            ),
            fetch_redirect_response=False,
        )

    def test_multi_initiative_contact_routed_to_picker(self):
        ProviderContact.objects.create(
            initiative=self.other_initiative,
            first_name="Con",
            last_name="Tact",
            email="contact@example.com",
            user=self.contact_user,
            notification_frequency="immediate",
        )
        self.client.force_login(self.contact_user)
        response = self.client.get(reverse("portal:index"))
        self.assertRedirects(
            response,
            reverse("portal:provider_initiative_picker"),
            fetch_redirect_response=False,
        )

    def test_picker_lists_contact_initiative(self):
        ProviderContact.objects.create(
            initiative=self.other_initiative,
            first_name="Con",
            last_name="Tact",
            email="contact@example.com",
            user=self.contact_user,
            notification_frequency="immediate",
        )
        self.client.force_login(self.contact_user)
        response = self.client.get(
            reverse("portal:provider_initiative_picker")
        )
        self.assertEqual(response.status_code, 200)
        initiatives = set(response.context["initiatives"])
        self.assertEqual(
            initiatives, {self.initiative, self.other_initiative}
        )
