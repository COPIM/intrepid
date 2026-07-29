"""Behavioural tests for the get_site_text template tag.

The tag caches SiteText rows per request, but it must also work in
templates rendered without a request in context (password-reset emails,
management commands, background tasks), where it should still resolve
texts and avoid issuing one query per tag.
"""

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core import mail
from django.template import Context, Template
from django.test import TestCase
from django.test.client import RequestFactory
from django.urls import reverse

from cms.models import SiteText
from intrepid.models import SiteSetup


def render_template(source, context=None):
    return Template(source).render(Context(context or {}))


class GetSiteTextWithoutRequestTests(TestCase):
    """The tag must not require a request in the template context."""

    @classmethod
    def setUpTestData(cls):
        SiteText.objects.create(
            key="email_greeting",
            body="Dear",
            help_text="Greeting used at the top of emails.",
        )
        SiteText.objects.create(
            key="username_reminder",
            body="Your username is:",
            help_text="Reminder line in the password reset email.",
        )

    def test_renders_text_without_request_in_context(self):
        rendered = render_template("{% get_site_text 'email_greeting' %}")
        self.assertEqual(rendered, "Dear")

    def test_unknown_key_without_request_returns_marker(self):
        rendered = render_template("{% get_site_text 'no_such_key' %}")
        self.assertEqual(rendered, "!!no_such_key")

    def test_single_query_for_multiple_tags_without_request(self):
        source = (
            "{% get_site_text 'email_greeting' %} "
            "{% get_site_text 'username_reminder' %}"
        )
        with self.assertNumQueries(1):
            rendered = render_template(source)
        self.assertEqual(rendered, "Dear Your username is:")


class GetSiteTextWithRequestTests(TestCase):
    """The existing per-request caching behaviour must be preserved."""

    def setUp(self):
        self.request = RequestFactory().get("/")
        SiteText.objects.create(
            key="email_greeting",
            body="Dear",
            help_text="Greeting used at the top of emails.",
        )

    def test_renders_text_with_request_in_context(self):
        rendered = render_template(
            "{% get_site_text 'email_greeting' %}",
            {"request": self.request},
        )
        self.assertEqual(rendered, "Dear")

    def test_texts_are_cached_on_the_request(self):
        context = {"request": self.request}
        render_template("{% get_site_text 'email_greeting' %}", context)

        # A change in the database must not be visible through the same
        # request: the first render's snapshot is reused.
        SiteText.objects.filter(key="email_greeting").update(body="Hello")
        with self.assertNumQueries(0):
            rendered = render_template(
                "{% get_site_text 'email_greeting' %}", context
            )
        self.assertEqual(rendered, "Dear")


class PasswordResetEmailTests(TestCase):
    """End-to-end reproduction of the 500 in the password reset flow."""

    @classmethod
    def setUpTestData(cls):
        SiteSetup.objects.get_or_create(defaults={"site_name": "Test OBC"})
        Site.objects.get_or_create(
            pk=settings.SITE_ID,
            defaults={"domain": "testserver", "name": "testserver"},
        )
        cls.user = User.objects.create_user(
            "reset-user", email="reset-user@example.com", password="pw"
        )

    def test_password_reset_sends_email(self):
        response = self.client.post(
            reverse("password_reset"),
            {"email": "reset-user@example.com"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
