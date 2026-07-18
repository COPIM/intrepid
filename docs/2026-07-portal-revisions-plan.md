# Portal revisions — July 2026

Eleven revisions to the document portal (`src/portal/`), covering bulk-import
filename tolerance, a three-tier permission model (Admin / Provider / Contact),
translation tooling, document-list UX, upload notification controls, email
attachments, and an email-queue management screen.

## Global Constraints

These bind every task below.

- **Stack:** Django 3.2.8, Python 3.12, uv-managed. Run everything as
  `uv run ./manage.py …` from `src/`.
- **Tests:** `cd src && uv run ./manage.py test portal --settings=intrepid.test_settings --keepdb`
  (Postgres runs in Docker and is already up). The suite currently passes with
  110 tests — it must still pass, plus your new tests, when you finish.
- **TDD is mandatory (red/green):** write failing tests FIRST, run them and
  confirm they fail for the right reason (stub new functions with
  `raise NotImplementedError` where needed — an ImportError is not a valid
  red), then implement until green. Tests must exercise behaviour (return
  values, response content, DB state), never implementation details (no
  call-counting, no asserting on logging). For pure-content changes (wording,
  HTML copy) write the tests anyway to guide the work, then DELETE them before
  the final commit so future content edits are not constrained.
- **Settings files are git-ignored** (`src/intrepid/settings.py` is a symlink
  to `dev_settings.py`). Do not rely on committing settings changes; if a task
  needs a new setting, document it in `PORTAL.md` instead.
- **Translatable UI strings** use the `cms.SiteText` system: templates call
  `{% get_site_text 'key' %}`, forms call `portal.forms.site_text(key, default)`.
  Every NEW user-visible string must be seeded as a `SiteText` row via a portal
  data migration (copy the pattern of
  `src/portal/migrations/0011_portal_contact_user_split.py`) with a key
  prefixed `portal_` — the prefix is what makes portal strings findable in the
  dashboard translation screen. Seed both `body` and `body_en`.
- **Migrations:** portal migrations are numbered sequentially; take the next
  free number when you create one (check `src/portal/migrations/` first —
  earlier tasks in this plan may have added some).
- **Commits:** conventional-commit style, e.g. `feat(portal): …` /
  `fix(portal): …`. No issue number (none exists for this work). Do NOT
  credit Claude, any LLM, or anybody else in commit messages — no
  Co-Authored-By lines, no session links.
- **Notification system invariants** (do not break):
  - Uploading a `Document` fires the `post_save` signal
    (`src/portal/signals.py`) which calls
    `notifications.enqueue_for_document` unless the instance carries the
    suppress attribute (currently `_bulk_import_silent`).
  - Immediate notifications become eligible at
    `uploaded_at + settings.DOC_NOTIFICATION_DELAY` (2-hour safety buffer);
    digest rows get the recipient's next daily/weekly/monthly slot.
  - A cron job (`send_document_notifications`) drains
    `NotificationQueue` every 15 minutes via
    `notifications.send_pending_notifications`, grouping digest rows.
  - Deleting a document cancels its unsent rows
    (`notifications.cancel_for_document` + FK cascade).
- **Portal pages** extend `src/templates/portal/base.html`, which extends
  `base/frontend/base.html`. The frontend base does NOT load jQuery. If a
  portal page needs DataTables, load jQuery + DataTables from the CDN inside
  `{% block js %}` in that template (see
  `src/templates/elements/datatables.js.html` for the CDN versions used
  elsewhere — but do not modify that shared include, and do not include it on
  portal pages; write a page-local init so you can control paging/searching).
- The old configuration dashboard is mounted at `/staff/`
  (`dashboard.urls`, index URL name `dashboard_index`); the translation screen
  is `cms.views.list_site_text` (URL name `list_site_text`) rendering
  `src/templates/cms/site_text_list.html`.

---

## Task 1 — Bulk import: tolerate a leading underscore in filenames

**User requirement (item 1):** ZIPs sometimes contain files whose *basename*
starts with an underscore, e.g.
`2026-04/_2026-04 OBC Accounts Report - OBP.pdf`. These must be parsed exactly
like their underscore-less equivalents (same reporting month, same provider
match). The existing naming convention must keep working unchanged.

**Where:** `src/portal/bulk_import.py`. The current pipeline:
`parse_zip` → `_classify(archive_path, default_type)`;
`MONTH_DIR_RE` requires `YYYY-MM/<basename>.<ext>`; `REPORT_NAME_RE`
(`^\d{4}-\d{2}.*\s-\s(?P<provider>.+)$`) requires the basename to START with
the date, so a leading `_` currently lands the file in "skipped".

