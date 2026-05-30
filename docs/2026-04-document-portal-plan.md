# Document Management Portal — Implementation Plan

## Context

OBC's client (Open Book Collective) needs a per-Provider document management portal so that the OBC team can upload Provider-related documents (primarily remittance advice and contracts) and Provider Members can access their own archive. Today there are ~22 Supporter Programmes and ~100 supporting institutions; both are expected to grow. There is no document-distribution mechanism currently — remittance PDFs sit in OBC-side folders organised by month.

In codebase terms, "Provider" maps to the existing `initiatives.Initiative` model (`src/initiatives/models.py:41`). Initiatives already have an `Initiative.users` M2M to Django's `User`, so user→Provider scoping has a foundation. The codebase already uses `fluid_permissions` for granular per-view access, `mail.EmailTemplate` for templated email, native cron via `install/management/commands/install_cron.py` for scheduled jobs, and `modeltranslation` for i18n. The plan reuses each of these.

The end state:
- New `portal` Django app exposing a portal at `/portal/` for both audiences (one UI, permission-gated visibility).
- Per-document-type, per-user fluid permissions for OBC team granularity.
- Provider Members are scoped to their own Initiative(s) by `Initiative.users`.
- Manual single + multi + bulk-folder upload (with `<short_code>/YYYY-MM/*.pdf` ZIP convention auto-mapping to Initiative + reporting month).
- Provider notifications: immediate (delayed 2h), daily digest, weekly digest, monthly digest — implemented via a DB queue drained by a 15-minute cron job. If a document is deleted, its notifications should be, also.
- Provider self-service contact management with an OBC change-notification email + persistent audit log.
- An invitation flow that reuses the existing `Contact.access_code` UUID pattern to onboard Provider Members.
- A small tidy of the site's top-level navigation: the existing (redundant-to-most-users) top-right **"Dashboard"** link is re-pointed at the new portal, the old configuration dashboard is moved from `/dashboard/` to `/staff/`, and that older area is left reachable only by typing its URL directly. This is the lightest-touch way to give OBC and Providers a single obvious entry point without disturbing the existing dashboard's internals.

The dashboard tidy-up mentioned in the spec is intentionally deferred to a follow-up issue, since which admin models OBC vs Provider users actually need is best inventoried after the portal is in use. Further, it will be quicker and cleaner to build this as a new dashboard, completely separate to the main admin system, which is complex to accommodate the design spec.

**Engineering note on framework version.** The OBC site runs **Django 3.2** (not Django 5.x). Two consequences are reflected throughout this plan: (a) multi-file upload uses the Django 3.2 idiom — a `ClearableFileInput(attrs={"multiple": True})` widget plus iteration over `request.FILES.getlist(...)` — rather than the Django ≥ 5.0 `MultipleFileField`; and (b) `JSONField` and other model features used below are all available in 3.2.

No GitHub issues exist yet; commits will not carry a footer reference until one is created.

---

## Client clarifications incorporated

During review the client raised five questions. The answers are folded into the relevant sections below; they are summarised here so the decision trail is in one place.

1. **Can the redundant top-right "Dashboard" link become the login/entry point for the new backend, and does OBC still need a separate way into the old areas?** Yes. We re-point that link at the new portal (`/portal/`). We move the *old* configuration dashboard from `/dashboard/` to `/staff/` and stop linking to it from the navigation, so it remains fully functional but is only reached by visiting `/staff/` directly. OBC keeps full access to both; everyday users see one clean entry point. (See §1 and §15.)
2. **How precise must the bulk-upload ZIP naming be — the four-letter code only, or the whole filename?** Only the *folder structure* must match; the filenames inside can be anything. The parser regex is `^<short_code>/YYYY-MM/.+\.(pdf|docx?|xlsx?|csv)$` (case-insensitive), so `PUNC/2024-03/whatever-the-original-name-was.pdf` works. The `short_code` folder must match an existing `Initiative.short_code` (looked up case-insensitively; 1–4 alphanumeric characters) and the month folder must be a real `YYYY-MM` date. Anything unrecognised appears in the dry-run preview under "Skipped — please review" rather than being silently dropped. (See §5.)
3. **Six document types are listed now — can we add more later?** Yes, fully. `DocumentType` is its own admin-editable model (§2); the data migration only seeds two starter rows ("Remittance advice", "Agreement contract"). OBC can add any number more from the admin, each with its own name, description, `requires_reporting_month` flag, `default` flag and display order. Read/write access to each new type is then assignable per team member via `DocumentTypePermission`. (See §2 and §3.)
4. **What does "up to 5 contacts (soft)" mean?** "Soft" is a friendly warning, not a hard cap. The data model places no limit on `ProviderContact` rows per Initiative; the contact form simply shows a JavaScript warning when a Provider adds a sixth contact, but still saves it. A Provider that genuinely needs 7 or 12 contacts can add them with no engineering change. (See §2 and §6.)
5. **Is the notification frequency per-user, or one global setting per Provider?** Per-user. `notification_frequency` lives on each `ProviderContact` row (§2), and the preferences screen shows one choice (immediate / daily / weekly / monthly / off) per contact (§4, §6). Three people at the same Provider can each pick a different cadence without affecting the others.

---

## Original specification

This is reproduced here verbatim so that every technical decision below can be traced back to a stated need. Each numbered section in this document begins with an **"In plain language"** paragraph that describes which part of this specification it satisfies and how.

