# Document Management Portal — Implementation Plan

## Context

OBC's client (Open Book Collective) needs a per-Provider document management portal so that the OBC team can upload Provider-related documents (primarily remittance advice and contracts) and Provider Members can access their own archive. Today there are ~22 Supporter Programmes and ~100 supporting institutions; both are expected to grow. There is no document-distribution mechanism currently — remittance PDFs sit in OBC-side folders organised by month.

In codebase terms, "Provider" maps to the existing `initiatives.Initiative` model (`src/initiatives/models.py:41`). Initiatives already have an `Initiative.users` M2M to Django's `User`, so user→Provider scoping has a foundation. The codebase already uses `fluid_permissions` for granular per-view access, `mail.EmailTemplate` for templated email, native cron via `install/management/commands/install_cron.py` for scheduled jobs, and `modeltranslation` for i18n. The plan reuses each of these.

The end state:
- New `documents` Django app exposing a portal at `/documents/` for both audiences (one UI, permission-gated visibility).
- Per-document-type, per-user fluid permissions for OBC team granularity.
- Provider Members are scoped to their own Initiative(s) by `Initiative.users`.
- Manual single + multi + bulk-folder upload (with `<short_code>/YYYY-MM/*.pdf` ZIP convention auto-mapping to Initiative + reporting month).
- Provider notifications: immediate (delayed 2h), daily digest, weekly digest, monthly digest — implemented via a DB queue drained by a 15-minute cron job. If a document is deleted, its notifications should be, also.
- Provider self-service contact management with an OBC change-notification email + persistent audit log.
- An invitation flow that reuses the existing `Contact.access_code` UUID pattern to onboard Provider Members.

The dashboard tidy-up mentioned in the spec is intentionally deferred to a follow-up issue, since which admin models OBC vs Provider users actually need is best inventoried after the portal is in use. Further, it will quicker and cleaner to build this as a new dashboard, completely separate to the main admin system, which is complex to accommodate the design spec.

No GitHub issues exist yet; commits will not carry a footer reference until one is created.

---

## 1. New `documents` Django app

Create `src/documents/` with the standard layout used by `access`, `vocab`, `mail`:

```
src/documents/
    __init__.py
    apps.py
    admin.py
    forms.py
    models.py
    translation.py
    urls.py
    views.py
    notifications.py      # queue/digest helpers
    permissions.py        # per-area decorators / helpers
    migrations/
    management/commands/
        send_document_notifications.py      # the notification handler
        bulk_import.py                      # ZIP + folder-tree parser
    tests.py
```

Add `"documents"` to `INSTALLED_APPS` in `src/intrepid/settings.py:34-72` and register `path("documents/", include("documents.urls"))` in `src/intrepid/urls.py:10`.

---

## 2. Data model

All file uploads use the existing `upload_storage = FileSystemStorage(location=settings.FILE_ROOT, base_url="/files")` declared in `src/package/models.py:28-30`, so files land outside `MEDIA_ROOT` and require an authenticated view to serve — matching the `MediaFile` precedent (`src/package/models.py:2091`).

### `DocumentType`
Admin-editable type list (translatable via `modeltranslation`, mirroring `vocab/translation.py:6-9`).

| Field | Type | Notes |
|---|---|---|
| `name` | CharField(120, unique) | Translated. e.g. "Remittance advice", "Agreement contract" |
| `slug` | SlugField(unique) | Stable code for permission keys |
| `description` | BleachField(blank) | Translated |
| `requires_reporting_month` | Boolean(default=False) | Gates the reporting-month field on upload |
| `default` | Boolean(default=False) | The type pre-selected on the upload form |
| `ordering` | PositiveSmallIntegerField | Display order |

`Meta.ordering = ("ordering", "name")`. A data migration seeds: "Remittance advice" (`requires_reporting_month=True`, `default=True`) and "Agreement contract" (`requires_reporting_month=False`).

### `Document`
The core uploaded file.

