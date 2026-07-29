"""Behavioural tests for the dashboard translation screen (list_site_text).

Covers the staff-only guard, that portal-prefixed SiteText rows reach the
page, and that the quick-filter controls used to jump straight to the
portal's strings are present with stable, JS-hookable ids.
"""

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from cms.models import SiteText
from intrepid.models import SiteSetup


class ListSiteTextViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        SiteSetup.objects.get_or_create(defaults={"site_name": "Test OBC"})
        cls.staff_user = User.objects.create_user(
            "site-text-staff", password="pw", is_staff=True
        )
        cls.regular_user = User.objects.create_user(
            "site-text-regular", password="pw", is_staff=False
        )
        cls.portal_text = SiteText.objects.create(
            key="portal_qa_probe_apple",
            body="Apple probe",
            body_en="Apple probe",
            help_text="A portal-prefixed probe row for tests.",
        )
        cls.non_portal_text = SiteText.objects.create(
            key="cms_qa_probe_banana",
            body="Banana probe",
            body_en="Banana probe",
            help_text="A non-portal probe row for tests.",
        )

    def test_anonymous_user_is_redirected(self):
        response = self.client.get(reverse("list_site_text"))
        self.assertEqual(response.status_code, 302)

    def test_non_staff_user_is_redirected(self):
        self.client.login(username="site-text-regular", password="pw")
        response = self.client.get(reverse("list_site_text"))
        self.assertEqual(response.status_code, 302)

    def test_staff_user_gets_200(self):
        self.client.login(username="site-text-staff", password="pw")
        response = self.client.get(reverse("list_site_text"))
        self.assertEqual(response.status_code, 200)

    def test_context_includes_portal_prefixed_site_text(self):
        self.client.login(username="site-text-staff", password="pw")
        response = self.client.get(reverse("list_site_text"))
        site_texts = list(response.context["site_texts"])
        self.assertIn(self.portal_text, site_texts)
        self.assertIn(self.non_portal_text, site_texts)
        portal_keys = [t.key for t in site_texts if t.key.startswith("portal_")]
        self.assertIn(self.portal_text.key, portal_keys)

    def test_rendered_page_lists_portal_prefixed_key(self):
        self.client.login(username="site-text-staff", password="pw")
        response = self.client.get(reverse("list_site_text"))
        self.assertContains(response, self.portal_text.key)
        self.assertContains(response, self.non_portal_text.key)

    def test_quick_filter_controls_present_by_stable_id(self):
        self.client.login(username="site-text-staff", password="pw")
        response = self.client.get(reverse("list_site_text"))
        self.assertContains(response, 'id="site-text-filter-all"')
        self.assertContains(response, 'id="site-text-filter-portal"')
