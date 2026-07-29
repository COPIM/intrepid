"""Refresh the portal dashboard and staff-access SiteText copy.

Three copy changes to the rows seeded by 0005_portal_site_text and
0008_portal_text_phase2:

* ``portal_dashboard_title`` -- "OBC document dashboard" becomes
  "OBC document portal dashboard".
* ``portal_dashboard_intro`` -- the introductory paragraph is removed from
  the portal homepage altogether (the template no longer renders it), so
  the now-orphaned row is deleted.
* ``portal_staff_subhint`` and ``portal_tile_staff_desc`` -- the hint
  "Choose which users can access the OBC backend." is expanded to explain
  who backend access is for and what it grants.

Overwrites body/body_en/body_de following the 0023 pattern.
"""

from django.db import migrations

TITLE_KEY = "portal_dashboard_title"
INTRO_KEY = "portal_dashboard_intro"
STAFF_HINT_KEYS = ("portal_staff_subhint", "portal_tile_staff_desc")

TITLE_EN = "OBC document portal dashboard"
TITLE_DE = "Dashboard des OBC-Dokumentenportals"

STAFF_HINT_EN = (
    "Choose which OBC staff and collaborators can access the OBC backend, "
    "to manage all site-wide functions."
)
STAFF_HINT_DE = (
    "Wählen Sie aus, welche OBC-Mitarbeiter und Kooperationspartner auf "
    "das OBC-Backend zugreifen können, um alle websiteweiten Funktionen "
    "zu verwalten."
)


def refresh_portal_text(apps, schema_editor):
    SiteText = apps.get_model("cms", "SiteText")
    SiteText.objects.filter(key=TITLE_KEY).update(
        body=TITLE_EN, body_en=TITLE_EN, body_de=TITLE_DE
    )
    SiteText.objects.filter(key=INTRO_KEY).delete()
    SiteText.objects.filter(key__in=STAFF_HINT_KEYS).update(
        body=STAFF_HINT_EN, body_en=STAFF_HINT_EN, body_de=STAFF_HINT_DE
    )


def noop_reverse(apps, schema_editor):
    """Deliberately a no-op -- see 0019/0023 for the same reasoning: the
    pre-refresh copy isn't recorded anywhere, so a faithful reverse can't
    restore it, and re-seeding the deleted intro row or restoring the old
    English copy unconditionally on reverse risks clobbering later edits.
    """


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0024_portal_nav_users_text"),
    ]

    operations = [migrations.RunPython(refresh_portal_text, noop_reverse)]
