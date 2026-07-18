# Document Portal — configuration & deployment

The document portal is a Django app (`portal`) mounted at `/portal/`. It lets the
OBC team upload and manage per-Provider documents, and lets Provider Members
access their own archive, with email notifications and digests.

This file documents the **settings the portal needs**. They live in the
environment-specific Django settings file, which is **git-ignored** (it holds
secrets), so they are **not** version-controlled and must be added by hand to the
production settings at deploy time.

## Where the settings live

- The active settings module is `src/intrepid/settings.py`, which is a **symlink**
  to the environment file — `dev_settings.py` locally; on the server it is
  symlinked to `prod_settings.py` by
  `infrastructure/ansible/virtualenv/symlink_settings.yml`.
- `dev_settings.py`, `settings.py` and `prod_settings.py` are all listed in
  `.gitignore`, so changes to them are **not** committed.
- **At deploy time you must add the two blocks below to `prod_settings.py` on the
  server**, or the portal will not load and the notification cron job will error.

## 1. Register the app

Add `"portal"` to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    ...,
    "portal",
]
```

## 2. Notification timing constants

The portal needs the `datetime` import and four `DOC_*` constants:

```python
import datetime

# Document portal
DOC_NOTIFICATION_DELAY = datetime.timedelta(hours=2)
DOC_DIGEST_DAILY_HOUR  = 9   # daily digests are sent at this hour
DOC_DIGEST_WEEKLY_DAY  = 0   # weekday for weekly digests (Python weekday(): 0 = Monday)
DOC_DIGEST_MONTHLY_DAY = 1   # day-of-month for monthly digests
```

| Constant | Default | What it controls |
|---|---|---|
| `DOC_NOTIFICATION_DELAY` | `timedelta(hours=2)` | Grace window before an **immediate** notification email is allowed to fire. This lets OBC delete and re-upload a mistakenly-uploaded document within the window without any email going out. |
| `DOC_DIGEST_DAILY_HOUR` | `9` | Hour of day (project timezone, 24-hour clock) at which **daily** digest emails are sent. |
| `DOC_DIGEST_WEEKLY_DAY` | `0` (Monday) | Day of the week for **weekly** digests, using Python's `date.weekday()` (0 = Monday … 6 = Sunday). |
| `DOC_DIGEST_MONTHLY_DAY` | `1` | Day of the month on which **monthly** digests are sent. |

All four are read by `src/portal/notifications.py` when computing when each queued
notification becomes due. They are also present in `dev_settings.py` for local
development.

## 3. Other deploy steps (for completeness)

These steps **are** version-controlled (migrations and the cron installer travel
with the code) — listed here so a deploy is complete:

- **Run migrations:** `uv run ./manage.py migrate`. This creates the portal tables
  and seeds the two starter document types, the `OBC Team` / `Provider Members`
  groups, the four email templates, and the portal's translatable UI strings
  (`cms.SiteText`). The `mail` migrations also add the translation columns to
  `EmailTemplate` (`subject_en/de`, `body_en/de`) and copy each existing
  template's `subject`/`body` into its English columns, so every existing send
  path keeps rendering after the upgrade — no manual step is required. OBC staff
  can then edit and translate the four portal notification emails from
  **Portal → Email copy** (`/portal/obc/email-templates/`).
- **Install the cron job** that drains the notification queue every 15 minutes:
  `uv run ./manage.py install_cron` (adds the `send_document_notifications` job).
- **(Optional) populate translations:** `uv run ./manage.py update_translation_fields`,
  then translate the seeded `SiteText` / `DocumentType` strings into German from
  the usual translation tooling.

## URL note

The portal lives at `/portal/`. The older configuration dashboard was moved from
`/dashboard/` to `/staff/` and is reachable only by typing that URL directly; the
top-right "Dashboard" link in the site navigation now points at the portal.

See `docs/2026-04-document-portal-plan.md` for the full design and implementation
plan.
