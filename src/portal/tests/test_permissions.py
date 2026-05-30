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
