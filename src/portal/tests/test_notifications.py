"""Tests for the portal notification queue, digest grouping and cron drain.

Creating a Document enqueues notifications via a post_save signal, so the tests
create the contacts first and then the document, exercising the real path.
"""

import builtins
import os
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.core import mail as django_mail
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from initiatives.models import Initiative
from mail.models import EmailTemplate
from portal import notifications
from portal.tests._helpers import clear_seed_data
from portal.tests.test_views import StorageRedirectMixin
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

    def test_one_group_send_failure_does_not_abort_the_drain(self):
        """A send failure for one recipient's group (e.g. an attachment file

        vanishing between the existence check and the actual open) must not
        stop other due groups from being sent in the same drain. The failed
        group's rows must be left unsent so a later drain retries them.
        """
        good_contact = self._contact("daily", first="Good")
        bad_contact = self._contact("daily", first="Bad")
        self._document("Shared upload")
        self._set_due(NotificationQueue.objects.filter(recipient=good_contact))
        self._set_due(NotificationQueue.objects.filter(recipient=bad_contact))

        def fake_send_email(
            to, subject=None, html=None, from_email=None, bcc=None,
            attachments=None,
        ):
            if bad_contact.email in to:
                raise OSError("attachment file vanished mid-send")
            return 1

        with patch(
            "mail.models.EmailTemplate._send_email",
            side_effect=fake_send_email,
        ):
            emails = notifications.send_pending_notifications()

        self.assertEqual(emails, 1)
        self.assertIsNotNone(
            NotificationQueue.objects.get(recipient=good_contact).sent_at
        )
        self.assertIsNone(
            NotificationQueue.objects.get(recipient=bad_contact).sent_at
        )