> ### GENERAL
> - In general, the backend should be tidied up, especially for Providers. All irrelevant/extraneous information to be hidden, and only information relevant to the modules below to be visible.
>
> ### MODULE 1: Document management portal
>
> **Summary:** Using backend to create an area for Providers to keep track of documents related to their OBC's "Supporter Programmes". At present there are 22 "Supporter Programmes". This number is expected to steadily grow over the months and years. At present we have close to 100 different universities supporting at least 1 Supporter Programme each (and most support more than one).
>
> **Users:** OBC Team (full access) + Provider Members (partial access).
>
> #### Functionality required by OBC team
>
> The OBC team are the primary users. The team should be able to at least read all information in the portal.
>
> 1. **Permissions management:** it should be possible to assign different read/write permissions to different areas of the document management portal, to different members of the team.
> 2. **Document upload & management:** Documents (agreement contracts, remittance advice) to be manually uploaded by the OBC for each Provider.
>
> Relevant information displayed in the portal, with relevant filters available, should include:
> - Type of document (with the possibility to select from a predefined list, e.g., by default 'Remittance advice')
> - Name of document (as per the file name)
> - Date of upload
> - Reporting month [i.e. similar to a bank statement, there are 12 of these, one for each month. This would only apply to Remittance advice documents, so if another document type is selected, then this would be greyed out]
>
> **Note on required functionality:** The system should allow uploading of both individual files and multiple files and/or folders.
>
> **Request/advice appreciated:** we currently have previous Remittance advice stored in folders, by month. If we tag these files appropriately (suggestions welcome), is there a way to bulk upload these, so they are assigned to the correct provider, and the correct reporting month?
>
> #### Functionality required by Provider Members
>
> Provider Members are our Publisher and Service Providers — i.e. these are the ones offering Supporter Programmes to subscribe to, which we promote/sell on their behalf. They will be using the portal to access their archive of OBC documents and to edit relevant content on the OBC site. Each user should only be able to see documents, and only be able to manage content, relevant to their own Provider.
>
> - We should be able to invite Provider Members to set up an account or potentially multiple accounts relating to the same Provider.
>     - The details below should be associated with their account. Note: These details should be possible to change by the Provider user. However, we should receive a notification if these details are changed.
>         - First, Secondary, Tertiary, contact details (name, surname, job title, email address): one or more contacts will be assigned to each supporting institution [up to .. 5 contacts?]
>         - For each:
>             - First name
>             - Surname
>             - Provider(s) (see above)
>             - Job title(s)
>             - Email address
> - When logging in, Providers can access documents for their own initiative, via the Document Management Area.
> - **AREA 1: OBC Document Management Area.** These are documents created by the OBC and our accounts team. We expect these to be predominately statements of account and payment remittance information.
>     - **Functionality required by OBC**
>         - These documents should be uploaded manually by the OBC.
>         - It should be possible to upload documents individually or in bulk related to a particular provider.
>     - **Functionality required by Providers**
>         - Providers should be able to access and interact with these documents.
>         - Documents to be filterable by the above categories.
>         - Providers receive an email notification when a new document is uploaded.
>             - Ideally: Providers should be able to choose how often to receive notifications — either immediately or as a digest (e.g. daily, weekly, monthly).
>             - Ideally: Those that choose 'immediate' receive these notifications no earlier than 2 hours after documents are uploaded. This is to enable OBC to potentially delete and replace a document uploaded in error, without a notification being sent.
>         - Providers should be allowed to download documents either individually or in bulk.

---

## Coverage map: specification → plan

A quick reference so a non-technical reader can verify, at a glance, that every line of the spec is covered by a corresponding part of this plan.

| Specification line | Where it is implemented                                                                                                                                                                                                                                                                                |
|---|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Tidy-up of the existing backend / hide irrelevant info for Providers | This dashboard will be an entirely new section that is clean and minimal; it will do what is needed and keep the complexity of the previous dashboard confined to admins. See §17. We build a **separate, purpose-built dashboard** at `/portal/`, sidestepping the existing admin clutter entirely |
| OBC team has full access; Provider Members have partial access | §3 Permissions (two-layer model: per-Provider scope + per-document-type read/write)                                                                                                                                                                                                                    |
| Read/write permissions assignable to different OBC team members per area | §3 Permissions, `DocumentTypePermission`                                                                                                                                                                                                                                                               |
| OBC manually uploads documents per Provider | §4 Views (`obc_upload`) and §6 Forms (`DocumentUploadForm`)                                                                                                                                                                                                                                            |
| Predefined list of document types (default: Remittance advice) | §2 `DocumentType` model + §14 seed data                                                                                                                                                                                                                                                                |
| Filters: type, name, date of upload, reporting month | §4 (shared QuerySet builder); §6 forms                                                                                                                                                                                                                                                                 |
| Reporting month greyed out unless type requires it | §2 `DocumentType.requires_reporting_month`; §6 form (JS-gated)                                                                                                                                                                                                                                         |
| Upload individual files OR multiple files/folders | §4 (`obc_upload` multi-file) and §5 (bulk import)                                                                                                                                                                                                                                                      |
| Bulk upload of historic remittance advice from month-folder structure | §5 Bulk import pipeline (`<short_code>/YYYY-MM/*.pdf` ZIP)                                                                                                                                                                                                                                             |
| Invite Provider Members to set up accounts | §10 Invitation flow                                                                                                                                                                                                                                                                                    |
| Multiple accounts per Provider | §2 `ProviderContact` (many-per-Initiative)                                                                                                                                                                                                                                                             |
| Per-contact details: first name, surname, job title, email, provider(s) | §2 `ProviderContact`                                                                                                                                                                                                                                                                                   |
| Up to 5 contacts (soft) | §6 `ProviderContactForm` (soft warning above 5; no hard cap)                                                                                                                                                                                                                                           |
| Provider can edit their own contact details | §4 (`provider_manage_contacts`) and §6 forms                                                                                                                                                                                                                                                           |
| OBC notified of contact-detail changes | §9 Provider contact change notifications                                                                                                                                                                                                                                                               |
| Provider sees documents for **their own** initiative only | §3 Layer A scoping via `Initiative.users`                                                                                                                                                                                                                                                              |
| Filter documents by the above categories (Provider side) | §4 (shared QuerySet builder, used by both audiences)                                                                                                                                                                                                                                                   |
| Email notification on new document | §8 Notification system                                                                                                                                                                                                                                                                                 |
| Choose immediate / daily / weekly / monthly digest | §2 `ProviderContact.notification_frequency` and §8 cron drain                                                                                                                                                                                                                                          |
| Immediate delayed by 2 hours so OBC can correct mis-uploads | §2 `Document.notification_eligible_at` and §8 trigger logic                                                                                                                                                                                                                                            |
| Individual + bulk download | §4 (`download_document`, `bulk_download` streamed ZIP)                                                                                                                                                                                                                                                 |
| Single, obvious entry point; redundant "Dashboard" link repurposed (client clarification 1) | §1 URL restructure: portal at `/portal/`, old dashboard moved to `/staff/`, nav link re-pointed                                                                                                                                                                       |

