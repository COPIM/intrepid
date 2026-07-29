"""Tests for the portal's two-layer permission helpers (Layer B)."""

from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from initiatives.models import Initiative
from portal import permissions
from portal.tests._helpers import clear_seed_data
from portal.models import (
    Document,
    DocumentType,
    DocumentTypePermission,
    ProviderContact,
)


class PermissionTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        clear_seed_data()
        cls.initiative = Initiative.objects.create(
            name="Punctum", short_code="PUNC"
        )
        cls.remittance = DocumentType.objects.create(
            name="Remittance advice", slug="remittance", ordering=1
        )
        cls.contract = DocumentType.objects.create(
            name="Agreement contract", slug="contract", ordering=2
        )
        cls.obc_group = Group.objects.create(name="OBC Team")

        cls.superuser = User.objects.create_superuser(
            username="root", email="root@example.com", password="pw"
        )
        cls.staff = User.objects.create_user(
            username="staff", password="pw", is_staff=True
        )
        cls.obc_member = User.objects.create_user(username="obc", password="pw")
        cls.obc_member.groups.add(cls.obc_group)
        cls.plain = User.objects.create_user(username="plain", password="pw")

        # A reader group with read-only access to remittance advice.
        cls.reader_group = Group.objects.create(name="Readers")
        cls.reader = User.objects.create_user(username="reader", password="pw")
        cls.reader.groups.add(cls.reader_group)
        DocumentTypePermission.objects.create(
            document_type=cls.remittance,
            group=cls.reader_group,
            can_read=True,
            can_write=False,
        )


class IsObcStaffTests(PermissionTestBase):
    def test_superuser_is_obc_staff(self):
        self.assertTrue(permissions.is_obc_staff(self.superuser))

    def test_staff_is_obc_staff(self):
        self.assertTrue(permissions.is_obc_staff(self.staff))

    def test_obc_group_member_is_obc_staff(self):
        self.assertTrue(permissions.is_obc_staff(self.obc_member))

    def test_plain_user_is_not_obc_staff(self):
        self.assertFalse(permissions.is_obc_staff(self.plain))


class UserCanTests(PermissionTestBase):
    def test_superuser_can_write_any_type(self):
        self.assertTrue(
            permissions.user_can(self.superuser, "write", self.contract)
        )

    def test_obc_member_can_do_anything(self):
        self.assertTrue(
            permissions.user_can(self.obc_member, "write", self.contract)
        )

    def test_reader_can_read_but_not_write(self):
        self.assertTrue(
            permissions.user_can(self.reader, "read", self.remittance)
        )
        self.assertFalse(
            permissions.user_can(self.reader, "write", self.remittance)
        )

    def test_reader_has_no_access_to_other_type(self):
        self.assertFalse(
            permissions.user_can(self.reader, "read", self.contract)
        )

    def test_plain_user_cannot_read(self):
        self.assertFalse(
            permissions.user_can(self.plain, "read", self.remittance)
        )