| Field | Type | Notes |
|---|---|---|
| `initiative` | FK → `initiatives.Initiative`, on_delete=CASCADE | The owning Provider |
| `document_type` | FK → `DocumentType`, on_delete=PROTECT |  |
| `file` | FileField(upload_to=`documents_upload_path`, storage=upload_storage) | UUID-renamed under `provider_documents/<initiative_pk>/` |
| `display_name` | CharField(255) | Defaults to original filename minus extension; provider-editable by OBC at upload time |
| `original_filename` | CharField(255) | Captured at save for display alongside `display_name` |
| `reporting_month` | DateField(null=True, blank=True) | Stored as the first day of that month; null when type doesn't require it |
| `uploaded_by` | FK → `User`, on_delete=SET_NULL, null=True | OBC uploader |
| `uploaded_at` | DateTimeField(default=timezone.now) |  |
| `notification_eligible_at` | DateTimeField | Auto-set to `uploaded_at + DOC_NOTIFICATION_DELAY` (settings, default 2h). Used by the cron job to suppress immediate notifications for documents uploaded then deleted by OBC within the grace window |
| `notes` | BleachField(blank, null) | Internal-only OBC notes; never shown to Provider |

`Meta.ordering = ("-uploaded_at",)`.
`__str__` returns `display_name`.
`file_size`, `mime_type` properties use `mimetypes` and `os.path.getsize`, mirroring `MediaFile.mime()` (`src/package/models.py:2116`).

Helper `documents_upload_path(instance, filename)` lives at module top (UUID rename, same idiom as `profile_images_upload_path` at `src/initiatives/models.py:9-22`).

### `DocumentTypePermission`
Bridges `DocumentType` ↔ `auth.Group` for read/write granularity within OBC. Uses `auth.Group` directly — `fluid_permissions` operates on `Group`s already (`src/accounts/utils.py:10-23`), so existing group management UI keeps working.

| Field | Type | Notes |
|---|---|---|
| `document_type` | FK → DocumentType |  |
| `group` | FK → auth.Group |  |
| `can_read` | Boolean(default=True) |  |
| `can_write` | Boolean(default=False) | Includes upload, edit, delete |

`unique_together = ("document_type", "group")`.

### `ProviderContact`
Replaces the spec's "First/Secondary/Tertiary contacts" with a flexible per-Initiative table. The existing `access.Contact` is **kept** (it's used by signup access codes on the customer side), but a new `ProviderContact` represents the editable directory of provider-side staff who manage documents and notifications.

| Field | Type | Notes |
|---|---|---|
| `initiative` | FK → Initiative |  |
| `user` | FK → User, null=True, blank=True | Set once they accept the invite |
| `first_name` | CharField(150) |  |
| `last_name` | CharField(150) |  |
| `job_title` | CharField(255, blank) |  |
| `email` | EmailField |  |
| `position` | PositiveSmallIntegerField | 1=primary, 2=secondary, 3=tertiary, …; soft-warned at 5 in the form |
| `notification_frequency` | CharField, choices=("immediate","daily","weekly","monthly","off") | Default "immediate" |
| `invite_token` | UUIDField(default=uuid4) | Reuses the `Contact.access_code` idiom (`src/access/models.py:32`) |
| `invited_at` | DateTimeField(null) |  |
| `accepted_at` | DateTimeField(null) |  |

`Meta.ordering = ("position", "last_name")`.

### `ContactChangeLog`
Audit log of provider-edited contact details for OBC review.

| Field | Type | Notes |
|---|---|---|
| `provider_contact` | FK → ProviderContact, on_delete=SET_NULL, null=True | Survives contact deletion |
| `initiative` | FK → Initiative | Denormalised for filtering |
| `actor` | FK → User, null=True | Who made the edit |
| `field_changes` | JSONField | `{field: {"from": ..., "to": ...}}` |
| `created_at` | DateTimeField(default=timezone.now) |  |

### `NotificationQueue`
DB-queue drained by cron.