---

## 1. New `portal` Django app

**In plain language.** A "Django app" is the engineering name for a self-contained area of the website. We are creating a brand-new one called *portal* that lives entirely on its own, side-by-side with the existing parts of the OBC site. This is what makes the spec's "tidy-up" feasible without weeks of unpicking the current backend: by working in a fresh space, we get to design every screen for OBC team and Provider Members from scratch, and they will only ever see information relevant to documents — nothing else from the wider OBC system bleeds in. Once finished it will be reachable at the URL `/portal/` on the OBC site.

Create `src/portal/` with the standard layout used by `access`, `vocab`, `mail`:

```
src/portal/
    __init__.py
    apps.py
    admin.py
    bulk_import.py         # ZIP + folder-tree parser
    forms.py
    models.py
    translation.py
    urls.py
    views.py
    notifications.py      # queue/digest helpers
    permissions.py        # per-area decorators / helpers
    migrations/
    management/
        commands/
            send_document_notifications.py  # the notification handler
    tests/                  # a test package (one module per area) rather than a single tests.py,
        __init__.py         #   so the modules can be developed independently
        test_models.py
        test_permissions.py
        test_bulk_import.py
        test_notifications.py
        test_forms.py
        test_views.py
        test_invitation.py
```

Add `"portal"` to `INSTALLED_APPS` in `src/intrepid/settings.py` and register `path("portal/", include("portal.urls"))` in `src/intrepid/urls.py`.

**URL restructure (client clarification 1).** In the same `src/intrepid/urls.py`, the existing line `path("dashboard/", include("dashboard.urls"))` becomes `path("staff/", include("dashboard.urls"))`. This is safe because every old-dashboard URL is referenced by *name* (`dashboard_index`, `dashboard_setup`, …) and resolved with `{% url %}`/`reverse()`, not by hard-coded path — so the mount point can move without breaking internal links. The redundant top-right **"Dashboard"** link (`src/templates/base/frontend/nav.html`, and the equivalent in `src/templates/base/admin_nav.html`) is re-pointed from `{% url 'dashboard_index' %}` to the new portal index. The old dashboard at `/staff/` is intentionally left unlinked — OBC reaches it by typing the URL.

---

## 2. Data model

**In plain language.** Before we can build any screen, we have to decide what the system *remembers*. There are six concepts:
1. **Document type** — the predefined list the spec asks for (Remittance advice, Agreement contract, and any future types OBC adds). Each type can flag whether it needs a reporting month, which is what makes the "grey out reporting month for non-remittance documents" rule work.
2. **Document** — a single uploaded file, attached to one Provider, with all the columns the spec calls out (type, name, date of upload, reporting month).
3. **DocumentTypePermission** — the bridge that lets OBC say "Alice can read remittance advice but only Bob can upload contracts". This is the engine behind the spec's "different read/write permissions to different areas, to different members of the team".
4. **ProviderContact** — the per-Provider directory of people: their first name, surname, job title, email, and how often they'd like to be notified. Replaces the spec's First/Secondary/Tertiary slots with a flexible list.
5. **ContactChangeLog** — a permanent history of any edits a Provider Member makes to their contact details. Backs the spec's "we should receive a notification if these details are changed", letting OBC inspect what actually changed.
6. **NotificationQueue** — a behind-the-scenes waiting list of pending email alerts. Each entry knows when it's *due* to be sent. This is how we honour the spec's two-hour grace window and the daily/weekly/monthly digest options without sending anything prematurely.

Where files are physically stored: we reuse the OBC site's existing private-file storage area (separate from publicly-served images), so a document is never accessible by anyone who hasn't been authenticated and authorised.

All file uploads use the existing `upload_storage = FileSystemStorage(location=settings.FILE_ROOT, base_url="/files")` declared in `src/package/models.py:28-30`, so files land outside `MEDIA_ROOT` and require an authenticated view to serve — matching the `MediaFile` precedent (`src/package/models.py:2091`).

### `DocumentType`
Admin-editable type list (translatable via `modeltranslation`, mirroring `vocab/translation.py`). **Fully extensible (client clarification 3):** the six types referenced in discussion are not hard-coded — `DocumentType` is its own model, the migration seeds only two starter rows, and OBC can add any number more from the admin, each with its own `name`, `description`, `requires_reporting_month`, `default` and `ordering`. Adding a type immediately makes it assignable per team member through `DocumentTypePermission`.

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
| `file` | FileField(upload_to=`portal_documents_upload_path`, storage=upload_storage) | UUID-renamed under `provider_documents/<initiative_pk>/` |
| `display_name` | CharField(255) | Defaults to original filename minus extension; provider-editable by OBC at upload time |
| `original_filename` | CharField(255) | Captured at save for display alongside `display_name` |
| `reporting_month` | DateField(null=True, blank=True) | Stored as the first day of that month; null when type doesn't require it |
| `uploaded_by` | FK → `User`, on_delete=SET_NULL, null=True | OBC uploader |
| `uploaded_at` | DateTimeField(default=timezone.now) |  |
| `notification_eligible_at` | DateTimeField | Auto-set to `uploaded_at + DOC_NOTIFICATION_DELAY` (settings, default 2h). Used by the cron job to suppress immediate notifications for documents uploaded then deleted by OBC within the grace window |
| `notes` | BleachField(blank, null) | Internal-only OBC notes; never shown to Provider |

`Meta.ordering = ("-uploaded_at",)`.
`__str__` returns `display_name`.
`file_size` returns `self.file.size` and `mime_type` mirrors `MediaFile.mime()` (`src/package/models.py:2116`), which uses `magic.from_file(self.file.path, mime=True)` — matching house style rather than the stdlib `mimetypes`.

