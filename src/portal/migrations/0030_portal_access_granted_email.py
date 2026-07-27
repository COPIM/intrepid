"""Seed the provider_access_granted email template.

When invite-by-email matches an existing, working account, that person is
added straight to ``initiative.users`` with no invitation email. This
template tells them it happened: they now have admin access to the Provider
on the OBC document portal, with a sign-in link. This migration seeds the
English and German copy for that email.
"""

from django.db import migrations

TEMPLATE_NAME = "provider_access_granted"

SUBJECT_EN = "You now have access to {{ initiative.name }}"
SUBJECT_DE = "Sie haben jetzt Zugriff auf {{ initiative.name }}"

BODY_FALLBACK_EN = (
    "<p>You have been given admin access to {{ initiative.name }} on the "
    "Open Book Collective document portal.</p>"
    "<p>Sign in with your existing account details to view and manage "
    '{{ initiative.name }}.</p><p><a href="{{ url }}">{{ url }}</a></p>'
)

BODY_DE = """<p>Guten Tag,</p>

<p>Sie haben Admin-Zugriff auf {{ initiative.name }} im Dokumentenportal des
Open Book Collective erhalten.</p>

<p>Melden Sie sich bitte mit Ihren bestehenden Zugangsdaten an, um
{{ initiative.name }} einzusehen und zu verwalten.</p>

<p>
    <a href="{{ url }}" style="display:inline-block;background:#151462;color:#ffffff;text-decoration:none;padding:12px 24px;border-radius:6px;font-weight:bold;">Anmelden</a>
</p>

<p>Falls die Schaltfläche nicht funktioniert, kopieren Sie bitte diesen Link
in Ihren Browser:<br>
<a href="{{ url }}">{{ url }}</a></p>
"""


def _template_body(path, fallback):
    try:
        from django.template.loader import get_template

        return get_template(path).template.source
    except Exception:
        return fallback


def seed(apps, schema_editor):
    EmailTemplate = apps.get_model("mail", "EmailTemplate")
    body_en = _template_body(
        "portal/emails/provider_access_granted.html", BODY_FALLBACK_EN
    )
    EmailTemplate.objects.get_or_create(
        name=TEMPLATE_NAME,
        defaults={
            "subject": SUBJECT_EN,
            "subject_en": SUBJECT_EN,
            "subject_de": SUBJECT_DE,
            "body": body_en,
            "body_en": body_en,
            "body_de": BODY_DE,
        },
    )


def unseed(apps, schema_editor):
    EmailTemplate = apps.get_model("mail", "EmailTemplate")
    EmailTemplate.objects.filter(name=TEMPLATE_NAME).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0029_portal_account_label"),
        ("mail", "0002_emailtemplate_translation_fields"),
    ]

    operations = [migrations.RunPython(seed, unseed)]
