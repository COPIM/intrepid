"""Site-wide language activation.

The EN/DE switcher posts to Django's ``set_language`` view, which stores the
choice in the ``django_language`` cookie/session. These tests pin the other
half of the contract: subsequent requests must actually be served in the
chosen language. This requires ``django.middleware.locale.LocaleMiddleware``
in ``MIDDLEWARE`` — a git-ignored settings concern, so this test guards
against the settings drift that once silently disabled switching.
"""

from django.conf import settings
from django.test import TestCase

from intrepid.models import SiteSetup


class LanguageActivationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        SiteSetup.objects.get_or_create(defaults={"site_name": "Test OBC"})

    def test_language_cookie_activates_german(self):
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "de"
        response = self.client.get("/portal/")
        self.assertEqual(response.headers.get("Content-Language"), "de")

    def test_without_cookie_default_language_applies(self):
        response = self.client.get("/portal/")
        self.assertEqual(response.headers.get("Content-Language"), "en")
