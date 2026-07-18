"""Behavioural tests for the OBC email-template editing interface.

The four portal notification emails are ``mail.EmailTemplate`` rows whose
``subject`` and ``body`` are translatable via ``django-modeltranslation``. OBC
staff can edit each language's copy through a portal screen; Providers and
Contacts must never reach it. Editing the ``de`` copy must not disturb the
``en`` copy (and vice versa), and the send path (``render_email``) must reflect
whatever copy is current for the active language.
"""

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import translation

from intrepid.models import SiteSetup
from mail.models import EmailTemplate
from portal.tests._helpers import clear_seed_data

PORTAL_TEMPLATE_NAMES = [
    "document_notification_immediate",
    "document_notification_digest",
    "contact_change_notification",
    "provider_invite",
]


class EmailTemplateEditTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        clear_seed_data()
        SiteSetup.objects.create(site_name="Test OBC")

        cls.templates = {}
        for name in PORTAL_TEMPLATE_NAMES:
            cls.templates[name] = EmailTemplate.objects.create(
                name=name,
                subject="Subject for {0}".format(name),
                body="<p>Body for {0}: {{{{ recipient }}}}</p>".format(name),
            )
        # A non-portal template that must not appear in the list.
        cls.other = EmailTemplate.objects.create(
            name="some_other_template",
            subject="Other",
            body="<p>other</p>",
        )

        cls.obc_group = Group.objects.create(name="OBC Team")
        cls.staff = User.objects.create_user("staff", password="pw")
        cls.staff.groups.add(cls.obc_group)
        cls.provider = User.objects.create_user("provider", password="pw")
        cls.outsider = User.objects.create_user("outsider", password="pw")

    def _immediate(self):
        return self.templates["document_notification_immediate"]

    # -- Access control ---------------------------------------------------

    def test_list_forbidden_for_non_staff(self):
        self.client.force_login(self.provider)
        resp = self.client.get(reverse("portal:obc_email_templates"))
        self.assertEqual(resp.status_code, 403)

    def test_edit_forbidden_for_non_staff(self):
        self.client.force_login(self.outsider)
        url = reverse(
            "portal:obc_email_template_edit",
            kwargs={"template_id": self._immediate().pk, "lang_code": "en"},
        )
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 403)

    # -- Listing ----------------------------------------------------------

    def test_list_shows_the_four_portal_templates(self):
        self.client.force_login(self.staff)
        resp = self.client.get(reverse("portal:obc_email_templates"))
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        for name in PORTAL_TEMPLATE_NAMES:
            self.assertIn(name, content)
        # The unrelated template is not offered for editing here.
        self.assertNotIn("some_other_template", content)

    # -- Editing English --------------------------------------------------

    def test_post_en_updates_english_columns(self):
        self.client.force_login(self.staff)
        template = self._immediate()
        url = reverse(
            "portal:obc_email_template_edit",
            kwargs={"template_id": template.pk, "lang_code": "en"},
        )
        resp = self.client.post(
            url,
            {
                "subject": "Edited EN subject",
                "body": "<p>Edited EN body {{ recipient }}</p>",
            },
        )
        self.assertIn(resp.status_code, (200, 302))
        template.refresh_from_db()
        self.assertEqual(template.subject_en, "Edited EN subject")
        self.assertEqual(
            template.body_en, "<p>Edited EN body {{ recipient }}</p>"
        )

    # -- Editing German leaves English untouched --------------------------

    def test_post_de_updates_german_and_leaves_english_alone(self):
        self.client.force_login(self.staff)
        template = self._immediate()
        original_subject_en = template.subject_en
        original_body_en = template.body_en

        url = reverse(
            "portal:obc_email_template_edit",
            kwargs={"template_id": template.pk, "lang_code": "de"},
        )
        resp = self.client.post(
            url,
            {
                "subject": "Betreff auf Deutsch",
                "body": "<p>Deutscher Text {{ recipient }}</p>",
            },
        )
        self.assertIn(resp.status_code, (200, 302))
        template.refresh_from_db()
        self.assertEqual(template.subject_de, "Betreff auf Deutsch")
        self.assertEqual(
            template.body_de, "<p>Deutscher Text {{ recipient }}</p>"
        )
        # English columns are untouched.
        self.assertEqual(template.subject_en, original_subject_en)
        self.assertEqual(template.body_en, original_body_en)

    # -- render_email reflects the edited body ----------------------------

    def test_render_email_reflects_edited_body(self):
        self.client.force_login(self.staff)
        template = self._immediate()
        url = reverse(
            "portal:obc_email_template_edit",
            kwargs={"template_id": template.pk, "lang_code": "en"},
        )
        self.client.post(
            url,
            {
                "subject": "Edited",
                "body": "Hello {{ recipient }} from EN",
            },
        )
        template.refresh_from_db()
        with translation.override("en"):
            rendered = template.render_email({"recipient": "Ada"})
        self.assertEqual(rendered, "Hello Ada from EN")

    def test_render_email_uses_language_specific_body(self):
        self.client.force_login(self.staff)
        template = self._immediate()
        de_url = reverse(
            "portal:obc_email_template_edit",
            kwargs={"template_id": template.pk, "lang_code": "de"},
        )
        self.client.post(
            de_url,
            {"subject": "DE", "body": "Hallo {{ recipient }} auf Deutsch"},
        )
        template.refresh_from_db()
        with translation.override("de"):
            rendered = template.render_email({"recipient": "Ada"})
        self.assertEqual(rendered, "Hallo Ada auf Deutsch")

    # -- Invalid language rejected ---------------------------------------

    def test_invalid_lang_code_rejected(self):
        self.client.force_login(self.staff)
        url = reverse(
            "portal:obc_email_template_edit",
            kwargs={
                "template_id": self._immediate().pk,
                "lang_code": "fr",
            },
        )
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)

    def test_non_portal_template_not_editable(self):
        # A template that is not one of the four portal templates must not be
        # reachable through this interface, even by a staff member crafting the
        # URL with its primary key.
        self.client.force_login(self.staff)
        url = reverse(
            "portal:obc_email_template_edit",
            kwargs={"template_id": self.other.pk, "lang_code": "en"},
        )
        get_resp = self.client.get(url)
        self.assertEqual(get_resp.status_code, 404)

        post_resp = self.client.post(
            url, {"subject": "Hacked", "body": "<p>hacked</p>"}
        )
        self.assertEqual(post_resp.status_code, 404)
        # The non-portal template is left untouched.
        self.other.refresh_from_db()
        self.assertEqual(self.other.subject_en, "Other")


class SeededTemplateRenderAfterMigrationTests(TestCase):
    """The data migration must keep the seeded send path working.

    After registering modeltranslation, ``render_email`` reads the active
    language's ``body`` column with a fallback. The 0004 seed data lives only in
    the untranslated ``body`` field until the 0003 data migration copies it into
    ``body_en``. This proves a seeded template still renders once migrated.
    """

    def test_seeded_template_still_renders(self):
        # The seed migration (portal 0004) created the four templates and the
        # mail 0003 data migration populated body_en. Both have run against the
        # test database, so the seeded rows must render via the en column.
        template = EmailTemplate.objects.get(
            name="document_notification_immediate"
        )
        self.assertTrue(template.body_en)
        with translation.override("en"):
            rendered = template.render_email(
                {"recipient": "Ada", "document": None, "documents": []}
            )
        # Rendering must not raise and must return the (non-empty) seeded body.
        self.assertTrue(rendered)