Helper `portal_documents_upload_path(instance, filename)` lives at module top (UUID rename, same idiom as `profile_images_upload_path` at `src/initiatives/models.py:9-22`).

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
Replaces the spec's "First/Secondary/Tertiary contacts" with a flexible per-Initiative table. The existing `access.Contact` is **kept** (it's used by signup access codes on the customer side), but a new `ProviderContact` represents the editable directory of provider-side staff who manage documents and notifications. There is deliberately **no database limit** on the number of `ProviderContact` rows per Initiative — the "up to 5" is a soft, form-level warning only (client clarification 4), and `notification_frequency` is stored **per contact**, so contacts at the same Provider notify independently (client clarification 5).

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

**In plain language.** "Who is allowed to see what?" is enforced by two checks that must *both* pass.

- **Check one — which Provider's documents am I looking at?** A logged-in Provider Member only ever sees the Provider(s) they've been linked to. They can never type a different Provider's URL into the address bar to peek at other documents. OBC team members and superusers bypass this check (because they're allowed everywhere).
- **Check two — am I allowed to do *this action* on *this document type*?** OBC can decide, per team member, things like "Alice can read remittance advice", "Bob can upload contracts", "Carol can do everything". This is the granularity the spec asked for in its first OBC requirement.

Because both checks must pass, a Provider Member can never accidentally end up able to upload contracts; an OBC reader can never accidentally end up able to delete documents; and a malicious URL guess goes nowhere.

Two complementary layers.

**Layer A — per-Provider scoping (Provider Members):** the existing `intrepid.security.user_is_initiative_manager` decorator (`src/intrepid/security.py:8`) already enforces "user must be in `Initiative.users` or be staff". Apply it to every per-initiative view in the new app, identical to how `package.media_views.list_media_files` does (`src/package/media_views.py:10`).

**Layer B — per-document-type, read/write (OBC team):** wrapped by a new `portal.permissions.user_can(user, action, doc_type)` helper. (Note: the codebase has **no** existing `is_staff_obc` method — that was a placeholder in an earlier draft. We add a small `is_obc_staff(user)` helper in `portal/permissions.py` that treats Django superusers, `is_staff` users, and members of the seeded **"OBC Team"** group as full-access OBC staff. This mirrors the existing `_is_initiative_manager` convention at `src/intrepid/security.py:60`, which already grants `is_staff`/`is_superuser` blanket access, while additionally honouring the dedicated OBC group.)