**Implementation:**
- Allow one or more leading underscores before the date in `REPORT_NAME_RE`
  (e.g. `^_*\d{4}-\d{2}…`). The provider group and everything else stays the
  same.
- CRITICAL: do NOT let macOS AppleDouble junk through — files whose basename
  starts with `._` (e.g. `2026-04/._2026-04 Report - OBP.pdf`) are binary
  resource forks, and `_classify` already ignores basenames starting with `.`
  plus `__MACOSX` paths. That behaviour must be preserved (add a regression
  test proving `._`-prefixed files are still ignored).
- Duplicate detection compares `original_filename`, which includes the
  underscore — that is fine, leave it.

**Tests** (extend `src/portal/tests/test_bulk_import.py`, following its
existing patterns): underscore-prefixed conforming file → `ok` with correct
initiative + reporting month; underscore-prefixed non-conforming file still
`skipped`; `._` AppleDouble still ignored entirely; existing tests untouched
and passing.

---

## Task 2 — Rename "Agreement contract" → "Contract"; add an "Other" document type

**User requirement (items 4a, 4b).**

**Where:** document types are `portal.DocumentType` rows seeded by
`src/portal/migrations/0004_seed.py` ("Remittance advice", "Agreement
contract"). The model is registered with modeltranslation
(`src/portal/translation.py`), so rows have `name` + `name_en` (+ `name_de`).

**Implementation:** one new portal data migration that:
- Renames the `DocumentType` with slug `agreement-contract`: set `name` and
  `name_en` to `"Contract"` (leave `name_de` alone if set, and leave the slug
  alone — it is a stable permission key referenced nowhere by display).
  Guard with `.filter(slug="agreement-contract")` so a missing row is a no-op.
- Creates (get_or_create by slug) a `DocumentType` with `slug="other"`,
  `name="Other"`, `name_en="Other"`, `requires_reporting_month=False`,
  `default=False`, `ordering=3`.
- Reverse migration: rename back to "Agreement contract"; leave "Other" in
  place if any `Document` references it, otherwise delete it.

**Tests** (`src/portal/tests/test_models.py` or a small new migration test):
after migrations, a `DocumentType` named "Contract" with slug
`agreement-contract` exists, and one with slug `other` named "Other" exists.
(Behavioural, not wording-fussy: assert on the slugs existing and the renamed
row no longer being called "Agreement contract".)

---

## Task 3 — Documents table UX: clear-filter button, sortable columns, select-all download

**User requirement (items 4c, 4d, 4e).**

**Where:** the Provider documents view
`src/templates/portal/provider_initiative_documents.html` (view
`provider_initiative_documents`) and the OBC equivalent
`src/templates/portal/obc_initiative_detail.html` — both render the same
filter form (document type / reporting month / free-text q) and a documents
table; the provider one has per-row checkboxes posting to
`portal:bulk_download`.

**Implementation:**
1. **Clear filter (4c):** on BOTH templates' filter forms, add a "Clear
   filters" button beside "Filter". A plain link to the page's own URL with no
   query string is the simplest robust implementation (`href="{% url … %}"`);
   a JS reset is acceptable too, but the result must be that all filters are
   cleared AND the unfiltered list is shown. Label via a new SiteText key
   (e.g. `portal_clear_filter`, default "Clear filters"), seeded by data
   migration.
2. **Sortable columns (4d):** make the Provider view table a DataTable with
   ALL data columns sortable (Name, Type, Reporting month, Uploaded). The
   checkbox column and the download-link column must NOT be sortable
   (`orderable: false`). Load jQuery + DataTables CDN assets in
   `{% block js %}` (see Global Constraints). Give the table an `id`.
   Reporting month and Uploaded cells already render sortable-friendly
   `Y-m` / `Y-m-d H:i` strings — string ordering is chronologically correct.
3. **No pagination + select all (4e):** I have confirmed the current table
   has no pagination (it is a plain full list). Keep it that way: initialise
   DataTables with `paging: false`, `info: false`, `searching: false` (the
   server-side filter form already covers search). Then add a "select all"
   master checkbox in the checkbox column header that checks/unchecks every
   row checkbox (plain JS). Because paging is off, every row stays in the DOM,
   so the existing "Download selected" POST to `portal:bulk_download`
   correctly downloads everything when select-all is on. No "Download All"
   zip endpoint is needed — do not build one.

**Tests:** view tests asserting the pages still render (200) with the new
elements present in the response for a provider user and an OBC user. The
select-all/DataTables behaviour is client-side JS — write template-render
tests during development, then delete purely content-assertion tests before
the final commit (keep the 200-render ones if they add coverage).

---

## Task 4 — Notification checkboxes on both upload paths

**User requirement (items 5, 6):** bulk upload's "Send notifications" must
default to TICKED; the individual upload form must gain a "Send notification"
checkbox, ticked by default, controlling whether notifications are enqueued
(with the usual 2-hour buffer).

**Where:**
- Bulk: `BulkImportZipForm.notify_on_commit` in `src/portal/forms.py`
  (currently `initial=False`); flows through
  `views.obc_bulk_import` → `bulk_import.stage_job(notify_on_commit=…)` →
  `commit_job` which sets `document._bulk_import_silent = True` when the job
  is silent.
- Individual: `DocumentUploadForm` + `views.obc_upload`, where each saved
  `Document` currently always triggers the `post_save` enqueue signal.

**Implementation:**
1. Change `notify_on_commit` to `initial=True`.
2. Add `send_notification = forms.BooleanField(required=False, initial=True)`
   to `DocumentUploadForm`, labelled via a new SiteText key
   (e.g. `portal_form_send_notification`, default "Send notification",
   seeded by data migration alongside any other new keys from this task).
3. In `obc_upload`, when `send_notification` is False, set the suppress
   attribute on each `Document` before `save()` so the signal skips enqueueing.
4. Rename the suppress attribute from `_bulk_import_silent` to
   `_suppress_notifications` everywhere (signals.py, bulk_import.py, the new
   upload path, and any tests) — it no longer only concerns bulk import. Keep
   it one attribute; do not invent a second flag.
5. When the box IS ticked, behaviour is exactly today's: enqueue rows whose
   immediate eligibility honours the 2-hour `DOC_NOTIFICATION_DELAY`.

**Tests** (forms + views): form initials are True; uploading with the box
ticked creates `NotificationQueue` rows with `eligible_at` 2 hours after
upload for immediate-frequency contacts; uploading with it unticked creates
NO rows; bulk commit respects `notify_on_commit` both ways (existing tests
cover much of this — update them for the rename).

---

## Task 5 — Remove the Notes field from document editing

**User requirement (item 7).**

**Where:** `DocumentEditForm` in `src/portal/forms.py` (fields list includes
`"notes"` and a `site_text` label for it); template
`src/templates/portal/obc_document_edit.html` renders the form via crispy.

**Implementation:** remove `"notes"` from the form's fields and drop its label
line. KEEP the `Document.notes` model column (no destructive schema change —
existing data stays). Check no template renders `document.notes` anywhere
(grep `src/templates/portal/`); remove renderings if found.

**Tests:** a view test asserting the edit form does not contain a notes field
and that submitting the form without notes still saves the other fields.

---

## Task 6 — Attach the document file to outbound notification emails

**User requirement (item 8):** notification emails linked to documents (bulk
or individual upload) must carry the document file(s) as attachment(s).

**Where:** `notifications._send_group` (`src/portal/notifications.py`) calls
`EmailTemplate.send(to, context)`; `mail.models.EmailTemplate.send` /
`_send_email` accept an `attachments` list of file PATHS but only the Mailgun
branch uses it — the plain-Django branch (`EmailMultiAlternatives`) silently
ignores attachments.

**Implementation:**
1. In `_send_group`, pass `attachments=[d.file.path for d in documents]`
   (immediate emails: the single document; digests: every document in the
   group). Skip paths whose file is missing on disk rather than crashing the
   cron drain — an email without its attachment must still send.
2. In `mail.models._send_email`, make the non-Mailgun branch attach each path
   (`msg.attach_file(path)`) so both backends honour `attachments`. In the
   Mailgun branch, the open file handles should be closed after the POST
   (wrap in a try/finally or context management) — fix this while you are
   here since you are making attachments actually used.
3. Do not change the queue/digest grouping semantics.

**Tests:** portal notification tests (mock `EmailTemplate.send` or use the
Django locmem email backend via `django.core.mail.outbox`) asserting that
sending a due immediate notification produces an email whose attachments
include the document's file, and a digest email carries all its documents'
files; a missing file does not raise and the email still goes out.

---

## Task 7 — Admin shortcut from the portal homepage to the main dashboard

**User requirement (item 9):** when logged in as an admin, the Portal
homepage must offer a button to the main admin dashboard.

**Where:** the OBC portal homepage is `views.obc_dashboard` rendering
`src/templates/portal/obc_dashboard.html` (tiles UI, `portal-tile` divs).
The main admin dashboard is the old configuration dashboard at `/staff/`,
URL name `dashboard_index`.

**Implementation:** add a tile (or clearly-visible button) on
`obc_dashboard.html` linking to `{% url 'dashboard_index' %}`, shown only when
`request.user.is_staff` (the dashboard itself is staff-gated; OBC-area users
who only hold `DocumentTypePermission` read access are not necessarily staff
and must not see a dead link). Label + description via new seeded SiteText
keys (e.g. `portal_tile_admin_dashboard*`).

**Tests:** obc_dashboard renders the dashboard link for a staff user and not
for a non-staff user with document-type access. (Assert on the `/staff/` href,
not the wording.)

---

## Task 8 — Filter portal strings in the dashboard translation screen

**User requirement (item 3):** on the old dashboard's translation interface
there must be a search such that typing "portal" shows all the portal's
translation strings.

**Where:** `cms.views.list_site_text` → `src/templates/cms/site_text_list.html`,
which already initialises DataTables via
`{% include "elements/datatables.js.html" with target='site-texts' %}` inside
`{% block dashboard_js %}`. DataTables ships a global search box by default.
All portal strings use keys prefixed `portal_` (verify: grep
`src/portal/migrations/` and `src/portal/forms.py`), so a "portal" search on
the Key column is exactly the requested filter.

**Implementation:**
1. Verify end-to-end that the search box actually renders and filters on this
   page (check the template/include wiring; if the DataTable fails to
   initialise — e.g. asset order or duplicate jQuery — fix it).
2. Make the filter discoverable and one-click: add a small quick-filter
   control above the table (e.g. buttons/links "All" and "Portal") that set
   the DataTables search to `""` / `"portal"` via its API. Keep it tiny and
   dependency-free.
3. Ensure every portal SiteText key is matched by that search (they all start
   with `portal_`; if you find any that do not, note it in your report — do
   not rename keys, renames would break templates).

**Tests:** a view test that `list_site_text` returns 200 for staff and its
context contains portal-prefixed site texts. The JS filtering itself is
client-side: write render-assertion tests during development and delete the
content-coupled ones before the final commit.

---

## Task 9 — Three-tier permissions: Admin / Provider / Contact

**User requirement (item 2):**
- Admin = OBC staff → can do everything (unchanged).
- Provider = the initiative's managing users → can access and manage their
  initiative (documents, contacts, users pages as today).
- Contact = less powerful: CAN log in, CAN see/download their initiative's
  documents, CANNOT manage the initiative or add users/contacts.
- (2a) A logged-in Contact must NOT see "Add a contact" on the Contacts pane.
- (2b) On the notifications page a Contact sees and edits ONLY their own
  notification preference, not everyone's.

**Current state (verified):** there is no Contact tier. `ProviderContact` is a
notifications directory; a contact who is sent an invite
(`views.send_invite` → `accept_invite` → `_link_contact_to_user`) gets a User
that is added to `initiative.users` and the "Provider Members" group — i.e.
today every accepted contact becomes a full Provider manager
(`intrepid.security.user_is_initiative_manager` checks `initiative.users`).
The OBC "Manage Users" page (`obc_manage_initiative_users`) manages
`initiative.users` directly and has an "invite by email" flow
(`views.invite_by_email`) that pre-creates a User with an unusable password.

**Design (decided):**
- A user is a **Provider manager** for an initiative iff they are in
  `initiative.users` (or staff/superuser) — exactly the existing Layer A rule.
- A user is a **Contact** for an initiative iff a `ProviderContact` row with
  `user=that user` exists for the initiative and they are not a manager.
- Add `ProviderContact.is_login_invite = models.BooleanField(default=False)`
  (schema migration). `views.invite_by_email` (the Manage-Users flow, whose
  purpose is granting portal login/managership) sets it True at creation.
- `_link_contact_to_user` (invite acceptance) only does
  `contact.initiative.users.add(user)` when `contact.is_login_invite` is True.
  Contact-pane invitees therefore end up linked (`contact.user = user`, in the
  "Provider Members" auth group for template/permission purposes) but NOT in
  `initiative.users` — they get Contact-tier access.
- New helpers in `src/portal/permissions.py`:
  - `linked_contact(user, initiative)` → the user's `ProviderContact` for that
    initiative, or None.
  - `can_manage_initiative(user, initiative)` → staff/superuser or membership
    of `initiative.users` (reuse/mirror `intrepid.security._is_initiative_manager`).
  - `can_access_initiative(user, initiative)` → manager OR linked contact.
  - Decorator `initiative_access_required` mirroring
    `user_is_initiative_manager`'s kwarg handling but passing when
    `can_access_initiative` holds.
- View changes:
  - `provider_initiative_documents`, `provider_manage_contacts`,
    `provider_notification_prefs`: switch to `initiative_access_required`.
  - `provider_manage_contacts`: pass `can_manage = can_manage_initiative(...)`
    into the context. Server-side: a non-manager may POST edits ONLY for their
    own linked contact row (`contact_id` == their linked contact's pk);
    creating a new contact (no `contact_id`) requires manager. Violations →
    `PermissionDenied`.
  - `provider_notification_prefs`: for a non-manager, `contacts` contains only
    their linked contact, and the POST loop only processes that row (ignore or
    reject others' `frequency_<pk>` keys).
  - `delete_contact` stays manager-only (keep `user_is_initiative_manager`).
  - `index` and `provider_initiative_picker`: a Contact's initiatives must be
    reachable — union `request.user.Initiatives.all()` with initiatives where
    they have a linked contact (distinct), and route a single-initiative
    contact straight to its documents page, same as managers.
  - `_user_can_read_document` (used by `download_document` / `bulk_download`):
    also allow users with a linked contact for the document's initiative.
- Template changes:
  - `provider_contacts.html`: wrap the whole "Add a contact" section
    (heading, note, button, form) in `{% if can_manage %}`; also hide
    per-row Edit buttons for rows that are not the viewer's own contact when
    not manager, and rely on `is_obc` (already) for invite buttons. Delete
    forms: only for managers.
  - `provider_notification_prefs.html`: no structural change needed (the view
    filters `contacts`), but ensure the save button still shows for a contact
    editing their own row.
- Existing production data: users already in `initiative.users` (including
  previously-accepted contacts) KEEP manager access — no demotion migration.
  This is deliberate; OBC can prune on the Manage Users page. Note this
  clearly in your report.

**Tests** (this is the security-sensitive task — be thorough, red/green):
- Contact-tier user (linked contact, not in `initiative.users`): can GET the
  documents page and download that initiative's documents; CANNOT access
  another initiative's; sees no "Add a contact" (assert on the
  `add-contact-form` id / structural marker, not wording); GET notifications
  page shows only their own contact; POST creating a contact → 403; POST
  editing another contact's row → 403 (and no change persisted); POST editing
  their own row → saves.
- Manager user: everything works as before (existing tests keep passing).
- Invite flows: accepting a Manage-Users `invite_by_email` invite → user IS in
  `initiative.users`; accepting a contacts-pane invite → user is linked but
  NOT in `initiative.users`, and can log in and reach the documents page.

---

## Task 10 — Email queue management page (list, cancel, re-send)

**User requirement (item 10):** a page listing all emails, sent and unsent:
recipient, which user (and their name), status; sortable DataTable with
search; unsent emails first (default newest-first date sort); Cancel action
for unsent only (keeps the document); Re-send action for sent ones.

**Design (decided):** the page lists `portal.NotificationQueue` rows — that is
where "unsent but scheduled" emails live (the 2-hour buffer + digests), and
cancellation semantics ("keep the associated document") already exist as
`cancelled_at`. Rows: pending (`sent_at` and `cancelled_at` null), sent
(`sent_at` set), cancelled (`cancelled_at` set).

**Implementation:**
1. View `obc_emails` (`@obc_staff_required`) at `obc/emails/`, name
   `portal:obc_emails`: all `NotificationQueue` rows,
   `select_related("recipient", "recipient__user", "document",
   "document__initiative")`.
2. Template `src/templates/portal/obc_emails.html` (portal base): a table with
   columns — recipient email, contact name, linked user's name (blank if
   none), document (link to `portal:download_document`), initiative,
   frequency, eligible/sent date, status, actions. DataTable init in
   `{% block js %}` (jQuery + DataTables CDN, page-local init): sorting
   enabled, DataTables' built-in search box ENABLED (`searching: true`),
   paging allowed here (it is fine on this screen — actions are per-row
   links, not cross-row selection).
   Default ordering: status group first (Pending before Sent before
   Cancelled), then date descending. Implement deterministic sorting with
   `data-order` attributes (numeric sort keys: pending=0, sent=1,
   cancelled=2; dates as ISO strings/epoch) so unsent rows top the list
   newest-first.
3. Actions (both POST-only views, `@obc_staff_required`, with confirm on the
   page):
   - `obc_email_cancel` (`obc/emails/<int:queue_id>/cancel/`): allowed only
     when `sent_at` and `cancelled_at` are null → set `cancelled_at=now`.
     The document is untouched. Sent rows → error message, no change.
   - `obc_email_resend` (`obc/emails/<int:queue_id>/resend/`): allowed only
     when `sent_at` is set → re-send the same email immediately by calling
     `notifications._send_group(row.recipient, row.frequency,
     [row.document])` (extract/reuse rather than duplicating rendering
     logic; a small public wrapper like `notifications.resend_row(row)` is
     the clean shape), then update `sent_at=now`. Attachments behaviour
     follows Task 6 automatically.
4. Add a tile/link to the page from `obc_dashboard.html`.
5. All new labels/status strings via seeded `portal_`-prefixed SiteText keys.

**Tests:** page lists pending+sent+cancelled rows for OBC staff and 403s for
providers/contacts; cancel on a pending row sets `cancelled_at`, leaves the
`Document` row and file intact, and the drain (`send_pending_notifications`)
then sends nothing; cancel on a sent row changes nothing; resend on a sent
row sends one email (locmem outbox or mocked `EmailTemplate.send`) and
refreshes `sent_at`; resend on a pending row changes nothing.

---

## Task 11 — Translatable, editable notification email copy

**User requirement (item 11):** the copy of all the (portal) notification
emails must be translatable and editable, via an interface for admins only.

**Where:** the portal's four emails are `mail.EmailTemplate` rows (seeded by
`src/portal/migrations/0004_seed.py`): `document_notification_immediate`,
`document_notification_digest`, `contact_change_notification`,
`provider_invite`. `EmailTemplate` (`src/mail/models.py`) has `name`,
`subject`, `body` (a Django template string rendered with a context). The
site translates models with `django-modeltranslation` (see
`src/cms/translation.py`; languages come from `settings.LANGUAGES` — en/de).

