"""Tests for the portal notification queue, digest grouping and cron drain.

Creating a Document enqueues notifications via a post_save signal, so the tests
create the contacts first and then the document, exercising the real path.
"""

from datetime import timedelta
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from initiatives.models import Initiative
from mail.models import EmailTemplate
from portal import notifications
from portal.tests._helpers import clear_seed_data
from portal.models import (
    Document,
    DocumentType,
    NotificationQueue,
    ProviderContact,
)


class NotificationTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        clear_seed_data()
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

    def _contact(self, frequency, first="A"):
        return ProviderContact.objects.create(
            initiative=self.initiative,
            first_name=first,
            last_name="Person",
            email="{0}@example.com".format(first.lower()),
            notification_frequency=frequency,
        )

    def _document(self, name):
        return Document.objects.create(
            initiative=self.initiative,
            document_type=self.doc_type,
            display_name=name,
        )

    def _set_due(self, queryset, when=None):
        queryset.update(
            eligible_at=when or (timezone.now() - timedelta(hours=1))
        )


class EnqueueTests(NotificationTestBase):
    def test_one_row_per_active_contact(self):
        self._contact("immediate", first="Imm")
        self._contact("daily", first="Day")
        self._contact("off", first="Off")

        document = self._document("March remittance")

        rows = NotificationQueue.objects.filter(document=document)
        self.assertEqual(rows.count(), 2)  # "off" excluded
        self.assertEqual(
            set(rows.values_list("frequency", flat=True)),
            {"immediate", "daily"},
        )

    def test_immediate_eligible_at_matches_document_grace(self):
        contact = self._contact("immediate")
        document = self._document("March remittance")

        row = NotificationQueue.objects.get(recipient=contact)
        self.assertEqual(row.eligible_at, document.notification_eligible_at)

    def test_off_contact_not_enqueued(self):
        self._contact("off")
        self._document("March remittance")
        self.assertEqual(NotificationQueue.objects.count(), 0)


class SignalTests(NotificationTestBase):
    def test_creating_document_enqueues_via_signal(self):
        self._contact("immediate")
        document = self._document("Auto enqueued")
        self.assertEqual(
            NotificationQueue.objects.filter(document=document).count(), 1
        )

    def test_bulk_silent_document_does_not_enqueue(self):
        self._contact("immediate")
        document = Document(
            initiative=self.initiative,
            document_type=self.doc_type,
            display_name="Silent",
        )
        document._suppress_notifications = True
        document.save()
        self.assertEqual(
            NotificationQueue.objects.filter(document=document).count(), 0
        )


class CancelTests(NotificationTestBase):
    @patch("mail.models.EmailTemplate._send_email", return_value=1)
    def test_cancel_marks_rows_and_prevents_send(self, mock_send):
        contact = self._contact("immediate")
        document = self._document("To be cancelled")
        self._set_due(NotificationQueue.objects.filter(document=document))

        notifications.cancel_for_document(document)

        row = NotificationQueue.objects.get(recipient=contact)
        self.assertIsNotNone(row.cancelled_at)
        self.assertEqual(notifications.send_pending_notifications(), 0)

    @patch("mail.models.EmailTemplate._send_email", return_value=1)
    def test_deleting_document_prevents_send(self, mock_send):
        self._contact("immediate")
        document = self._document("To be deleted")
        self._set_due(NotificationQueue.objects.filter(document=document))

        document.delete()

        self.assertEqual(NotificationQueue.objects.count(), 0)
        self.assertEqual(notifications.send_pending_notifications(), 0)


class DrainTests(NotificationTestBase):
    @patch("mail.models.EmailTemplate._send_email", return_value=1)
    def test_drain_marks_rows_sent(self, mock_send):
        contact = self._contact("daily")
        self._document("March remittance")
        self._set_due(NotificationQueue.objects.filter(recipient=contact))

        emails = notifications.send_pending_notifications()

        self.assertEqual(emails, 1)
        self.assertIsNotNone(
            NotificationQueue.objects.get(recipient=contact).sent_at
        )

    @patch("mail.models.EmailTemplate._send_email", return_value=1)
    def test_daily_digest_groups_documents_into_one_email(self, mock_send):
        contact = self._contact("daily")
        docs = [self._document("Doc {0}".format(n)) for n in range(3)]
        # All three share the daily window: force the same past eligible time.
        self._set_due(NotificationQueue.objects.filter(recipient=contact))

        emails = notifications.send_pending_notifications()

        self.assertEqual(emails, 1)  # one digest email
        sent_html = "".join(
            call.kwargs["html"] for call in mock_send.call_args_list
        )
        for doc in docs:
            self.assertIn(doc.display_name, sent_html)
        self.assertEqual(
            NotificationQueue.objects.filter(
                recipient=contact, sent_at__isnull=False
            ).count(),
            3,
        )

    @patch("mail.models.EmailTemplate._send_email", return_value=1)
    def test_immediate_documents_send_individually(self, mock_send):
        contact = self._contact("immediate")
        for n in range(3):
            self._document("Imm {0}".format(n))
        # Give each immediate row a distinct past eligible time.
        for i, row in enumerate(
            NotificationQueue.objects.filter(recipient=contact)
        ):
            row.eligible_at = timezone.now() - timedelta(hours=1, seconds=i)
            row.save()

        emails = notifications.send_pending_notifications()

        self.assertEqual(emails, 3)

    @patch("mail.models.EmailTemplate._send_email", return_value=1)
    def test_future_rows_not_sent(self, mock_send):
        contact = self._contact("daily")
        self._document("Not yet due")
        self._set_due(
            NotificationQueue.objects.filter(recipient=contact),
            when=timezone.now() + timedelta(days=1),
        )
        self.assertEqual(notifications.send_pending_notifications(), 0)


class CommandTests(NotificationTestBase):
    @patch("mail.models.EmailTemplate._send_email", return_value=1)
    def test_command_drains_due_rows(self, mock_send):
        contact = self._contact("daily")
        self._document("March remittance")
        self._set_due(NotificationQueue.objects.filter(recipient=contact))

        call_command("send_document_notifications")

        self.assertIsNotNone(
            NotificationQueue.objects.get(recipient=contact).sent_at
        )