```python
def is_obc_staff(user) -> bool:
    return (
        user.is_superuser
        or user.is_staff
        or user.groups.filter(name="OBC Team").exists()
    )


def user_can(user, action: str, doc_type: DocumentType) -> bool:
    if is_obc_staff(user):
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

**In plain language.** This is the list of every page and action that exists in the new portal — what a non-engineer would call the "screens". The same screens are used by both audiences; what differs is *what data shows up* on them, governed by the permission checks in §3.

For OBC team:
- A dashboard showing all Providers and recent uploads at a glance.
- A per-Provider view: the filterable, sortable list the spec describes (filter by type, name, upload date, reporting month).
- An upload screen accepting either one file or many, with the "reporting month" field automatically greyed out when the type doesn't need it.
- A bulk-import screen accepting a single ZIP and showing OBC a preview before anything is committed.
- Edit and delete screens for individual documents (delete inside the 2-hour grace window means no notification will ever go out).

For Provider Members:
- A picker (only shown if they belong to more than one Provider).
- A per-Provider documents list with the same filters as OBC's view, but scoped to *their* Provider.
- A "manage my contacts" screen (any change here triggers the §9 alert to OBC).
- A "notification preferences" screen where each contact picks immediate / daily / weekly / monthly / off.

Shared: a download button on each row, plus a "select multiple → download ZIP" action that satisfies the spec's bulk-download requirement. Behind the scenes, every download re-checks both permission layers before serving a single byte.

All under `/portal/`, namespace `portal`. URL list (in execution order in `src/portal/urls.py`):

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
| `bulk-download/` | `bulk_download` (POSTed ID list → streamed ZIP) | both |
| `invite/accept/<uuid:token>/` | `accept_invite` (sets password, links user→Initiative) | invitee |

`obc_initiative_detail` and `provider_initiative_documents` share a common QuerySet builder accepting filters: `document_type`, `reporting_month`, `uploaded_after`, `uploaded_before`, `q` (filename/display_name search). Provider view wraps it with `Document.objects.filter(initiative__in=request.user.Initiatives.all())` to enforce scoping at the QuerySet boundary.

`download_document` re-checks both layers (`user_can(... "read", ...)` for OBC, `Initiative.users` membership for Provider) before streaming via `FileResponse(open(doc.file.path, "rb"))` with `Content-Disposition: attachment` — mirroring `dashboard.views.frozen_document` (`src/dashboard/views.py:141`).

`bulk_download` accepts a list of document IDs, re-checks permission per ID, and streams a ZIP via `zipfile.ZipFile` in append mode over a `StreamingHttpResponse`. Memory bounded; suits archives in the 100s-MB range. Larger jobs would be a follow-up enhancement.

---

## 5. Bulk import pipeline (`portal/bulk_import.py`)

**In plain language.** This directly answers the spec's "Request/advice appreciated" question about historical remittance advice already sitting in monthly folders. The proposal is:

1. Each Provider already has a four-letter "short code" in the OBC system (e.g. *PUNC* for Punctum Books). This is something the OBC team already manages.
2. OBC zips up the historical archive so the *folders inside the ZIP* are named like `PUNC/2024-03/` and `OPEN/2024-03/` etc., with the actual PDFs sitting inside those month folders. **Only the folder names matter (client clarification 2)** — the individual filenames inside can be anything at all. `PUNC/2024-03/whatever-the-original-name-was.pdf` is matched purely on its `PUNC` (Provider) and `2024-03` (reporting month) folders; the leaf filename is preserved as-is for display and download.
3. OBC uploads the ZIP through the new "Bulk import" screen. **Nothing is saved yet.** The system shows OBC a preview table — "I found 47 files; here's which Provider and which reporting month I'd assign each one to". OBC can scan it, spot any mistakes (typos in folder names, files in wrong months), and either fix the ZIP and try again, or click Confirm to commit.
4. On Confirm, every file gets stored against the right Provider with the right reporting month — automatically.

Two safety features: (a) any file we don't recognise (wrong folder shape, unknown short code, malformed date) is *listed* but never silently committed — OBC always sees it; (b) historical bulk imports default to *not* sending notifications, since these are old records, not new alerts. OBC can tick a box if they really do want notifications to fire.

Two-step UX so OBC reviews mappings before files persist.

**Step 1 — upload & dry-run.** OBC uploads a ZIP. Server extracts to a temp directory, walks paths matching `^(?P<short_code>[A-Za-z0-9]{1,4})/(?P<year>\d{4})-(?P<month>\d{2})/.+\.(pdf|docx?|xlsx?|csv)$`, compiled case-insensitively (so the short-code folder may be upper- or lower-case and the extension may be `.PDF` or `.pdf`). For each match:
- Look up `Initiative.objects.get(short_code__iexact=short_code)` — case-insensitive, so the field already existing at `src/initiatives/models.py:67` matches regardless of folder casing.
- Validate `year`/`month` form a real calendar date (e.g. `2024-13` is rejected as a bad date).
- Default `document_type` = the seeded "Remittance advice" type (`requires_reporting_month=True`).
- Build a `BulkImportRow` (in-memory dataclass; persisted as `BulkImportJob` + `BulkImportRow` rows for resume/preview).

Dry-run renders a table: Filename → Initiative → Reporting month → Document type → Status (OK / unknown short_code / bad date / duplicate). Unrecognised paths are listed under "Skipped — please review".

**Step 2 — commit.** OBC clicks Confirm; the server creates `Document` rows from staged `BulkImportRow`s, copies files into the portal's private document storage (`upload_storage`), and enqueues notifications via the same path as a single upload.

Bulk imports default to `notify=False` for historical backfill (the spec implies historical data was already shared out-of-band). A checkbox lets OBC opt back in if they're importing recent activity.

---

## 6. Forms

**In plain language.** "Forms" here are the actual fields users fill in on each screen. The list below names every distinct form in the portal. Two details directly support the spec:
- The upload form has the **"reporting month is greyed out unless this is Remittance advice"** rule the spec asked for. This is implemented as small JavaScript that reacts to the type chosen.
- The contacts form **soft-warns** when a Provider tries to add a sixth contact (matching the spec's "up to .. 5 contacts?" guidance) but does not block them, since some Providers may legitimately need more.

| Form | Notes |
|---|---|
| `DocumentUploadForm` | Multi-file via `<input multiple>`. Because the site is on **Django 3.2** (no `MultipleFileField`), we add a tiny `MultipleFileInput(ClearableFileInput)` with `allow_multiple_selected = True` and a `MultipleFileField(forms.FileField)` that validates each item in `data` — the standard Django 3.2 pattern — and the view loops over `request.FILES.getlist("file")`. Fields: `document_type`, `reporting_month` (gated by JS on the type's `requires_reporting_month` flag), per-file `display_name` overrides |
| `DocumentEditForm` | Edit `display_name`, `document_type`, `reporting_month`, `notes`. File replacement creates a new Document row (we don't version in this iteration; deletion + re-upload covers correction during the 2h grace window) |
| `BulkImportZipForm` | Single ZIP upload + `notify_on_commit` checkbox |
| `ProviderContactForm` | Per-row inline form. Position auto-numbered. JS warns when adding a 6th contact but never blocks the save — the "up to 5" guidance is *soft* (client clarification 4); the model imposes no cap |
| `NotificationPreferencesForm` | One radio **per `ProviderContact`** (not per Provider): immediate / daily / weekly / monthly / off — so each contact at a Provider sets their own cadence (client clarification 5) |
| `AcceptInviteForm` | Sets password, optionally edits name/job_title; on save creates `User`, links to `Initiative.users`, marks `ProviderContact.user`/`accepted_at` |

The codebase uses `crispy_forms` with `CRISPY_TEMPLATE_PACK = "bootstrap4"` (`src/intrepid/settings.py`); these forms follow that convention (`FormHelper` + `Layout` + `Submit`).

---

## 7. Templates

**In plain language.** "Templates" are the HTML files that produce the rendered web pages — the actual screens that OBC and Provider Members see in their browser. They reuse the existing OBC site styling so the new portal looks like part of OBC, not a bolt-on. The list below names each screen plus the four email layouts (one per email type the system can send). Email content is also editable via the existing OBC admin email-template system, so OBC can refine wording without involving an engineer for every word change.

Under `src/templates/portal/`. Reuses the bootstrap4 base in `src/templates/base/` (shared page context is injected by `intrepid.middleware.variables_middleware`, not classic context processors).

```
portal/
    base.html                # extends base/frontend/base.html, adds left-nav for Documents
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

Email templates are primarily driven through `mail.EmailTemplate` rows (admin-editable subjects/bodies, per existing pattern at `src/mail/models.py:35`). The `EmailTemplate` model has just three fields — `name`, `subject`, `body` (no separate slug column), so rows are looked up by `name`. The HTML files above are loaded as the *initial* `body` content during a data migration that creates the `EmailTemplate` rows via `get_or_create(name=...)`; runtime renders use `EmailTemplate.send(to, context)` (`src/mail/models.py:159`), which accepts a single address or a list and returns whatever the underlying transport returns (an int for Django SMTP, a dict/str for Mailgun) — so tests assert on persisted state, not on this return value.

---

## 8. Notification system

**In plain language.** This is one of the more involved parts of the build because it satisfies several of the spec's most precise requirements at once: per-Provider-Member preference for *immediate / daily / weekly / monthly*, plus the "no immediate emails for two hours after upload" grace window, plus the implicit requirement that one digest email summarise multiple new documents instead of spamming the recipient.