**Implementation:**
1. Create `src/mail/translation.py` registering `EmailTemplate` with
   `fields = ("subject", "body")`, mirroring `cms/translation.py`.
2. Generate the mail-app schema migration for the new `subject_en/…de`,
   `body_en/…de` columns (`uv run ./manage.py makemigrations mail`), plus a
   data migration copying each existing row's `subject`→`subject_en`,
   `body`→`body_en` when the `_en` value is empty (the same effect as
   `update_translation_fields`, but self-contained for deploys).
3. Admin-only editing interface in the portal OBC area:
   - `obc_email_templates` (`@obc_staff_required`) at `obc/email-templates/`:
     lists the four portal template names above (query
     `EmailTemplate.objects.filter(name__in=…)`) with, per row and per
     language in `settings.LANGUAGES`, an edit link.
   - `obc_email_template_edit` (`@obc_staff_required`) at
     `obc/email-templates/<int:template_id>/<str:lang_code>/`: GET renders a
     form (subject `CharField`, body `Textarea`); POST saves inside
     `django.utils.translation.override(lang_code)` so modeltranslation
     writes the right language columns (the same trick as
     `cms.views.edit_site_text`). Show a warning note that the body is a
     Django template (variables like `{{ recipient }}` / `{{ documents }}`
     must be preserved) — note text via SiteText.
   - Link the list page from `obc_dashboard.html` (a tile next to Task 10's).
4. Rendering already goes through `EmailTemplate.render_email`/`send`, which
   read `self.subject`/`self.body` — modeltranslation makes those return the
   active language's value with fallback, so recipient-language selection
   needs no further change. Do not change send-time language selection.
5. New UI strings: seeded `portal_` SiteText keys. Document in `PORTAL.md`
   (deploy notes) that the mail migrations run as part of `migrate`.

**Tests:** non-staff → 403 on both views; staff GET lists the four names;
POST in `en` updates `subject_en`/`body_en`; POST in `de` updates the `de`
columns and leaves `en` untouched; after editing, `render_email` output
reflects the edited body.
