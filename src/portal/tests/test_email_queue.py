"""Behavioural tests for the OBC email-queue management page.

The page lists ``NotificationQueue`` rows (pending, sent and cancelled) and lets
OBC staff cancel a still-pending email (keeping its document) or re-send one that
has already been sent. Providers and Contacts must never reach it.
"""

from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.core import mail as django_mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from initiatives.models import Initiative
from intrepid.models import SiteSetup
from mail.models import EmailTemplate
from portal import notifications
from portal.models import (
    Document,
    DocumentType,
    NotificationQueue,
    ProviderContact,
)
from portal.tests._helpers import clear_seed_data
from portal.tests.test_views import StorageRedirectMixin


class EmailQueueTestBase(StorageRedirectMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        clear_seed_data()
        SiteSetup.objects.create(site_name="Test OBC")
        cls.initiative = Initiative.objects.create(
            name="Punctum", short_code="PUNC"
        )
        cls.doc_type = DocumentType.objects.create(
            name="Remittance advice", slug="remittance", ordering=1
        )
        EmailTemplate.objects.create(
            name="document_notification_immediate",
            subject="New document",
            body="New document: {{ document.display_name }}",
        )
        EmailTemplate.objects.create(
            name="document_notification_digest",
            subject="Your document digest",
            body="{% for d in documents %}[{{ d.display_name }}]{% endfor %}",
        )
        cls.obc_group = Group.objects.create(name="OBC Team")
        cls.staff = User.objects.create_user("staff", password="pw")
        cls.staff.groups.add(cls.obc_group)
        cls.provider = User.objects.create_user("provider", password="pw")
        cls.initiative.users.add(cls.provider)
        # A Contact-tier user linked to a ProviderContact of this initiative.
        cls.contact_user = User.objects.create_user(
            "contactuser", password="pw"
        )
        cls.outsider = User.objects.create_user("outsider", password="pw")

    def _contact(self, first="A", user=None):
        return ProviderContact.objects.create(
            initiative=self.initiative,
            first_name=first,
            last_name="Person",
            email="{0}@example.com".format(first.lower()),
            notification_frequency="immediate",
            user=user,
        )

    def _document(self, name):
        return Document.objects.create(
            initiative=self.initiative,
            document_type=self.doc_type,
            display_name=name,
        )

    def _row_for(self, document):
        return NotificationQueue.objects.get(document=document)


class AccessTests(EmailQueueTestBase):
    def test_obc_staff_sees_all_rows(self):
        # The contact must exist first so the upload signal enqueues a row.
        self._contact()
        pending_doc = self._document("Pending doc")
        sent_doc = self._document("Sent doc")
        cancelled_doc = self._document("Cancelled doc")

        # Build the three states.
        self._row_for(pending_doc)  # left pending
        NotificationQueue.objects.filter(document=sent_doc).update(
            sent_at=timezone.now()
        )
        NotificationQueue.objects.filter(document=cancelled_doc).update(
            cancelled_at=timezone.now()
        )

        self.client.force_login(self.staff)
        response = self.client.get(reverse("portal:obc_emails"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["rows"]), 3)

    def test_provider_denied(self):
        self.client.force_login(self.provider)
        response = self.client.get(reverse("portal:obc_emails"))
        self.assertEqual(response.status_code, 403)

    def test_contact_denied(self):
        self._contact(user=self.contact_user)
        self.client.force_login(self.contact_user)
        response = self.client.get(reverse("portal:obc_emails"))
        self.assertEqual(response.status_code, 403)

    def test_outsider_denied(self):
        self.client.force_login(self.outsider)
        response = self.client.get(reverse("portal:obc_emails"))
        self.assertEqual(response.status_code, 403)


class CancelActionTests(EmailQueueTestBase):
    def setUp(self):
        super().setUp()
        self._contact()

    def test_cancel_pending_row_sets_cancelled_at(self):
        document = self._document("To cancel")
        row = self._row_for(document)
        self.assertIsNone(row.cancelled_at)

        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("portal:obc_email_cancel", kwargs={"queue_id": row.pk})
        )

        self.assertEqual(response.status_code, 302)
        row.refresh_from_db()
        self.assertIsNotNone(row.cancelled_at)

    def test_cancel_keeps_document_and_stops_send(self):
        document = self._document("Keep me")
        row = self._row_for(document)

        self.client.force_login(self.staff)
        self.client.post(
            reverse("portal:obc_email_cancel", kwargs={"queue_id": row.pk})
        )

        # Document row untouched.
        self.assertTrue(Document.objects.filter(pk=document.pk).exists())
        # The drain sends nothing for the cancelled row.
        NotificationQueue.objects.filter(pk=row.pk).update(
            eligible_at=timezone.now() - timedelta(hours=1)
        )
        with override_settings(
            USE_MAILGUN=False,
            EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        ):
            self.assertEqual(notifications.send_pending_notifications(), 0)

    def test_cancel_sent_row_makes_no_change(self):
        document = self._document("Already sent")
        row = self._row_for(document)
        sent_time = timezone.now() - timedelta(days=1)
        NotificationQueue.objects.filter(pk=row.pk).update(sent_at=sent_time)

        self.client.force_login(self.staff)
        self.client.post(
            reverse("portal:obc_email_cancel", kwargs={"queue_id": row.pk})
        )

        row.refresh_from_db()
        self.assertIsNone(row.cancelled_at)
        self.assertIsNotNone(row.sent_at)

    def test_cancel_is_post_only(self):
        document = self._document("Get not allowed")
        row = self._row_for(document)
        self.client.force_login(self.staff)
        response = self.client.get(
            reverse("portal:obc_email_cancel", kwargs={"queue_id": row.pk})
        )
        self.assertEqual(response.status_code, 405)

    def test_provider_cannot_cancel(self):
        document = self._document("Provider blocked")
        row = self._row_for(document)
        self.client.force_login(self.provider)
        response = self.client.post(
            reverse("portal:obc_email_cancel", kwargs={"queue_id": row.pk})
        )
        self.assertEqual(response.status_code, 403)
        row.refresh_from_db()
        self.assertIsNone(row.cancelled_at)