The flow:
1. OBC uploads a document.
2. The system instantly creates one *pending email row* per Provider Member who has that Provider in their contacts list and has notifications turned on. Each pending row carries a "due time": for an immediate subscriber, that's *upload time + 2 hours*; for a daily subscriber, the next 09:00; for weekly, the next Monday 09:00; for monthly, the 1st of next month.
3. Every fifteen minutes, a scheduled task wakes up, looks for pending rows whose due time has passed, groups them per recipient (so a daily-digest user gets *one* email listing all their day's new documents), sends the email, and marks them sent.
4. **If OBC deletes a document inside the grace window (or any time before its email has fired), every pending row for that document is cancelled instantly. No erroneous email goes out.** This is exactly the "delete and replace without a notification" behaviour the spec requested.

The "every 15 minutes" rhythm is a deliberate trade-off: it's frequent enough that "immediate" feels close to immediate (worst-case 2h 15m delay vs the desired 2h), but it doesn't hammer the database between events.

### Trigger points

- **On `Document` save (`post_save`):** if `created and not _bulk_import_silent`, enqueue one `NotificationQueue` row per `ProviderContact` of `document.initiative` whose `notification_frequency` is not `off`. `eligible_at` is computed per-frequency:
    - `immediate` → `document.notification_eligible_at` (uploaded_at + 2h grace)
    - `daily` → next 09:00 in the project timezone
    - `weekly` → next Monday 09:00
    - `monthly` → 1st of next month, 09:00

- **On `Document` delete:** mark all unsent rows for that document `cancelled_at = now()`. Honours the spec's grace-window intent: if OBC deletes a misuploaded file before its `eligible_at`, no email goes out and no digest is ever created featuring that message.

### Cron drain

New management command: `src/portal/management/commands/send_document_notifications.py`.

Logic per run:
1. Select `NotificationQueue` rows where `sent_at IS NULL AND cancelled_at IS NULL AND eligible_at ≤ now()`.
2. Group by `(recipient, frequency, eligible_at_bucket)` so digest recipients receive one email summarising N documents instead of N emails. Bucket key = `(recipient_id, frequency, date_floor(eligible_at, frequency))`.
3. For each group, render via `EmailTemplate.send(to=recipient.email, context={...})`. Immediate uses the `document_notification_immediate` template; digests use `document_notification_digest` with a `documents` list in the context.
4. Mark all queue rows in the group `sent_at = now()`.
5. Atomic per-group transaction so a render failure doesn't half-mark the bucket.

Add the job to the existing cron installer at `src/install/management/commands/install_cron.py`:

```python
{
    "name": "{}_intrepid_send_document_notifications".format(cwd),
    "time": 15,              # run every 15 minutes
    "task": "send_document_notifications",
},
```

No installer change beyond this dict is needed: the existing loop already calls `cron_job.minute.every(job["time"])` whenever `time != -1` (the `-1` sentinel is reserved for the monthly `sync_thoth` job), so a `time` of `15` schedules the job every 15 minutes. The crontab line it writes invokes `{BASE_DIR}/manage.py send_document_notifications` (via the virtualenv's `python3` when one is active).

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

**In plain language.** The spec is explicit: Provider Members can edit their own contact details, but OBC must be alerted when they do. Two things happen whenever a Provider edits their name, surname, job title, email, or notification frequency:
1. An email is sent to the OBC team's main address listing exactly what changed (old value → new value).
2. A permanent record is written to the *contact change log*, viewable from OBC's portal under "/portal/obc/contact-changes/", so even if an email is missed, OBC has an auditable history.

`ProviderContact.save()` overridden to diff against `__class__.objects.get(pk=self.pk)` for existing rows. When tracked fields (`first_name`, `last_name`, `job_title`, `email`, `notification_frequency`) change:
1. Persist a `ContactChangeLog` row.
2. Send `EmailTemplate.objects.get(name="contact_change_notification").send(to=settings.FROM_EMAIL, context={...})`. (`FROM_EMAIL` is set at `src/intrepid/settings.py:228-235`.)

The change log is exposed at `/portal/obc/contact-changes/` (filterable by Initiative) and via `admin.py`.

---

## 10. Invitation flow

**In plain language.** This is how a real human at a Provider becomes able to log in. OBC adds them as a contact, clicks "send invitation", and the system emails the contact a one-time link. When they click it, they land on a page that asks them to set their own password. Once they do, the system silently links their new account to their Provider, drops them into the right group, and sends them straight to the documents list for their Provider — no further setup required. Multiple people from the same Provider can be invited individually, supporting the spec's "multiple accounts relating to the same Provider".

The one-time link is unique and can only be used once; if it's already been accepted, anyone who follows it later sees a polite "already accepted" page rather than being able to hijack the account.

OBC creates a `ProviderContact` row (no `user` yet, `invite_token` auto-generated). A "Send invitation" action emails the contact a link `/portal/invite/accept/<uuid:token>/`.

`accept_invite` view:
1. Looks up `ProviderContact` by token; 404 on miss; gone-message if `accepted_at` already set.
2. If the email already matches an existing `User`, presents a "log in to accept" path; otherwise shows `AcceptInviteForm`.
3. On accept: creates the `User`, adds them to `Initiative.users`, adds them to the `Provider Members` Group, fills `ProviderContact.user` + `accepted_at`, and logs them in.
4. Redirects to `/portal/provider/initiative/<id>/`.

---

## 11. Translation

**In plain language.** The OBC site is already bilingual (English + German). The new portal joins that arrangement. The names and descriptions of document types — the things OBC will actually want translated, since they're the labels Provider Members see in the type filter — can be edited in both languages from the existing OBC translation tooling. Document filenames, free-text notes, and email *bodies* remain in their original language; translating those is out of scope for v1 (and likely never desired for filenames anyway).

`src/portal/translation.py` registers translatable fields, mirroring `src/vocab/translation.py` — which uses the module-level `translator.register(Model, Options)` form (not the `@register` decorator), so we follow that house convention:

```python
from modeltranslation.translator import translator, TranslationOptions
from portal import models


class DocumentTypeTranslation(TranslationOptions):
    fields = ("name", "description")


translator.register(models.DocumentType, DocumentTypeTranslation)
```

`Document.display_name` is **not** translated (it's user-supplied per upload). Email template rows in `mail.EmailTemplate` are not translated by modeltranslation today; following spec scope, they remain English-only and a follow-up issue can address per-language email bodies.

---

## 12. Django Admin System and Existing Dashboard

**In plain language.** There are 2x backends: Django (the framework the OBC site uses) ships with a generic backend it calls "the admin". Then there is "the dashboard", which allows OBC staff to configure how the site works. This is the cluttered area the spec's GENERAL note asks to be tidied up. We are *not* using it as the home for the documents portal — that lives in §1's bespoke screens — but every model still gets a small, minimal entry in "the admin" as a developer fallback for emergency database fixes. Day-to-day, neither OBC team nor Provider Members will need to look at the admin. Cleaning up the rest of the Dashboard is deferred to a separate, follow-up issue — see §17.

Minimal — the portal is the primary UI, not the Django Admin or the existing dashboard. `src/portal/admin.py` registers:

- `DocumentTypeAdmin` (list_display: name, slug, requires_reporting_month, default, ordering)
- `DocumentAdmin` (raw_id_fields: initiative, document_type, uploaded_by; list_filter: document_type, initiative; search_fields: display_name, original_filename)
- `ProviderContactAdmin` (list_display: name, email, initiative, position, notification_frequency, accepted_at; list_filter: initiative, notification_frequency)
- `ContactChangeLogAdmin` (read-only)
- `DocumentTypePermissionAdmin`
- `NotificationQueueAdmin` (read-only debugging aid; list_filter: frequency, sent_at)

Follows the registration idiom at `src/initiatives/admin.py:24-29`.

---

## 13. Tests (red/green TDD)

**In plain language.** Before writing any working code, we write a list of automated checks ("tests") that describe what the system *should* do — does the upload form refuse a remittance advice without a reporting month? Does deleting a document cancel its pending notifications? Does an unauthorised user get a 403 if they guess another Provider's URL? These tests are then run continuously as the build progresses; the moment a regression is introduced, the test that protects that behaviour fails. This means: (a) bug-fix work down the road can't accidentally break working features, (b) when this plan says a feature is "done", a non-tech reader can ask "is the test green?" as a simple, unambiguous status check.

A small but important piece of discipline (per OBC's standing engineering convention): tests deliberately don't pin down *exact wording* of email subject lines or button labels — those should remain easy to refine later — but they do pin down behaviour like "an email was sent", "the queue row was marked sent", "permission was denied".

Write failing tests first against stubs, then implement until green. Each behavioural function/method under test gets a `NotImplementedError`-raising stub before its real body exists (model *fields* are defined up-front so the test database can be built, but the behavioural methods — `clean()`, the `save()` diff, the upload-path helper, the permission helpers, the parser, the queue logic — start as stubs that raise, so the first test run fails for the right reason).

Tests live in a `src/portal/tests/` **package** (one module per area: `test_models.py`, `test_permissions.py`, `test_bulk_import.py`, `test_notifications.py`, `test_forms.py`, `test_views.py`, `test_invitation.py`) rather than a single `tests.py`, so the areas can be built independently. They are Django `TestCase` subclasses with no live network/email: the active settings have `USE_MAILGUN=True`, so every test path that could send mail patches `mail.EmailTemplate._send_email` (or `EmailTemplate.send`) via `unittest.mock.patch` — otherwise a test would attempt a real Mailgun HTTP call. Run them with `uv run ./manage.py test portal --settings=intrepid.test_settings` (the test settings swap in the in-repo `fluid_permissions` migrations). Coverage:

**Models**
- `Document.notification_eligible_at` is set to `uploaded_at + DOC_NOTIFICATION_DELAY`.
- `portal_documents_upload_path()` produces a UUID-renamed path under `provider_documents/<initiative_pk>/`.
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
- Digest grouping: 3 documents for one daily-digest recipient resolve to a single send whose context carries all three documents (asserted by capturing the context handed to the mocked send and checking it lists three documents — i.e. behaviour, not a raw call-count).
- A digest contact's three documents collapse to one grouped send; an immediate contact's three documents resolve to three. (Asserted via persisted `sent_at` state and the captured render context, so the assertions survive a change of email backend.)

**Invitation**
- Accepting an invite creates the User, links to Initiative.users, sets `accepted_at`.
- Re-accepting the same token shows a "already accepted" page rather than re-using.

Tests follow standard practice: testing behaviour, not implementation. They mock `EmailTemplate._send_email` and assert on returned/persisted state, not call counts.

Important note: tests around exact wording (email subject text, button labels) are **written then deleted** as a discipline aid — they shouldn't constrain copy edits.

---

## 14. Migrations & data seeding

**In plain language.** A "migration" is the script that updates the live OBC database to add the new tables this build needs. A "data seed" pre-populates that database with the initial content the portal needs to be functional from day one — namely:
- The two starter document types ("Remittance advice", "Agreement contract"). OBC can add more later.
- The two user groups ("OBC Team" and "Provider Members") so permissions can be assigned immediately.
- The four email templates (immediate notification, digest notification, contact-change alert, invitation) so OBC isn't faced with a blank slate.

These run automatically when the new code is deployed. OBC doesn't need to do anything manual to "switch the portal on".

A single initial migration (`0001_initial.py`) creates all six models. A second data migration (`0002_seed.py`) populates (all steps idempotent via `get_or_create`, so re-running is safe):
- Two `DocumentType` rows ("Remittance advice" with `requires_reporting_month=True, default=True`; "Agreement contract" with `requires_reporting_month=False`).
- The `OBC Team` and `Provider Members` `auth.Group` rows.
- `EmailTemplate` rows looked up by `name` (`document_notification_immediate`, `document_notification_digest`, `contact_change_notification`, `provider_invite`), using the HTML files in `templates/portal/emails/` as the initial `subject`/`body`. (`EmailTemplate` has no slug field — `name` is the key.)
- *(Deferred.)* The portal gates the OBC area with its own `obc_area_required`/`obc_staff_required` decorators plus per-type `DocumentTypePermission`, rather than `fluid_permissions.ViewGroup` per-view gating. Seeding `ViewGroup` rows would surface the portal views in `/accounts/manage_fluid_permissions/` but, because the portal views do not use `user_in_authorised_group`, those rows would not actually restrict access — so they are intentionally **not** seeded, to avoid misleading, non-functional configuration. Layering `fluid_permissions` on top is a small, self-contained follow-up if per-view gating is later wanted.

The migration uses `apps.get_model(...)` for `DocumentType`/`Group`/`EmailTemplate`/`ViewGroup` (the historical-model pattern), reading the seed email bodies with Django's template loader so the HTML files remain the single source of truth.

---

## 15. Critical files — to be created or modified

**In plain language.** This is essentially a "scope of works" inventory: the complete list of files the engineer will touch to deliver everything above. Almost all of the work is *new* files (in the new `portal/` area), with only three existing files needing small additions. This is a useful sanity check on the size of the change — the new portal is a self-contained body of work, not a sprawling rewrite of the existing site.

**Created**
- `src/portal/__init__.py`, `apps.py`, `models.py`, `admin.py`, `forms.py`, `views.py`, `urls.py`, `translation.py`, `bulk_import.py`, `notifications.py`, `permissions.py`, `signals.py`
- `src/portal/tests/__init__.py` + `test_models.py`, `test_permissions.py`, `test_bulk_import.py`, `test_notifications.py`, `test_forms.py`, `test_views.py`, `test_invitation.py` (+ `_helpers.py`)
- `src/portal/management/__init__.py`, `management/commands/__init__.py`, `management/commands/send_document_notifications.py`
- `src/portal/migrations/0001_initial.py`, `0002_bulkimportjob_bulkimportrow.py`, `0003_*` (modeltranslation fields), `0004_seed.py`
- `src/templates/portal/*` (per §7)

**Modified**
- `src/intrepid/settings.py` — add `portal` to `INSTALLED_APPS`; add `DOC_NOTIFICATION_DELAY`, `DOC_DIGEST_*` constants
- `src/intrepid/urls.py` — add `path("portal/", include("portal.urls"))`; change the existing `path("dashboard/", …)` to `path("staff/", …)` (URL restructure, client clarification 1)
- `src/templates/base/frontend/nav.html` — re-point the top-right "Dashboard" link from `dashboard_index` to the new portal index. (The old dashboard's own sidebar in `src/templates/base/admin_nav.html` is intentionally left pointing at `dashboard_index`: it is the navigation *inside* the old dashboard, now at `/staff/`, and must keep working there.)
- `src/install/management/commands/install_cron.py` — add the `send_document_notifications` job dict (`time: 15`); no dispatcher change is needed (the existing `time`-based path already schedules `minute.every(...)`)

---

## 16. Verification That It's Working

**In plain language.** This is the checklist that shows that everything works before declaring "done". It includes: running the database migrations on a copy of the real OBC database (so we know there are no clashes); running every automated test; installing the new fifteen-minute notification job into the server's scheduler; and a guided walkthrough that exercises every feature the spec asked for, in the order a real user would. If any step fails, we fix it before saying the feature is shipped.

End-to-end checks before declaring done:

1. **Migrations apply cleanly:** `uv run ./manage.py makemigrations portal && uv run ./manage.py migrate`. Re-run on a copy of `obc_db.sqlite3` to confirm no clashes with existing data.
2. **Tests pass:** `uv run ./manage.py test portal --settings=intrepid.test_settings` — all green.
3. **Translations:** `uv run ./manage.py update_translation_fields` (modeltranslation pattern used for `BandingVocab` recently — see commit `b9a48e0`) followed by `uv run ./manage.py makemessages -l de && compilemessages`.
4. **Cron install:** `uv run ./manage.py install_cron --action test` shows the new job alongside `sync_thoth`.
5. **Browser walkthrough** (Django dev server on `https://localhost`, self-signed cert):
   - Sign in as superuser → upload a single PDF for an Initiative → confirm it appears in the OBC list.
   - Upload a multi-file batch → confirm all rows created.
   - ZIP a fixture matching `<short_code>/YYYY-MM/*.pdf` for two Initiatives → bulk-import dry-run preview shows correct mapping → commit → both `Document` rows appear.
   - Create a `ProviderContact`, send invitation, accept the invitation as a fresh user, log in, view the documents list scoped to that Initiative, change frequency to "daily", edit name → confirm OBC inbox receives `contact_change_notification`.
   - Manually `update NotificationQueue set eligible_at = '2020-01-01'` then run `uv run ./manage.py send_document_notifications` → confirm rows marked sent and (mock) email rendered.
   - Bulk-download three documents from the provider view → confirm streamed ZIP contains the three files at their `original_filename`.
6. **Permission probes:** log in as a non-staff user with no Initiative membership → verify 403 on every `/portal/obc/*` and on `/portal/provider/initiative/<other>/`.
7. **URL restructure:** confirm the top-right "Dashboard" link now lands on `/portal/`; confirm the old dashboard still works when visited directly at `/staff/` and that its internal links (which resolve by name) are intact; confirm `/dashboard/` no longer resolves.
8. **Lint/format:** `uv run ruff check src/portal` and any pre-commit hooks defined for the repo. Fix and re-stage before committing.

---

## 17. Out of scope (deferred)

**In plain language.** Things this build deliberately does *not* include, with the reasoning, so OBC can decide whether to commission them as separate follow-up work later:

- **Tidy-up of the wider Django admin and Dashboard to hide irrelevant models from Provider Members.** The portal in this build is its own self-contained dashboard, so Provider Members never need to enter the existing admin/dashboard. Hiding things in the wider admin/dashboard is a separate, larger, more risk-laden piece of work — best done once we know exactly which models OBC vs Providers really need to see. We need much more specification and guidance as to, for example, what will actually be taken out here?
- **Document versioning / replacement history.** If OBC needs to fix a typo on a document already past its 2-hour grace window, the answer for v1 is "delete and re-upload". A future enhancement could store every version automatically.
- **Email-link pickup of very large bulk-download archives.** Today's bulk download streams the ZIP as the user waits. If, in a year, archives become so large that this is uncomfortable, we could email the user a download link instead. Not needed now.
- **A public API for the portal.** The existing OBC API is untouched and remains available; the portal is reachable only through the browser.