@override_settings(
    USE_MAILGUN=False,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class CancelDrainRaceTests(NotificationTestBase):
    """A cancellation landing after selection but before send must win.

    The drain selects the pending rows up front. If an admin cancels a row in
    that window, the drain must not send or mark that row as sent.
    """

    def test_cancellation_between_selection_and_send_is_honoured(self):
        canceller = self._contact("daily", first="Canceller")
        victim = self._contact("daily", first="Victim")
        self._document("Shared upload")

        canceller_rows = NotificationQueue.objects.filter(recipient=canceller)
        victim_rows = NotificationQueue.objects.filter(recipient=victim)
        # Deterministic order: the canceller's group is drained first.
        self._set_due(canceller_rows, when=timezone.now() - timedelta(hours=2))
        self._set_due(victim_rows, when=timezone.now() - timedelta(hours=1))

        real_send_group = notifications._send_group

        def send_group_side_effect(recipient, frequency, documents):
            if recipient.pk == canceller.pk:
                # The cancellation lands here: after the drain selected the
                # victim's row, before that row is sent.
                NotificationQueue.objects.filter(recipient=victim).update(
                    cancelled_at=timezone.now()
                )
            return real_send_group(recipient, frequency, documents)

        django_mail.outbox = []
        with patch.object(
            notifications, "_send_group", side_effect=send_group_side_effect
        ):
            emails = notifications.send_pending_notifications()

        # Only the canceller's email went out.
        self.assertEqual(emails, 1)
        recipients_emailed = [addr for m in django_mail.outbox for addr in m.to]
        self.assertIn(canceller.email, recipients_emailed)
        self.assertNotIn(victim.email, recipients_emailed)

        # The victim's row is cancelled and was never marked sent.
        victim_row = victim_rows.get()
        self.assertIsNone(victim_row.sent_at)
        self.assertIsNotNone(victim_row.cancelled_at)


@override_settings(
    USE_MAILGUN=False,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class LanguagePreferenceSendTests(NotificationTestBase):
    """A contact's ``language`` selects which translated EmailTemplate copy is
    rendered at send time, with an English fallback."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        imm = EmailTemplate.objects.get(
            name="document_notification_immediate"
        )
        imm.subject_en = "New document (EN)"
        imm.subject_de = "Neues Dokument (DE)"
        imm.body_en = "English body {{ document.display_name }}"
        imm.body_de = "Deutscher Text {{ document.display_name }}"
        imm.save()
        dig = EmailTemplate.objects.get(name="document_notification_digest")
        dig.subject_en = "Digest (EN)"
        dig.subject_de = "Zusammenfassung (DE)"
        dig.body_en = (
            "English digest "
            "{% for d in documents %}[{{ d.display_name }}]{% endfor %}"
        )
        dig.body_de = (
            "Deutsche Zusammenfassung "
            "{% for d in documents %}[{{ d.display_name }}]{% endfor %}"
        )
        dig.save()

    def _contact_lang(self, frequency, language, first):
        contact = self._contact(frequency, first=first)
        contact.language = language
        contact.save()
        return contact

    def test_immediate_de_contact_gets_german_body_and_subject(self):
        contact = self._contact_lang("immediate", "de", "De")
        self._document("March remittance")
        self._set_due(NotificationQueue.objects.filter(recipient=contact))

        notifications.send_pending_notifications()

        self.assertEqual(len(django_mail.outbox), 1)
        sent = django_mail.outbox[0]
        self.assertIn("Deutscher Text", sent.body)
        self.assertEqual(sent.subject, "Neues Dokument (DE)")

    def test_immediate_en_contact_gets_english_body_and_subject(self):
        contact = self._contact_lang("immediate", "en", "En")
        self._document("March remittance")
        self._set_due(NotificationQueue.objects.filter(recipient=contact))

        notifications.send_pending_notifications()

        self.assertEqual(len(django_mail.outbox), 1)
        sent = django_mail.outbox[0]
        self.assertIn("English body", sent.body)
        self.assertEqual(sent.subject, "New document (EN)")

    def test_de_contact_with_empty_de_copy_falls_back_to_english(self):
        imm = EmailTemplate.objects.get(
            name="document_notification_immediate"
        )
        imm.subject_de = ""
        imm.body_de = ""
        imm.save()
        contact = self._contact_lang("immediate", "de", "Fb")
        self._document("March remittance")
        self._set_due(NotificationQueue.objects.filter(recipient=contact))

        notifications.send_pending_notifications()

        self.assertEqual(len(django_mail.outbox), 1)
        sent = django_mail.outbox[0]
        self.assertIn("English body", sent.body)
        self.assertEqual(sent.subject, "New document (EN)")

    def test_digest_de_contact_renders_german(self):
        contact = self._contact_lang("daily", "de", "Dig")
        for n in range(2):
            self._document("Doc {0}".format(n))
        self._set_due(NotificationQueue.objects.filter(recipient=contact))

        notifications.send_pending_notifications()

        self.assertEqual(len(django_mail.outbox), 1)
        sent = django_mail.outbox[0]
        self.assertIn("Deutsche Zusammenfassung", sent.body)
        self.assertEqual(sent.subject, "Zusammenfassung (DE)")

    def test_resend_row_honours_contact_language(self):
        contact = self._contact_lang("immediate", "de", "Re")
        self._document("Resend me")
        row = NotificationQueue.objects.get(recipient=contact)
        django_mail.outbox = []

        notifications.resend_row(row)

        self.assertEqual(len(django_mail.outbox), 1)
        self.assertIn("Deutscher Text", django_mail.outbox[0].body)
        self.assertEqual(
            django_mail.outbox[0].subject, "Neues Dokument (DE)"
        )

    def test_blank_language_does_not_crash_and_uses_english(self):
        contact = self._contact_lang("immediate", "", "Blank")
        self._document("March remittance")
        self._set_due(NotificationQueue.objects.filter(recipient=contact))

        notifications.send_pending_notifications()

        self.assertEqual(len(django_mail.outbox), 1)
        self.assertIn("English body", django_mail.outbox[0].body)


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


class AttachmentTestBase(StorageRedirectMixin, NotificationTestBase):
    """Base for attachment tests: real files on disk under a temp storage dir."""

    def _document_with_file(self, name, content=b"file-bytes", filename=None):
        filename = filename or "{0}.pdf".format(name.replace(" ", "_"))
        document = Document(
            initiative=self.initiative,
            document_type=self.doc_type,
            display_name=name,
        )
        document.file.save(filename, ContentFile(content), save=True)
        return document


@override_settings(
    USE_MAILGUN=False,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class LocalBackendAttachmentTests(AttachmentTestBase):
    """Attachment behaviour on the plain-Django (non-Mailgun) send branch."""

    def test_immediate_notification_attaches_document_file(self):
        contact = self._contact("immediate")
        self._document_with_file("Immediate doc", content=b"immediate-bytes")
        self._set_due(NotificationQueue.objects.filter(recipient=contact))

        emails = notifications.send_pending_notifications()

        self.assertEqual(emails, 1)
        self.assertEqual(len(django_mail.outbox), 1)
        sent = django_mail.outbox[0]
        self.assertEqual(len(sent.attachments), 1)
        _name, content, _ctype = sent.attachments[0]
        self.assertEqual(content, b"immediate-bytes")

    def test_digest_attaches_every_grouped_document_file(self):
        contact = self._contact("daily")
        for n in range(3):
            self._document_with_file(
                "Digest {0}".format(n),
                content="content-{0}".format(n).encode(),
            )
        self._set_due(NotificationQueue.objects.filter(recipient=contact))

        emails = notifications.send_pending_notifications()

        self.assertEqual(emails, 1)
        self.assertEqual(len(django_mail.outbox), 1)
        sent = django_mail.outbox[0]
        self.assertEqual(len(sent.attachments), 3)
        attached_contents = {
            content for _name, content, _ctype in sent.attachments
        }
        for n in range(3):
            self.assertIn("content-{0}".format(n).encode(), attached_contents)

    def test_missing_file_on_disk_is_skipped_without_crashing(self):
        contact = self._contact("daily")
        self._document_with_file("Present", content=b"present-bytes")
        missing = self._document_with_file("Missing", content=b"missing-bytes")
        os.remove(missing.file.path)
        self._set_due(NotificationQueue.objects.filter(recipient=contact))

        emails = notifications.send_pending_notifications()

        self.assertEqual(emails, 1)
        self.assertEqual(len(django_mail.outbox), 1)
        sent = django_mail.outbox[0]
        self.assertEqual(len(sent.attachments), 1)
        _name, content, _ctype = sent.attachments[0]
        self.assertEqual(content, b"present-bytes")

    def test_document_without_a_file_does_not_crash_cron_drain(self):
        contact = self._contact("immediate")
        self._document("No file doc")  # base helper: never sets a file
        self._set_due(NotificationQueue.objects.filter(recipient=contact))

        call_command("send_document_notifications")

        self.assertEqual(len(django_mail.outbox), 1)
        self.assertEqual(len(django_mail.outbox[0].attachments), 0)


@override_settings(USE_MAILGUN=True)
class MailgunAttachmentTests(AttachmentTestBase):
    """The Mailgun branch must close its attachment file handles after POST."""

    @patch("mail.models.requests.post")
    def test_attachment_file_handles_closed_after_post(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "abc123"}
        mock_post.return_value = mock_response

        contact = self._contact("immediate")
        self._document_with_file("Mailgun doc", content=b"mailgun-bytes")
        self._set_due(NotificationQueue.objects.filter(recipient=contact))

        notifications.send_pending_notifications()

        self.assertEqual(mock_post.call_count, 1)
        sent_files = mock_post.call_args.kwargs["files"]
        self.assertEqual(len(sent_files), 1)
        _field_name, file_handle = sent_files[0]
        self.assertTrue(file_handle.closed)

    @patch("mail.models.requests.post")
    def test_missing_file_skipped_on_mailgun_branch_too(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "abc123"}
        mock_post.return_value = mock_response

        contact = self._contact("daily")
        self._document_with_file("Present", content=b"present-bytes")
        missing = self._document_with_file("Missing", content=b"missing-bytes")
        os.remove(missing.file.path)
        self._set_due(NotificationQueue.objects.filter(recipient=contact))

        emails = notifications.send_pending_notifications()

        self.assertEqual(emails, 1)
        sent_files = mock_post.call_args.kwargs["files"]
        self.assertEqual(len(sent_files), 1)

    @patch("mail.models.requests.post")
    def test_open_failure_mid_loop_closes_already_opened_handles(
        self, mock_post
    ):
        """If the second of three attachments fails to open, the handle
        already opened for the first attachment must still be closed, and
        Mailgun must never be posted to with a partial/broken file list."""
        doc1 = self._document_with_file("First", content=b"first-bytes")
        doc2 = self._document_with_file("Second", content=b"second-bytes")
        doc3 = self._document_with_file("Third", content=b"third-bytes")

        opened_handles = []
        real_open = builtins.open

        def flaky_open(path, *args, **kwargs):
            if path == doc2.file.path:
                raise OSError("simulated failure opening the second attachment")
            handle = real_open(path, *args, **kwargs)
            opened_handles.append(handle)
            return handle

        with patch("mail.models.open", side_effect=flaky_open):
            with self.assertRaises(OSError):
                EmailTemplate()._send_email(
                    to="someone@example.com",
                    subject="Subject",
                    html="<p>Body</p>",
                    attachments=[
                        doc1.file.path,
                        doc2.file.path,
                        doc3.file.path,
                    ],
                )

        self.assertEqual(len(opened_handles), 1)
        self.assertTrue(opened_handles[0].closed)
        mock_post.assert_not_called()