@override_settings(
    USE_MAILGUN=False,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class ResendActionTests(EmailQueueTestBase):
    def setUp(self):
        super().setUp()
        self._contact()

    def test_resend_sent_row_sends_one_email_and_refreshes_sent_at(self):
        document = self._document("Resend me")
        row = self._row_for(document)
        old_sent = timezone.now() - timedelta(days=2)
        NotificationQueue.objects.filter(pk=row.pk).update(sent_at=old_sent)
        django_mail.outbox = []

        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("portal:obc_email_resend", kwargs={"queue_id": row.pk})
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(django_mail.outbox), 1)
        row.refresh_from_db()
        self.assertIsNotNone(row.sent_at)
        self.assertGreater(row.sent_at, old_sent)

    def test_resend_pending_row_makes_no_change(self):
        document = self._document("Not sent yet")
        row = self._row_for(document)
        django_mail.outbox = []

        self.client.force_login(self.staff)
        self.client.post(
            reverse("portal:obc_email_resend", kwargs={"queue_id": row.pk})
        )

        self.assertEqual(len(django_mail.outbox), 0)
        row.refresh_from_db()
        self.assertIsNone(row.sent_at)

    def test_resend_is_post_only(self):
        document = self._document("Get not allowed")
        row = self._row_for(document)
        NotificationQueue.objects.filter(pk=row.pk).update(
            sent_at=timezone.now()
        )
        self.client.force_login(self.staff)
        response = self.client.get(
            reverse("portal:obc_email_resend", kwargs={"queue_id": row.pk})
        )
        self.assertEqual(response.status_code, 405)

    def test_provider_cannot_resend(self):
        document = self._document("Provider blocked")
        row = self._row_for(document)
        NotificationQueue.objects.filter(pk=row.pk).update(
            sent_at=timezone.now()
        )
        django_mail.outbox = []
        self.client.force_login(self.provider)
        response = self.client.post(
            reverse("portal:obc_email_resend", kwargs={"queue_id": row.pk})
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(len(django_mail.outbox), 0)


class OrderingTests(EmailQueueTestBase):
    def setUp(self):
        super().setUp()
        self._contact()

    def test_rows_ordered_pending_first_then_newest(self):
        pending_doc = self._document("Pending")
        sent_doc = self._document("Sent")
        NotificationQueue.objects.filter(document=sent_doc).update(
            sent_at=timezone.now()
        )

        self.client.force_login(self.staff)
        response = self.client.get(reverse("portal:obc_emails"))

        rows = list(response.context["rows"])
        # Pending row must carry a smaller status sort key than the sent one.
        pending_row = next(
            r for r in rows if r.document_id == pending_doc.pk
        )
        sent_row = next(r for r in rows if r.document_id == sent_doc.pk)
        self.assertLess(pending_row.status_order, sent_row.status_order)
