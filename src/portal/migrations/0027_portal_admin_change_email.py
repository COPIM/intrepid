"""Seed the provider_admin_change email template.

Whenever a Provider admin is added to or removed from ``initiative.users``,
the portal emails the Provider's other admins and the OBC staff so an
unexpected change is noticed. This migration seeds the English and German
copy for that email; the body renders differently for the "added" and
"removed" cases via a template conditional.
"""

from django.db import migrations

TEMPLATE_NAME = "provider_admin_change"

SUBJECT_EN = "Admin change for {{ initiative.name }}"
SUBJECT_DE = "Änderung der Admins für {{ initiative.name }}"

BODY_FALLBACK_EN = (
    "<p>{{ admin_label }} was "
    '{% if action == "added" %}added as{% else %}removed as{% endif %} '
    "an admin for {{ initiative.name }}.</p>"
    "<p>If you didn't request this change, please either log in to manage "
    'your admins or contact the OBC.</p><p><a href="{{ url }}">'
    "{{ url }}</a></p>"
)

BODY_DE = """<p>Guten Tag,</p>

{% if action == "added" %}
<p>{{ admin_label }} wurde als Admin für {{ initiative.name }} im
Dokumentenportal des Open Book Collective hinzugefügt.</p>
{% else %}
<p>{{ admin_label }} wurde als Admin für {{ initiative.name }} im
Dokumentenportal des Open Book Collective entfernt.</p>
{% endif %}

<p>Wenn Sie diese Änderung nicht veranlasst haben, melden Sie sich bitte an,
um Ihre Admins zu verwalten, oder wenden Sie sich an das OBC.</p>

<p>
    <a href="{{ url }}" style="display:inline-block;background:#151462;color:#ffffff;text-decoration:none;padding:12px 24px;border-radius:6px;font-weight:bold;">Admins verwalten</a>
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
        "portal/emails/provider_admin_change.html", BODY_FALLBACK_EN
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
        ("portal", "0026_portal_unified_invite"),
        ("mail", "0002_emailtemplate_translation_fields"),
    ]

    operations = [migrations.RunPython(seed, unseed)]