| Field | Type | Notes |
|---|---|---|
| `document` | FK → Document, on_delete=CASCADE |  |
| `recipient` | FK → ProviderContact |  |
| `eligible_at` | DateTimeField | For "immediate" rows = `document.notification_eligible_at`; for digests = next digest send time |
| `frequency` | CharField | Snapshot of recipient's setting at enqueue time (so changing frequency mid-digest doesn't strand rows) |
| `sent_at` | DateTimeField(null) | NULL until processed |
| `cancelled_at` | DateTimeField(null) | Set if the document is deleted before send |

`Meta.indexes = [("eligible_at", "sent_at"), ("document",)]`.

---

## 3. Permissions

Two complementary layers.

**Layer A — per-Provider scoping (Provider Members):** the existing `intrepid.security.user_is_initiative_manager` decorator (`src/intrepid/security.py:8`) already enforces "user must be in `Initiative.users` or be staff". Apply it to every per-initiative view in the new app, identical to how `package.media_views.list_media_files` does (`src/package/media_views.py:10`).

**Layer B — per-document-type, read/write (OBC team):** wrapped by a new `documents.permissions.user_can_for_doc_type(action, doc_type)` helper:

```python
def user_can(user, action: str, doc_type: DocumentType) -> bool:
    if user.is_superuser or user.is_staff_obc(user):
        return True
    qs = DocumentTypePermission.objects.filter(
        document_type=doc_type,
        group__in=user.groups.all(),
    )
    if action == "read":
        return qs.filter(can_read=True).exists()
    return qs.filter(can_write=True).exists()
```

The existing `fluid_permissions.decorators.user_in_authorised_group` (already imported throughout, e.g. `src/accounts/views.py:7`) protects index and management views. A new `@requires_doc_type(action)` decorator wraps detail/edit/delete views and resolves the `DocumentType` from URL kwargs.

The OBC team is a single Django Group (`OBC Team`, seeded by data migration). Provider Members are added to a `Provider Members` group on first login via the invite-acceptance flow. These two groups feed both `fluid_permissions.ViewGroup` and `DocumentTypePermission`.

---

## 4. Views & URL routes

All under `/documents/`, namespace `documents`. URL list (in execution order in `src/documents/urls.py`):

| Path | View | Audience |
|---|---|---|
| `/` | `index` — landing page; redirects to OBC dashboard or Provider list | both |
| `obc/` | `obc_dashboard` | OBC |
| `obc/initiative/<int:initiative_id>/` | `obc_initiative_detail` (list, filter, sort) | OBC |
| `obc/initiative/<int:initiative_id>/upload/` | `obc_upload` (single + multi-file form) | OBC |
| `obc/bulk-import/` | `obc_bulk_import` (ZIP upload + dry-run preview) | OBC |
| `obc/bulk-import/<int:job_id>/commit/` | `obc_bulk_commit` | OBC |
| `obc/document/<int:doc_id>/edit/` | `obc_document_edit` | OBC |
| `obc/document/<int:doc_id>/delete/` | `obc_document_delete` | OBC |
| `provider/` | `provider_initiative_picker` (only if user has multiple Initiatives) | Provider |
| `provider/initiative/<int:initiative_id>/` | `provider_initiative_documents` (filter, sort, search) | Provider |
| `provider/initiative/<int:initiative_id>/contacts/` | `provider_manage_contacts` | Provider |
| `provider/initiative/<int:initiative_id>/notifications/` | `provider_notification_prefs` | Provider |
| `document/<int:doc_id>/download/` | `download_document` (auth-checked stream) | both |
| `documents/bulk-download/` | `bulk_download` (POSTed ID list → streamed ZIP) | both |
| `invite/accept/<uuid:token>/` | `accept_invite` (sets password, links user→Initiative) | invitee |

`obc_initiative_detail` and `provider_initiative_documents` share a common QuerySet builder accepting filters: `document_type`, `reporting_month`, `uploaded_after`, `uploaded_before`, `q` (filename/display_name search). Provider view wraps it with `Document.objects.filter(initiative__in=request.user.Initiatives.all())` to enforce scoping at the QuerySet boundary.