class ContactTierHelperTests(PermissionTestBase):
    """Unit tests for the three-tier access helpers."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.other_initiative = Initiative.objects.create(
            name="Open", short_code="OPEN"
        )
        # A manager: member of initiative.users.
        cls.manager = User.objects.create_user("mgr", password="pw")
        cls.initiative.users.add(cls.manager)
        # A contact: linked ProviderContact but NOT in initiative.users.
        cls.contact_user = User.objects.create_user("contact", password="pw")
        cls.contact = ProviderContact.objects.create(
            initiative=cls.initiative,
            first_name="Con",
            last_name="Tact",
            email="contact@example.com",
            user=cls.contact_user,
        )

    def test_linked_contact_returns_row_for_linked_user(self):
        self.assertEqual(
            permissions.linked_contact(self.contact_user, self.initiative),
            self.contact,
        )

    def test_linked_contact_none_for_other_initiative(self):
        self.assertIsNone(
            permissions.linked_contact(self.contact_user, self.other_initiative)
        )

    def test_linked_contact_none_for_manager(self):
        self.assertIsNone(
            permissions.linked_contact(self.manager, self.initiative)
        )

    def test_can_manage_initiative_true_for_member(self):
        self.assertTrue(
            permissions.can_manage_initiative(self.manager, self.initiative)
        )

    def test_can_manage_initiative_true_for_staff(self):
        self.assertTrue(
            permissions.can_manage_initiative(self.staff, self.initiative)
        )

    def test_can_manage_initiative_false_for_contact(self):
        self.assertFalse(
            permissions.can_manage_initiative(self.contact_user, self.initiative)
        )

    def test_can_access_initiative_true_for_contact(self):
        self.assertTrue(
            permissions.can_access_initiative(self.contact_user, self.initiative)
        )

    def test_can_access_initiative_true_for_manager(self):
        self.assertTrue(
            permissions.can_access_initiative(self.manager, self.initiative)
        )

    def test_can_access_initiative_false_for_contact_other_initiative(self):
        self.assertFalse(
            permissions.can_access_initiative(
                self.contact_user, self.other_initiative
            )
        )

    def test_can_access_initiative_false_for_outsider(self):
        self.assertFalse(
            permissions.can_access_initiative(self.plain, self.initiative)
        )


class InitiativeAccessDecoratorTests(PermissionTestBase):
    """The decorator admits managers and contacts, rejects outsiders."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.contact_user = User.objects.create_user("dcon", password="pw")
        ProviderContact.objects.create(
            initiative=cls.initiative,
            first_name="D",
            last_name="C",
            email="dc@example.com",
            user=cls.contact_user,
        )

    def setUp(self):
        self.factory = RequestFactory()

        @permissions.initiative_access_required
        def view(request, initiative_id):
            return HttpResponse("ok")

        self.view = view

    def _request(self, user):
        request = self.factory.get("/")
        request.user = user
        return request

    def test_contact_is_allowed(self):
        response = self.view(
            self._request(self.contact_user), initiative_id=self.initiative.pk
        )
        self.assertEqual(response.status_code, 200)

    def test_outsider_is_denied(self):
        with self.assertRaises(PermissionDenied):
            self.view(
                self._request(self.plain), initiative_id=self.initiative.pk
            )


class ObcTeamManagementConsistencyTests(PermissionTestBase):
    """An OBC Team group member with is_staff=False is full-access management."""

    def test_can_manage_initiative_true_for_obc_group_member(self):
        # obc_member is in the "OBC Team" group but is not is_staff.
        self.assertFalse(self.obc_member.is_staff)
        self.assertTrue(
            permissions.can_manage_initiative(self.obc_member, self.initiative)
        )

    def test_can_manage_initiative_false_for_plain_user(self):
        self.assertFalse(
            permissions.can_manage_initiative(self.plain, self.initiative)
        )


class InitiativeManagerDecoratorTests(PermissionTestBase):
    """``initiative_manager_required`` admits managers/OBC staff only."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.manager = User.objects.create_user("mgr2", password="pw")
        cls.initiative.users.add(cls.manager)
        cls.contact_user = User.objects.create_user("ccon", password="pw")
        ProviderContact.objects.create(
            initiative=cls.initiative,
            first_name="C",
            last_name="C",
            email="cc@example.com",
            user=cls.contact_user,
        )

    def setUp(self):
        self.factory = RequestFactory()

        @permissions.initiative_manager_required
        def view(request, initiative_id):
            return HttpResponse("ok")

        self.view = view

    def _request(self, user):
        request = self.factory.get("/")
        request.user = user
        return request

    def test_manager_allowed(self):
        response = self.view(
            self._request(self.manager), initiative_id=self.initiative.pk
        )
        self.assertEqual(response.status_code, 200)

    def test_obc_group_member_allowed(self):
        response = self.view(
            self._request(self.obc_member), initiative_id=self.initiative.pk
        )
        self.assertEqual(response.status_code, 200)

    def test_contact_denied(self):
        with self.assertRaises(PermissionDenied):
            self.view(
                self._request(self.contact_user),
                initiative_id=self.initiative.pk,
            )

    def test_outsider_denied(self):
        with self.assertRaises(PermissionDenied):
            self.view(
                self._request(self.plain), initiative_id=self.initiative.pk
            )


class RequiresDocTypeDecoratorTests(PermissionTestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self.document = Document.objects.create(
            initiative=self.initiative, document_type=self.remittance
        )

        @permissions.requires_doc_type("write")
        def view(request, doc_id):
            return HttpResponse("ok")

        self.view = view

    def test_allows_authorised_user(self):
        request = self.factory.get("/")
        request.user = self.superuser
        response = self.view(request, doc_id=self.document.pk)
        self.assertEqual(response.status_code, 200)

    def test_blocks_unauthorised_user(self):
        request = self.factory.get("/")
        request.user = self.reader  # read-only on remittance, no write
        with self.assertRaises(PermissionDenied):
            self.view(request, doc_id=self.document.pk)
