"""Tests for the Provider invitation acceptance flow."""

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from initiatives.models import Initiative
from intrepid.models import SiteSetup
from portal.models import ProviderContact
from portal.tests._helpers import clear_seed_data


class InvitationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        clear_seed_data()
        SiteSetup.objects.create(site_name="Test OBC")
        cls.initiative = Initiative.objects.create(
            name="Punctum", short_code="PUNC"
        )
        cls.contact = ProviderContact.objects.create(
            initiative=cls.initiative,
            first_name="Grace",
            last_name="Hopper",
            email="grace@example.com",
            notification_frequency="immediate",
        )

    def _url(self, token=None):
        return reverse(
            "portal:accept_invite",
            kwargs={"token": token or self.contact.invite_token},
        )

    def test_get_shows_acceptance_form(self):
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["already_accepted"])

    def test_accepting_creates_user_and_links_initiative(self):
        response = self.client.post(
            self._url(),
            {
                "first_name": "Grace",
                "last_name": "Hopper",
                "job_title": "Engineer",
                "password1": "a-good-password-1",
                "password2": "a-good-password-1",
            },
        )
        self.assertEqual(response.status_code, 302)

        user = User.objects.get(email="grace@example.com")
        self.assertIn(user, self.initiative.users.all())

        self.contact.refresh_from_db()
        self.assertEqual(self.contact.user, user)
        self.assertIsNotNone(self.contact.accepted_at)

    def test_already_accepted_token_shows_notice(self):
        self.contact.accepted_at = timezone.now()
        self.contact.save()
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["already_accepted"])

    def test_existing_account_email_is_not_password_reset(self):
        """An unauthenticated invitee must not reset a pre-existing account."""
        existing = User.objects.create_user(
            username="grace@example.com",
            email="grace@example.com",
            password="the-real-owners-password",
        )
        response = self.client.post(
            self._url(),
            {
                "first_name": "Grace",
                "last_name": "Hopper",
                "password1": "attacker-chosen-password",
                "password2": "attacker-chosen-password",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["existing_account"])
        existing.refresh_from_db()
        self.assertTrue(
            existing.check_password("the-real-owners-password")
        )
        self.contact.refresh_from_db()
        self.assertIsNone(self.contact.accepted_at)

    def test_username_collision_routes_to_existing_account(self):
        """A user whose username == the invited email (different email) must
        route to the existing-account path, not crash on create_user."""
        User.objects.create_user(
            username="grace@example.com",
            email="someone-else@example.com",
            password="their-own-password",
        )
        before = User.objects.count()
        response = self.client.post(
            self._url(),
            {
                "first_name": "Grace",
                "last_name": "Hopper",
                "password1": "a-good-password-1",
                "password2": "a-good-password-1",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["existing_account"])
        self.assertEqual(User.objects.count(), before)
        self.contact.refresh_from_db()
        self.assertIsNone(self.contact.accepted_at)

    def test_reaccepting_does_not_create_second_user(self):
        self.contact.accepted_at = timezone.now()
        self.contact.save()
        before = User.objects.count()
        self.client.post(
            self._url(),
            {
                "first_name": "Grace",
                "last_name": "Hopper",
                "password1": "a-good-password-1",
                "password2": "a-good-password-1",
            },
        )
        self.assertEqual(User.objects.count(), before)
