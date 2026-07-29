"""Seed translatable SiteText entries for the portal UI.

The portal's user-facing strings are served through the site's existing
``get_site_text`` / ``cms.SiteText`` translation system so OBC can translate
them (English + German) from the standard translation tooling. Each key is
seeded here with its English text; German is filled in later by OBC.
"""

from django.db import migrations

# key -> (english_text, help_text)
PORTAL_SITE_TEXT = {
    # Masthead / shared
    "portal_brand_name": ("Document portal", "Portal name in the masthead."),
    "portal_eyebrow": ("Open Book Collective", "Small label above the portal name."),
    "portal_mobile_note": (
        "The document portal is designed for a larger screen. Please open it "
        "on a desktop or tablet to upload, manage and download documents.",
        "Message shown on small screens.",
    ),
    "portal_mobile_continue": ("Continue anyway", "Mobile continue button."),
    # Shared labels / buttons
    "portal_filter": ("Filter", "Filter button."),
    "portal_download": ("Download", "Download link."),
    "portal_edit": ("Edit", "Edit link."),
    "portal_delete": ("Delete", "Delete link/button."),
    "portal_cancel": ("Cancel", "Cancel button."),
    "portal_save": ("Save", "Save button."),
    "portal_remove": ("Remove", "Remove link."),
    "portal_download_selected": ("Download selected", "Bulk download button."),
    "portal_all_types": ("All types", "Document-type filter, all option."),
    "portal_search_name": ("Search name", "Search field label."),
    "portal_documents_label": ("documents", "Word after a document count badge."),
    # Shared table headers
    "portal_th_document": ("Document", "Table header."),
    "portal_th_provider": ("Provider", "Table header."),
    "portal_th_type": ("Type", "Table header."),
    "portal_th_uploaded": ("Uploaded", "Table header."),
    "portal_th_name": ("Name", "Table header."),
    "portal_th_reporting_month": ("Reporting month", "Table header / field label."),
    "portal_th_actions": ("Actions", "Table header."),
    "portal_th_email": ("Email", "Table header."),
    "portal_th_job_title": ("Job title", "Table header."),
    "portal_th_notifications": ("Notifications", "Table header / nav label."),
    "portal_th_username": ("Username", "Table header."),
    "portal_th_when": ("When", "Table header."),
    "portal_th_contact": ("Contact", "Table header."),
    "portal_th_changed_by": ("Changed by", "Table header."),
    "portal_th_changes": ("Changes", "Table header."),
    "portal_th_file": ("File", "Table header."),
    "portal_th_status": ("Status", "Table header."),
    "portal_th_note": ("Note", "Table header."),
    # Shared nav links
    "portal_nav_all_providers": ("All providers", "Back link to the dashboard."),
    "portal_nav_dashboard": ("Dashboard", "Back link to the dashboard."),
    "portal_nav_documents": ("Documents", "Provider sub-nav."),
    "portal_nav_contacts": ("Contacts", "Provider sub-nav."),
    "portal_nav_back_documents": ("Back to documents", "Back link."),
    # Dashboard
    "portal_dashboard_title": ("OBC document dashboard", "Dashboard heading."),
    "portal_dashboard_intro": (
        "Upload and manage documents for each Provider, import historical "
        "archives in bulk, and review the changes Providers make to their own "
        "contact details.",
        "Dashboard introduction.",
    ),
    "portal_tile_documents_title": ("Provider documents & access", "Tile title."),
    "portal_tile_documents_desc": (
        "Open a Provider to view, upload and download their documents — and "
        "manage which users can access them.",
        "Tile description.",
    ),
    "portal_tile_bulk_title": ("Bulk import", "Tile title."),
    "portal_tile_bulk_desc": (
        "Upload a ZIP of historical documents, organised by Provider and "
        "month, and import them all at once.",
        "Tile description.",
    ),
    "portal_tile_contacts_title": ("Contact changes", "Tile title."),
    "portal_tile_contacts_desc": (
        "Review the changes Providers have made to their contact details, with "
        "a full history.",
        "Tile description.",
    ),
    "portal_providers_heading": ("Providers", "Section heading."),
    "portal_providers_hint": (
        "Select a Provider to view, upload and manage their documents.",
        "Section hint.",
    ),
    "portal_providers_empty": ("No Providers yet.", "Empty state."),
    "portal_recent_heading": ("Recent uploads", "Section heading."),
    "portal_recent_hint": (
        "The latest documents added across all Providers.", "Section hint."
    ),
    "portal_recent_empty": ("No documents uploaded yet.", "Empty state."),
    # Initiative detail
    "portal_detail_hint": (
        "Documents held for this Provider. Filter the list below, or upload "
        "new documents.",
        "Per-provider hint.",
    ),
    "portal_btn_upload": ("Upload documents", "Upload button."),
    "portal_btn_manage_users": ("Manage users", "Manage-users button."),
    "portal_documents_none_match": ("No documents match.", "Empty filtered state."),
    # Upload
    "portal_upload_title": ("Upload documents", "Upload page heading."),
    "portal_upload_for": ("Uploading for", "Prefix before the Provider name."),
    "portal_upload_multiselect": (
        "You can select several files at once.", "Upload hint."
    ),
    "portal_label_document_type": ("Document type", "Field label."),
    "portal_upload_month_help": (
        "Required for document types such as Remittance advice.", "Field help."
    ),
    "portal_label_files": ("Files", "Field label."),
    "portal_btn_upload_short": ("Upload", "Upload submit button."),
    # Bulk import
    "portal_bulk_title": ("Bulk import documents", "Bulk import heading."),
    "portal_bulk_subhint": (
        "Import a back-catalogue of documents in one go.", "Bulk import hint."
    ),
    "portal_bulk_body1": (
        "Upload a ZIP file containing one folder per reporting month, named "
        "<code>YYYY-MM</code> — for example <code>2026-04/</code>. Inside each "
        "month folder, put one file per Provider, named so the Provider's name "
        "comes last after a dash, e.g. "
        "<code>2026-04 OBC Accounts Report - Open Book Publishers.pdf</code>. "
        "The Provider is matched on its name <strong>or any alias</strong> you "
        "have added (so <code>OBP</code> resolves to Open Book Publishers).",
        "Bulk import explanation, paragraph 1 (contains HTML).",
    ),
    "portal_bulk_body2": (
        "Nothing is saved until you review the preview and confirm. Anything "
        "that can't be matched — an unknown Provider name (add the Provider, or "
        "an alias, first), a bad date, or a file that doesn't follow the naming "
        "convention — is listed for you to review, and is never imported "
        "silently.",
        "Bulk import explanation, paragraph 2.",
    ),
    # Bulk preview
    "portal_bulk_preview_title": ("Bulk import preview", "Preview heading."),
    "portal_bulk_preview_subhint": (
        "Check the mapping below before importing. Rows marked Skipped or Error "
        "will not be imported.",
        "Preview hint.",
    ),
    "portal_bulk_startover": ("Start over", "Back link on the preview."),
    "portal_bulk_confirm": (
        "Confirm and import the OK rows", "Commit button."
    ),
    "portal_bulk_already_committed": (
        "This import has already been committed.", "Committed notice."
    ),
    # Contact changes
    "portal_contact_changes_title": ("Provider contact changes", "Heading."),
    "portal_contact_changes_subhint": (
        "Whenever a Provider edits one of their contacts, the change is "
        "recorded here (and emailed to the OBC team).",
        "Contact changes hint.",
    ),
    "portal_all_providers": ("All providers", "Provider filter, all option."),
    "portal_contact_changes_empty": (
        "No contact changes recorded yet.", "Empty state."
    ),
    # Provider picker
    "portal_picker_title": ("Choose a provider", "Picker heading."),
    "portal_picker_subhint": (
        "You manage documents for more than one Provider. Choose one to "
        "continue.",
        "Picker hint.",
    ),
    "portal_picker_tile_desc": (
        "View documents, contacts and notification settings.", "Picker tile."
    ),
    "portal_picker_empty": (
        "You are not linked to any Provider yet.", "Empty state."
    ),
    # Provider documents
    "portal_provider_docs_subhint": (
        "Documents the Open Book Collective has shared with you. Download them "
        "individually, or tick several and download a ZIP.",
        "Provider documents hint.",
    ),
    "portal_provider_docs_empty": (
        "No documents available yet.", "Empty state."
    ),
    # Provider contacts
    "portal_contacts_heading": ("Contacts", "Contacts heading (Provider name follows)."),
    "portal_contacts_subhint": (
        "The people at your organisation who manage documents and "
        "notifications. Any change is recorded and sent to the OBC team.",
        "Contacts hint.",
    ),
    "portal_contacts_add_heading": ("Add a contact", "Add contact heading."),
    "portal_send_invitation": ("Send invitation", "Send invite button."),
    "portal_resend_invite": ("Re-send invite", "Re-send invite button."),
    "portal_contacts_empty": ("No contacts yet.", "Empty state."),
    "portal_contacts_softwarn": (
        "Most Providers need five contacts or fewer. Add another anyway?",
        "JavaScript warning when adding a sixth contact.",
    ),
    # Notification preferences
    "portal_notif_heading": (
        "Notification preferences", "Notifications heading (Provider name follows)."
    ),
    "portal_notif_subhint": (
        "Each contact chooses how often they hear about new documents. Everyone "
        "is independent — one person can get every document immediately while "
        "another gets a weekly digest or nothing at all.",
        "Notifications hint.",
    ),
    "portal_btn_save_prefs": ("Save preferences", "Save button."),
    "portal_notif_no_contacts": (
        "No contacts yet. Add contacts first.", "Empty state."
    ),
    # Document edit / delete
    "portal_edit_title": ("Edit document", "Edit heading."),
    "portal_delete_title": ("Delete document", "Delete heading."),
    "portal_delete_confirm_pre": (
        "Are you sure you want to delete", "Delete confirmation (name follows)."
    ),
    "portal_delete_confirm_post": (
        "? Any pending notifications for it will be cancelled.",
        "Delete confirmation, after the name.",
    ),
    # Provider access (users)
    "portal_users_heading": ("Provider access", "Users heading (Provider name follows)."),
    "portal_users_subhint_pre": (
        "These user accounts can sign in and see the Provider side of the "
        "portal for",
        "Users hint (Provider name follows).",
    ),
    "portal_users_subhint_post": (
        "— their documents, contacts and notification settings.",
        "Users hint, after the name.",
    ),
    "portal_users_current_heading": ("Current users", "Section heading."),
    "portal_users_empty": (
        "No users have access to this Provider yet.", "Empty state."
    ),
    "portal_users_add_heading": ("Add a user", "Section heading."),
    "portal_users_add_hint": (
        "Enter the email address of an existing OBC account to give them access "
        "to this Provider. To onboard someone who doesn't have an account yet, "
        "invite them from the Provider's contacts instead.",
        "Add user hint.",
    ),
    # Accept invite
    "portal_invite_title": ("Accept your invitation", "Invite heading."),
    "portal_invite_already_pre": (
        "This invitation has already been accepted. If this was you, please",
        "Already-accepted notice (a log-in link follows).",
    ),
    "portal_invite_already_post": ("instead.", "Already-accepted notice, after link."),
    "portal_invite_login": ("log in", "Log-in link text."),
    "portal_invite_existing_pre": (
        "An account already exists for this email address. Please",
        "Existing-account notice (a sign-in link follows).",
    ),
    "portal_invite_existing_post": (
        "with that account to accept this invitation — we will never reset an "
        "existing account's password from this page.",
        "Existing-account notice, after link.",
    ),
    "portal_invite_signin": ("sign in", "Sign-in link text."),
    "portal_invite_welcome": ("Welcome", "Invite welcome (Provider name may follow)."),
    "portal_invite_choose_password": (
        "Choose a password to activate your account.", "Invite instruction."
    ),
}


def seed(apps, schema_editor):
    SiteText = apps.get_model("cms", "SiteText")
    for key, (body, help_text) in PORTAL_SITE_TEXT.items():
        SiteText.objects.get_or_create(
            key=key,
            defaults={"body": body, "body_en": body, "help_text": help_text},
        )


def unseed(apps, schema_editor):
    SiteText = apps.get_model("cms", "SiteText")
    SiteText.objects.filter(key__in=PORTAL_SITE_TEXT.keys()).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0004_seed"),
        # Depend on the latest cms migration so SiteText.body_en exists.
        ("cms", "0044_add_basket_message_site_texts"),
    ]

    operations = [migrations.RunPython(seed, unseed)]