`download_document` re-checks both layers (`user_can(... "read", ...)` for OBC, `Initiative.users` membership for Provider) before streaming via `FileResponse(open(doc.file.path, "rb"))` with `Content-Disposition: attachment` — mirroring `dashboard.views.frozen_document` (`src/dashboard/views.py:141`).

`bulk_download` accepts a list of document IDs, re-checks permission per ID, and streams a ZIP via `zipfile.ZipFile` in append mode over a `StreamingHttpResponse`. Memory bounded; suits archives in the 100s-MB range. Larger jobs would be a follow-up enhancement.

---

## 5. Bulk import pipeline (`documents/bulk_import.py`)

Two-step UX so OBC reviews mappings before files persist.

**Step 1 — upload & dry-run.** OBC uploads a ZIP. Server extracts to a temp directory, walks paths matching `^(?P<short_code>[A-Z0-9]{1,4})/(?P<year>\d{4})-(?P<month>\d{2})/.+\.(pdf|docx?|xlsx?|csv)$` (case-insensitive). For each match:
- Look up `Initiative.objects.get(short_code__iexact=short_code)` (the field already exists at `src/initiatives/models.py:67`).
- Validate `year`/`month` form a real date.
- Default `document_type` = the seeded "Remittance advice" type (`requires_reporting_month=True`).
- Build a `BulkImportRow` (in-memory dataclass; persisted as `BulkImportJob` + `BulkImportRow` rows for resume/preview).

Dry-run renders a table: Filename → Initiative → Reporting month → Document type → Status (OK / unknown short_code / bad date / duplicate). Unrecognised paths are listed under "Skipped — please review".

**Step 2 — commit.** OBC clicks Confirm; the server creates `Document` rows from staged `BulkImportRow`s, copies files into the `documents` storage, and enqueues notifications via the same path as a single upload.

Bulk imports default to `notify=False` for historical backfill (the spec implies historical data was already shared out-of-band). A checkbox lets OBC opt back in if they're importing recent activity.

---

## 6. Forms

