"""Relabel the email-queue "Portal user" column as "Portal account".

0017_portal_email_queue_text seeded ``portal_th_user`` as "Portal user",
labelling the login account linked to a contact. Since the portal tiers
were renamed to "admins" and "super admins" (0028), "user" is stale
vocabulary and reads as if the column named a tier. Relabel it "Portal
account", which describes what the column actually shows: whether the
contact has a linked login account. Overwrites body/body_en/body_de
following the 0023 pattern.
"""

from django.db import migrations

LABEL_KEY = "portal_th_user"

BODY_EN = "Portal account"

BODY_DE = "Portal-Konto"


def relabel_portal_account(apps, schema_editor):
    SiteText = apps.get_model("cms", "SiteText")
    SiteText.objects.filter(key=LABEL_KEY).update(
        body=BODY_EN, body_en=BODY_EN, body_de=BODY_DE
    )


def noop_reverse(apps, schema_editor):
    """Deliberately a no-op -- see 0023 for the same reasoning: the
    pre-refresh copy isn't recorded anywhere a faithful reverse could
    read it back from, and unconditionally restoring the old label on
    reverse risks clobbering later edits made through the CMS.
    """


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0028_portal_admin_language"),
    ]

    operations = [
        migrations.RunPython(relabel_portal_account, noop_reverse)
    ]