| Form | Notes |
|---|---|
| `DocumentUploadForm` | Multi-file via `<input multiple>` and a custom `MultipleFileField` (Django ≥ 5.0 idiom). Fields: `document_type`, `reporting_month` (gated by JS on the type's `requires_reporting_month` flag), per-file `display_name` overrides. ModelForm-flavoured but loops over `request.FILES.getlist("file")` |
| `DocumentEditForm` | Edit `display_name`, `document_type`, `reporting_month`, `notes`. File replacement creates a new Document row (we don't version in this iteration; deletion + re-upload covers correction during the 2h grace window) |
| `BulkImportZipForm` | Single ZIP upload + `notify_on_commit` checkbox |
| `ProviderContactForm` | Per-row inline form. Position auto-numbered. JS warns when adding a 6th contact |
| `NotificationPreferencesForm` | One radio per ProviderContact: immediate / daily / weekly / monthly / off |
| `AcceptInviteForm` | Sets password, optionally edits name/job_title; on save creates `User`, links to `Initiative.users`, marks `ProviderContact.user`/`accepted_at` |

The codebase uses `crispy_forms` (`src/intrepid/settings.py:74`); these forms follow that convention.

---

## 7. Templates

Under `src/templates/documents/`. Reuses the bootstrap4 base in `src/templates/base/` (already loaded site-wide via `intrepid.context_processors`).

```
documents/
    base.html                # extends elements/base.html, adds left-nav for Documents
    obc_dashboard.html       # cards: per-Initiative doc counts, recent uploads
    obc_initiative_detail.html  # filter form + paginated table
    obc_upload.html          # drag-and-drop multi-file
    obc_bulk_import.html     # form upload
    obc_bulk_preview.html    # mapping table + commit button
    obc_document_edit.html
    obc_document_delete.html
    provider_initiative_picker.html
    provider_initiative_documents.html  # filter + table + bulk-download form
    provider_contacts.html
    provider_notification_prefs.html
    accept_invite.html
    emails/
        document_notification_immediate.html
        document_notification_digest.html
        contact_change_notification.html
        provider_invite.html
```

Email templates are primarily driven through `mail.EmailTemplate` rows (admin-editable subjects/bodies, per existing pattern at `src/mail/models.py:35`). The HTML files above are loaded as the *initial* `body` content during a data migration that creates the `EmailTemplate` rows by `name` slug; runtime renders use `EmailTemplate.send(to, context)` (`src/mail/models.py:159`).

---

## 8. Notification system

### Trigger points

- **On `Document` save (`post_save`):** if `created and not _bulk_import_silent`, enqueue one `NotificationQueue` row per `ProviderContact` of `document.initiative` whose `notification_frequency` is not `off`. `eligible_at` is computed per-frequency:
    - `immediate` → `document.notification_eligible_at` (uploaded_at + 2h grace)
    - `daily` → next 09:00 in the project timezone
    - `weekly` → next Monday 09:00
    - `monthly` → 1st of next month, 09:00

- **On `Document` delete:** mark all unsent rows for that document `cancelled_at = now()`. Honours the spec's grace-window intent: if OBC deletes a misuploaded file before its `eligible_at`, no email goes out.

### Cron drain

New management command: `src/documents/management/commands/send_document_notifications.py`.

Logic per run:
1. Select `NotificationQueue` rows where `sent_at IS NULL AND cancelled_at IS NULL AND eligible_at ≤ now()`.
2. Group by `(recipient, frequency, eligible_at_bucket)` so digest recipients receive one email summarising N documents instead of N emails. Bucket key = `(recipient_id, frequency, date_floor(eligible_at, frequency))`.
3. For each group, render via `EmailTemplate.send(to=recipient.email, context={...})`. Immediate uses the `document_notification_immediate` template; digests use `document_notification_digest` with a `documents` list in the context.
4. Mark all queue rows in the group `sent_at = now()`.
5. Atomic per-group transaction so a render failure doesn't half-mark the bucket.

Add the job to the existing cron installer at `src/install/management/commands/install_cron.py:48-55`:

```python
{
    "name": "{}_intrepid_send_document_notifications".format(cwd),
    "minutes": 15,           # every 15 min
    "task": "send_document_notifications",
},
```

The current installer's job dict shape supports `time` for `minute.every(...)` (`install_cron.py:70-73`); a small extension reads `minutes` and dispatches to `cron_job.minute.every(minutes)` to make the intent explicit.

### Settings

In `src/intrepid/settings.py`:
```python
DOC_NOTIFICATION_DELAY = datetime.timedelta(hours=2)
DOC_DIGEST_DAILY_HOUR  = 9
DOC_DIGEST_WEEKLY_DAY  = 0  # Monday
DOC_DIGEST_MONTHLY_DAY = 1
```

---

## 9. Provider contact change notifications

`ProviderContact.save()` overridden to diff against `__class__.objects.get(pk=self.pk)` for existing rows. When tracked fields (`first_name`, `last_name`, `job_title`, `email`, `notification_frequency`) change:
1. Persist a `ContactChangeLog` row.
2. Send `EmailTemplate.objects.get(name="contact_change_notification").send(to=settings.FROM_EMAIL, context={...})`. (`FROM_EMAIL` is set at `src/intrepid/settings.py:228-235`.)

The change log is exposed at `/documents/obc/contact-changes/` (filterable by Initiative) and via `admin.py`.

---

## 10. Invitation flow

OBC creates a `ProviderContact` row (no `user` yet, `invite_token` auto-generated). A "Send invite" action emails the contact a link `/documents/invite/accept/<uuid:token>/`.

`accept_invite` view:
1. Looks up `ProviderContact` by token; 404 on miss; gone-message if `accepted_at` already set.
2. If the email already matches an existing `User`, presents a "log in to accept" path; otherwise shows `AcceptInviteForm`.
3. On accept: creates the `User`, adds them to `Initiative.users`, adds them to the `Provider Members` Group, fills `ProviderContact.user` + `accepted_at`, and logs them in.
4. Redirects to `/documents/provider/initiative/<id>/`.

---

## 11. Translation

`src/documents/translation.py` registers translatable fields, mirroring `src/vocab/translation.py`:

```python
@register(DocumentType)
class DocumentTypeTranslation(TranslationOptions):
    fields = ("name", "description")
```

`Document.display_name` is **not** translated (it's user-supplied per upload). Email template rows in `mail.EmailTemplate` are not translated by modeltranslation today; following spec scope, they remain English-only and a follow-up issue can address per-language email bodies.

---

## 12. Django Admin System

Minimal — the portal is the primary UI, not the Django Admin. `src/documents/admin.py` registers:

- `DocumentTypeAdmin` (list_display: name, slug, requires_reporting_month, default, ordering)
- `DocumentAdmin` (raw_id_fields: initiative, document_type, uploaded_by; list_filter: document_type, initiative; search_fields: display_name, original_filename)
- `ProviderContactAdmin` (list_display: name, email, initiative, position, notification_frequency, accepted_at; list_filter: initiative, notification_frequency)
- `ContactChangeLogAdmin` (read-only)
- `DocumentTypePermissionAdmin`
- `NotificationQueueAdmin` (read-only debugging aid; list_filter: frequency, sent_at)

Follows the registration idiom at `src/initiatives/admin.py:24-29`.

---

## 13. Tests (red/green TDD)

Write failing tests first against stubs, then implement until green. Each module under test gets a `NotImplementedError`-raising stub before its real body exists.

`src/documents/tests.py` — Django `TestCase` subclasses, no live network/email (`mail.EmailTemplate._send_email` is mocked via `unittest.mock.patch` so we test return values, not call counts). Coverage:

**Models**
- `Document.notification_eligible_at` is set to `uploaded_at + DOC_NOTIFICATION_DELAY`.
- `documents_upload_path()` produces a UUID-renamed path under `provider_documents/<initiative_pk>/`.
- `DocumentType.requires_reporting_month=True` causes `Document.clean()` to require `reporting_month`.
- `ProviderContact.save()` emits a `ContactChangeLog` row when tracked fields change, and not when untracked fields change.

**Permissions**
- `user_can(superuser, "write", any_type)` is True.
- A user in a Group with `DocumentTypePermission(can_write=False, can_read=True)` returns True for read, False for write.
- Provider user not in `Initiative.users` gets 403 from `provider_initiative_documents`.
- `download_document` returns 403 when user lacks both Layer A and Layer B access.

**Bulk import**
- `parse_zip(<sample.zip>)` with valid `<short_code>/YYYY-MM/file.pdf` yields the expected `(initiative, reporting_month, type)` tuples.
- Unknown short_code → row marked `skipped`.
- Bad date → row marked `error`.
- Commit creates the right number of `Document` rows and queues no notifications when `notify_on_commit=False`.

**Notifications**
- Enqueueing on `post_save` produces one `NotificationQueue` row per active `ProviderContact`.
- Deleting a `Document` cancels its unsent queue rows.
- The `send_document_notifications` command, run with `eligible_at` in the past, marks rows `sent_at`.
- Digest grouping: 3 documents → 1 digest email (asserted via the mocked `EmailTemplate.send` return).
- A digest contact gets one email; an immediate contact gets per-doc emails.

**Invitation**
- Accepting an invite creates the User, links to Initiative.users, sets `accepted_at`.
- Re-accepting the same token shows a "already accepted" page rather than re-using.

Tests follow standard practice: testing behaviour, not implementation. They mock `EmailTemplate._send_email` and assert on returned/persisted state, not call counts.

Important note: tests around exact wording (email subject text, button labels) are **written then deleted** as a discipline aid — they shouldn't constrain copy edits.

---

## 14. Migrations & data seeding

A single initial migration (`0001_initial.py`) creates all six models. A second data migration (`0002_seed.py`) populates:
- Two `DocumentType` rows ("Remittance advice", "Agreement contract").
- The `OBC Team` and `Provider Members` `auth.Group` rows (idempotent `get_or_create`).
- `EmailTemplate` rows by name slug (`document_notification_immediate`, `document_notification_digest`, `contact_change_notification`, `provider_invite`) using the HTML files in `templates/documents/emails/` as the initial `body`.
- `fluid_permissions.ViewGroup` rows for the new view names so the existing permission UI at `/accounts/manage_fluid_permissions/` (`src/accounts/views.py:179`) immediately surfaces the new views.

---

## 15. Critical files — to be created or modified

**Created**
- `src/documents/__init__.py`, `apps.py`, `models.py`, `admin.py`, `forms.py`, `views.py`, `urls.py`, `translation.py`, `bulk_import.py`, `notifications.py`, `permissions.py`, `tests.py`
- `src/documents/management/__init__.py`, `management/commands/__init__.py`, `management/commands/send_document_notifications.py`
- `src/documents/migrations/0001_initial.py`, `0002_seed.py`
- `src/templates/documents/*` (per §7)

**Modified**
- `src/intrepid/settings.py` — add `documents` to `INSTALLED_APPS` (line 34-72); add `DOC_NOTIFICATION_DELAY`, `DOC_DIGEST_*` constants
- `src/intrepid/urls.py` — add `path("documents/", include("documents.urls"))` (line 10)
- `src/install/management/commands/install_cron.py` — add the `send_document_notifications` job (line 48-55) and extend the dispatcher to read `minutes` (line 70-73)

---

## 16. Verification

End-to-end checks before declaring done:

1. **Migrations apply cleanly:** `uv run ./manage.py makemigrations documents && uv run ./manage.py migrate`. Re-run on a copy of `obc_db.sqlite3` to confirm no clashes with existing data.
2. **Tests pass:** `uv run ./manage.py test documents` — all green.
3. **Translations:** `uv run ./manage.py update_translation_fields` (modeltranslation pattern used for `BandingVocab` recently — see commit `b9a48e0`) followed by `uv run ./manage.py makemessages -l de && compilemessages`.
4. **Cron install:** `uv run ./manage.py install_cron --action test` shows the new job alongside `sync_thoth`.
5. **Browser walkthrough** (Django dev server on `https://localhost`, self-signed cert):
   - Sign in as superuser → upload a single PDF for an Initiative → confirm it appears in the OBC list.
   - Upload a multi-file batch → confirm all rows created.
   - ZIP a fixture matching `<short_code>/YYYY-MM/*.pdf` for two Initiatives → bulk-import dry-run preview shows correct mapping → commit → both `Document` rows appear.
   - Create a `ProviderContact`, send invite, accept the invite as a fresh user, log in, view the documents list scoped to that Initiative, change frequency to "daily", edit name → confirm OBC inbox receives `contact_change_notification`.
   - Manually `update NotificationQueue set eligible_at = '2020-01-01'` then run `uv run ./manage.py send_document_notifications` → confirm rows marked sent and (mock) email rendered.
   - Bulk-download three documents from the provider view → confirm streamed ZIP contains the three files at their `original_filename`.
6. **Permission probes:** log in as a non-staff user with no Initiative membership → verify 403 on every `/documents/obc/*` and on `/documents/provider/initiative/<other>/`.
7. **Lint/format:** `uv run ruff check src/documents` and any pre-commit hooks defined for the repo. Fix and re-stage before committing.

---

## 17. Out of scope (deferred)

- Document versioning / replacement history (one-version, deletion-and-replace covers the 2h grace use case).
- Email-link pickup of very large bulk-download archives.
- Translated email bodies (English only in v1).
- A REST API surface for the portal — the existing `api/` app is unaffected.
