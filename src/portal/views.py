"""
Views for the document management portal.

The same screens serve both audiences; what differs is the data shown, which is
governed by the permission checks in ``portal.permissions`` (Layer B, OBC) and
``intrepid.security.user_is_initiative_manager`` (Layer A, Providers).
"""

import os
import tempfile
import zipfile
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST

from initiatives.models import Initiative
from mail.models import EmailTemplate
from portal import bulk_import, notifications
from portal.forms import (
    AcceptInviteForm,
    BulkImportZipForm,
    DocumentEditForm,
    DocumentUploadForm,
    EmailTemplateForm,
    InitiativeAliasForm,
    InitiativeUserForm,
    InviteByEmailForm,
    ProviderContactForm,
    StaffUserForm,
)
from portal.models import (
    NOTIFICATION_FREQUENCY_CHOICES,
    BulkImportJob,
    ContactChangeLog,
    Document,
    DocumentType,
    InitiativeAlias,
    NotificationQueue,
    ProviderContact,
)
from portal.permissions import (
    OBC_TEAM_GROUP,
    can_manage_initiative,
    has_doc_type_access,
    initiative_access_required,
    initiative_manager_required,
    is_obc_staff,
    linked_contact,
    obc_area_required,
    obc_staff_required,
    readable_document_types,
    requires_doc_type,
    user_can,
)

PROVIDER_MEMBERS_GROUP = "Provider Members"
VALID_FREQUENCIES = {choice[0] for choice in NOTIFICATION_FREQUENCY_CHOICES}

logger = logging.getLogger(__name__)


def _filter_documents(queryset, params):
    """Apply the shared filter set used by both OBC and Provider lists."""
    document_type = params.get("document_type")
    if document_type:
        queryset = queryset.filter(document_type_id=document_type)

    reporting_month = params.get("reporting_month")
    if reporting_month:
        parts = reporting_month.split("-")
        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
            queryset = queryset.filter(
                reporting_month__year=int(parts[0]),
                reporting_month__month=int(parts[1]),
            )

    uploaded_after = parse_date(params.get("uploaded_after") or "")
    if uploaded_after:
        queryset = queryset.filter(uploaded_at__date__gte=uploaded_after)

    uploaded_before = parse_date(params.get("uploaded_before") or "")
    if uploaded_before:
        queryset = queryset.filter(uploaded_at__date__lte=uploaded_before)

    search = params.get("q")
    if search:
        queryset = queryset.filter(
            Q(display_name__icontains=search) | Q(original_filename__icontains=search)
        )
    return queryset


def _accessible_initiatives(user):
    """Initiatives a Provider/Contact user may reach (managed OR linked).

    A user reaches an initiative either as a manager (member of
    ``initiative.users``) or as a Contact (a ``ProviderContact`` linking them to
    it). Returned as a distinct queryset for use by the index/picker screens.
    """
    return Initiative.objects.filter(
        Q(users=user) | Q(provider_contacts__user=user)
    ).distinct()


def _user_can_read_document(user, document):
    """Whether ``user`` may read ``document`` under either permission layer."""
    if is_obc_staff(user):
        return True
    if document.initiative in user.Initiatives.all():
        return True
    if linked_contact(user, document.initiative) is not None:
        return True
    return user_can(user, "read", document.document_type)


def _stream_zip(documents, filename="documents.zip"):
    # Build the archive on disk (not in memory) and stream it back, so the
    # response is memory-bounded even for archives in the 100s-MB range.
    # Mirrors the temp-file + FileResponse + unlink idiom used by
    # package.order_management.download_order_document.
    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    try:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as archive:
            used = set()
            for document in documents:
                arcname = document.original_filename or os.path.basename(
                    document.file.name
                )
                # Avoid clobbering identically-named files in the archive.
                candidate, counter = arcname, 1
                while candidate in used:
                    stem, ext = os.path.splitext(arcname)
                    candidate = "{0} ({1}){2}".format(stem, counter, ext)
                    counter += 1
                used.add(candidate)
                archive.write(document.file.path, arcname=candidate)
        tmp.close()
        response = FileResponse(open(tmp.name, "rb"), content_type="application/zip")
        response["Content-Disposition"] = 'attachment; filename="{0}"'.format(filename)
        response["Content-Length"] = os.path.getsize(tmp.name)
        return response
    finally:
        # The open handle held by FileResponse keeps the file readable while
        # it streams; unlinking now means it is cleaned up afterwards.
        os.unlink(tmp.name)


@login_required
def index(request):
    if is_obc_staff(request.user) or has_doc_type_access(request.user):
        return redirect("portal:obc_dashboard")
    initiatives = _accessible_initiatives(request.user)
    if initiatives.count() == 1:
        return redirect(
            "portal:provider_initiative_documents",
            initiative_id=initiatives.first().pk,
        )
    return redirect("portal:provider_initiative_picker")


@obc_area_required
def obc_dashboard(request):
    types = readable_document_types(request.user)
    recent_documents = (
        Document.objects.filter(document_type__in=types)
        .select_related("initiative", "document_type")
        .order_by("-uploaded_at")[:10]
    )
    initiatives = Initiative.objects.annotate(
        document_count=Count(
            "documents",
            filter=Q(documents__document_type__in=types),
        )
    ).order_by("name")
    return render(
        request,
        "portal/obc_dashboard.html",
        {
            "initiatives": initiatives,
            "recent_documents": recent_documents,
        },
    )


@obc_area_required
def obc_initiative_detail(request, initiative_id):
    initiative = get_object_or_404(Initiative, pk=initiative_id)
    types = readable_document_types(request.user)
    documents = _filter_documents(
        Document.objects.filter(
            initiative=initiative, document_type__in=types
        ).select_related("document_type"),
        request.GET,
    )
    return render(
        request,
        "portal/obc_initiative_detail.html",
        {
            "initiative": initiative,
            "documents": documents,
            "document_types": types,
            "filters": request.GET,
            "is_obc": True,
        },
    )


@obc_area_required
def obc_upload(request, initiative_id):
    initiative = get_object_or_404(Initiative, pk=initiative_id)
    if request.method == "POST":
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            doc_type = form.cleaned_data["document_type"]
            if not user_can(request.user, "write", doc_type):
                raise PermissionDenied("You may not upload this document type.")
            reporting_month = form.cleaned_data["reporting_month"]
            send_notification = form.cleaned_data["send_notification"]
            created = 0
            for upload in form.cleaned_data["file"]:
                document = Document(
                    initiative=initiative,
                    document_type=doc_type,
                    reporting_month=reporting_month,
                    uploaded_by=request.user,
                    original_filename=upload.name,
                )
                if not send_notification:
                    document._suppress_notifications = True
                document.file.save(upload.name, upload, save=False)
                document.save()
                created += 1
            messages.success(request, "Uploaded {0} document(s).".format(created))
            return redirect("portal:obc_initiative_detail", initiative_id=initiative.pk)
    else:
        form = DocumentUploadForm()
    return render(
        request,
        "portal/obc_upload.html",
        {"form": form, "initiative": initiative},
    )


@obc_staff_required
def obc_bulk_import(request):
    if request.method == "POST":
        form = BulkImportZipForm(request.POST, request.FILES)
        if form.is_valid():
            upload = form.cleaned_data["zip_file"]
            job = bulk_import.stage_job(
                upload,
                user=request.user,
                notify_on_commit=form.cleaned_data["notify_on_commit"],
                original_filename=upload.name,
            )
            return render(
                request,
                "portal/obc_bulk_preview.html",
                {"job": job, "rows": job.rows.all()},
            )
    else:
        form = BulkImportZipForm()
    return render(request, "portal/obc_bulk_import.html", {"form": form})


@obc_staff_required
def obc_bulk_commit(request, job_id):
    job = get_object_or_404(BulkImportJob, pk=job_id)
    if request.method == "POST":
        created = bulk_import.commit_job(job)
        messages.success(request, "Imported {0} document(s).".format(created))
        return redirect("portal:obc_dashboard")
    return render(
        request,
        "portal/obc_bulk_preview.html",
        {"job": job, "rows": job.rows.all()},
    )


@requires_doc_type("write")
def obc_document_edit(request, doc_id):
    document = get_object_or_404(Document, pk=doc_id)
    if request.method == "POST":
        form = DocumentEditForm(request.POST, instance=document)
        if form.is_valid():
            form.save()
            messages.success(request, "Document updated.")
            return redirect(
                "portal:obc_initiative_detail",
                initiative_id=document.initiative_id,
            )
    else:
        form = DocumentEditForm(instance=document)
    return render(
        request,
        "portal/obc_document_edit.html",
        {"form": form, "document": document},
    )


@requires_doc_type("write")
def obc_document_delete(request, doc_id):
    document = get_object_or_404(Document, pk=doc_id)
    initiative_id = document.initiative_id
    if request.method == "POST":
        notifications.cancel_for_document(document)
        document.delete()
        messages.success(request, "Document deleted.")
        return redirect("portal:obc_initiative_detail", initiative_id=initiative_id)
    return render(request, "portal/obc_document_delete.html", {"document": document})


@obc_area_required
def obc_contact_changes(request):
    logs = ContactChangeLog.objects.select_related(
        "initiative", "provider_contact", "actor"
    )
    initiative_id = request.GET.get("initiative")
    if initiative_id:
        logs = logs.filter(initiative_id=initiative_id)
    return render(
        request,
        "portal/obc_contact_changes.html",
        {"logs": logs, "initiatives": Initiative.objects.all()},
    )


@obc_staff_required
def obc_emails(request):
    """List every notification email — pending, sent and cancelled.

    OBC staff can cancel a still-pending email (keeping its document) or
    re-send one that has already gone out. Rows are decorated with numeric
    sort keys (status group, then the relevant timestamp) so the DataTable can
    default to "unsent first, newest-first" deterministically.
    """
    rows = list(
        NotificationQueue.objects.select_related(
            "recipient",
            "recipient__user",
            "document",
            "document__initiative",
        )
    )
    for row in rows:
        if row.cancelled_at is not None:
            row.status_order = 2
            row.status_key = "cancelled"
            row.status_date = row.cancelled_at
        elif row.sent_at is not None:
            row.status_order = 1
            row.status_key = "sent"
            row.status_date = row.sent_at
        else:
            row.status_order = 0
            row.status_key = "pending"
            row.status_date = row.eligible_at
        # Epoch seconds give the DataTable a stable numeric date sort key.
        row.status_date_epoch = int(row.status_date.timestamp())
    # Match the DataTable default (status ascending, then date descending) so a
    # no-JS page and the initial JS render agree.
    rows.sort(key=lambda r: (r.status_order, -r.status_date_epoch))
    return render(request, "portal/obc_emails.html", {"rows": rows})


@obc_staff_required
@require_POST
def obc_email_cancel(request, queue_id):
    """Cancel a still-pending notification row (the document is untouched)."""
    row = get_object_or_404(NotificationQueue, pk=queue_id)
    if row.sent_at is None and row.cancelled_at is None:
        row.cancelled_at = timezone.now()
        row.save(update_fields=["cancelled_at"])
        messages.success(request, "Email cancelled.")
    else:
        messages.error(
            request, "Only a pending email can be cancelled."
        )
    return redirect("portal:obc_emails")


@obc_staff_required
@require_POST
def obc_email_resend(request, queue_id):
    """Re-send an already-sent notification email immediately."""
    row = get_object_or_404(NotificationQueue, pk=queue_id)
    if row.sent_at is not None:
        try:
            notifications.resend_row(row)
        except EmailTemplate.DoesNotExist:
            messages.error(
                request, "The email template is missing; nothing was sent."
            )
        else:
            row.sent_at = timezone.now()
            row.save(update_fields=["sent_at"])
            messages.success(request, "Email re-sent.")
    else:
        messages.error(
            request, "Only an email that has already been sent can be re-sent."
        )
    return redirect("portal:obc_emails")


PORTAL_EMAIL_TEMPLATE_NAMES = [
    "document_notification_immediate",
    "document_notification_digest",
    "contact_change_notification",
    "provider_invite",
]


@obc_staff_required
def obc_email_templates(request):
    """List the four portal notification templates with a per-language edit link.

    Each language in ``settings.LANGUAGES`` gets its own edit link because the
    subject/body are translated columns (``django-modeltranslation``).
    """
    templates = EmailTemplate.objects.filter(
        name__in=PORTAL_EMAIL_TEMPLATE_NAMES
    ).order_by("name")
    languages = [
        {"code": code, "name": name} for code, name in settings.LANGUAGES
    ]
    return render(
        request,
        "portal/obc_email_templates.html",
        {"templates": templates, "languages": languages},
    )


@obc_staff_required
def obc_email_template_edit(request, template_id, lang_code):
    """Edit one language's subject/body for a portal notification template.

    The POST saves inside ``translation.override(lang_code)`` so
    modeltranslation writes the columns for that language only (the same trick
    as ``cms.views.edit_site_text``). An unknown ``lang_code`` is a 404.
    """
    valid_codes = {code for code, _ in settings.LANGUAGES}
    if lang_code not in valid_codes:
        raise Http404("Unknown language.")

    template = get_object_or_404(
        EmailTemplate,
        pk=template_id,
        name__in=PORTAL_EMAIL_TEMPLATE_NAMES,
    )
    language_name = dict(settings.LANGUAGES).get(lang_code, lang_code)

    with translation.override(lang_code):
        if request.method == "POST":
            form = EmailTemplateForm(request.POST)
            if form.is_valid():
                template.subject = form.cleaned_data["subject"]
                template.body = form.cleaned_data["body"]
                template.save()
                messages.success(request, "Email template saved.")
                return redirect("portal:obc_email_templates")
        else:
            form = EmailTemplateForm(
                initial={
                    "subject": template.subject,
                    "body": template.body,
                }
            )

    return render(
        request,
        "portal/obc_email_template_edit.html",
        {
            "form": form,
            "template": template,
            "lang_code": lang_code,
            "language_name": language_name,
        },
    )


@login_required
def provider_initiative_picker(request):
    initiatives = _accessible_initiatives(request.user)
    if initiatives.count() == 1:
        return redirect(
            "portal:provider_initiative_documents",
            initiative_id=initiatives.first().pk,
        )
    return render(
        request,
        "portal/provider_initiative_picker.html",
        {"initiatives": initiatives},
    )


@initiative_access_required
def provider_initiative_documents(request, initiative_id):
    initiative = get_object_or_404(Initiative, pk=initiative_id)
    documents = _filter_documents(
        Document.objects.filter(initiative=initiative).select_related("document_type"),
        request.GET,
    )
    return render(
        request,
        "portal/provider_initiative_documents.html",
        {
            "initiative": initiative,
            "documents": documents,
            "document_types": DocumentType.objects.all(),
            "filters": request.GET,
            "is_obc": is_obc_staff(request.user),
        },
    )


@initiative_access_required
def provider_manage_contacts(request, initiative_id):
    initiative = get_object_or_404(Initiative, pk=initiative_id)
    can_manage = can_manage_initiative(request.user, initiative)
    own_contact = linked_contact(request.user, initiative)
    if request.method == "POST":
        contact_id = request.POST.get("contact_id")
        if not can_manage:
            # A Contact-tier user may only edit their own linked contact row;
            # creating a new contact (no contact_id) is manager-only.
            if not contact_id or not own_contact or str(own_contact.pk) != str(
                contact_id
            ):
                raise PermissionDenied(
                    "You may not manage contacts for this initiative."
                )
        if contact_id:
            instance = get_object_or_404(
                ProviderContact, pk=contact_id, initiative=initiative
            )
            form = ProviderContactForm(request.POST, instance=instance)
        else:
            form = ProviderContactForm(request.POST)
        if form.is_valid():
            contact = form.save(commit=False)
            contact.initiative = initiative
            if not contact_id:
                # Position is auto-numbered for new contacts (next free slot).
                last = initiative.provider_contacts.order_by("-position").first()
                contact.position = (last.position + 1) if last else 1
            contact._actor = request.user
            contact.save()
            messages.success(request, "Contact saved.")
            return redirect(
                "portal:provider_manage_contacts", initiative_id=initiative.pk
            )
    else:
        form = ProviderContactForm()
    return render(
        request,
        "portal/provider_contacts.html",
        {
            "initiative": initiative,
            "contacts": initiative.provider_contacts.all(),
            "form": form,
            "is_obc": is_obc_staff(request.user),
            "can_manage": can_manage,
            "own_contact_id": own_contact.pk if own_contact else None,
        },
    )


@obc_staff_required
def obc_manage_initiative_users(request, initiative_id):
    """OBC action: control which user accounts can see a Provider's portal."""
    initiative = get_object_or_404(Initiative, pk=initiative_id)
    form = InitiativeUserForm()
    if request.method == "POST":
        if request.POST.get("remove_user"):
            user = get_object_or_404(User, pk=request.POST["remove_user"])
            initiative.users.remove(user)
            messages.success(
                request,
                "Removed {0} from {1}.".format(
                    user.email or user.username, initiative.name
                ),
            )
            return redirect("portal:obc_initiative_users", initiative_id=initiative.pk)
        form = InitiativeUserForm(request.POST)
        if form.is_valid():
            initiative.users.add(form.user)
            messages.success(
                request,
                "Added {0} to {1}.".format(
                    form.user.email or form.user.username, initiative.name
                ),
            )
            return redirect(
                "portal:obc_initiative_users", initiative_id=initiative.pk
            )
    return render(
        request,
        "portal/obc_initiative_users.html",
        {
            "initiative": initiative,
            "form": form,
            "invite_form": InviteByEmailForm(),
            "members": initiative.users.all().order_by("last_name", "username"),
            "is_obc": True,
        },
    )


@obc_staff_required
def obc_manage_aliases(request, initiative_id):
    """OBC action: manage a Provider's alternative names (aliases).

    Aliases let bulk import match a Provider by alternate names. They are an
    OBC-only concern, surfaced as a dedicated tab in the Provider sub-nav.
    """
    initiative = get_object_or_404(Initiative, pk=initiative_id)
    alias_form = InitiativeAliasForm()
    if request.method == "POST":
        if request.POST.get("remove_alias"):
            InitiativeAlias.objects.filter(
                pk=request.POST["remove_alias"], initiative=initiative
            ).delete()
            messages.success(request, "Alias removed.")
            return redirect(
                "portal:obc_initiative_aliases", initiative_id=initiative.pk
            )
        alias_form = InitiativeAliasForm(request.POST)
        if alias_form.is_valid():
            InitiativeAlias.objects.get_or_create(
                initiative=initiative,
                alias=alias_form.cleaned_data["alias"].strip(),
            )
            messages.success(
                request,
                "Added alias '{0}' for {1}.".format(
                    alias_form.cleaned_data["alias"].strip(),
                    initiative.name,
                ),
            )
            return redirect(
                "portal:obc_initiative_aliases", initiative_id=initiative.pk
            )
    return render(
        request,
        "portal/obc_aliases.html",
        {
            "initiative": initiative,
            "alias_form": alias_form,
            "aliases": initiative.aliases.all(),
            "is_obc": True,
        },
    )


@obc_staff_required
@require_POST
def send_invite(request, contact_id):
    """OBC action: (re-)send a contact their one-time invitation link."""
    contact = get_object_or_404(ProviderContact, pk=contact_id)
    # Don't (re-)invite a contact who already has a working account: either
    # they have accepted, or their linked user can already sign in.
    already_active = contact.accepted_at is not None or (
        contact.user is not None and contact.user.has_usable_password()
    )
    if already_active:
        messages.error(
            request,
            "{0} already has an account and cannot be re-invited.".format(
                contact.email
            ),
        )
    else:
        _send_invitation(request, contact)
        messages.success(
            request, "Invitation sent to {0}.".format(contact.email)
        )
    return redirect(
        "portal:provider_manage_contacts",
        initiative_id=contact.initiative_id,
    )


@initiative_manager_required
@require_POST
def delete_contact(request, initiative_id, contact_id):
    """Delete a notifications contact.

    Anyone who manages the Provider may remove a contact, except their own
    linked contact (removing it would be self-defeating). This only affects
    notifications; portal login access is managed separately on Manage Users.
    """
    initiative = get_object_or_404(Initiative, pk=initiative_id)
    contact = get_object_or_404(
        ProviderContact, pk=contact_id, initiative=initiative
    )
    if contact.user_id == request.user.id:
        messages.error(request, "You cannot delete your own contact.")
    else:
        contact.delete()
        messages.success(request, "Contact removed.")
    return redirect(
        "portal:provider_manage_contacts", initiative_id=initiative.pk
    )


def _send_invitation(request, contact):
    """Email a contact their one-time invitation link and record the time."""
    url = request.build_absolute_uri(
        reverse("portal:accept_invite", kwargs={"token": contact.invite_token})
    )
    try:
        template = EmailTemplate.objects.get(name="provider_invite")
        template.send(to=contact.email, context={"contact": contact, "url": url})
    except EmailTemplate.DoesNotExist:
        logger.error("Missing provider_invite email template.")
    contact.invited_at = timezone.now()
    contact.save()


@obc_staff_required
@require_POST
def invite_by_email(request, initiative_id):
    """Invite someone by email alone (grants portal login — creates a User).

    Creates a contact (with no details yet) and, unless an account already
    exists for that email, a detail-less user account, then sends the
    invitation. The invitee fills in their name and password when they land.
    """
    initiative = get_object_or_404(Initiative, pk=initiative_id)
    form = InviteByEmailForm(request.POST)
    if form.is_valid():
        email = form.cleaned_data["email"]
        last = initiative.provider_contacts.order_by("-position").first()
        contact = ProviderContact.objects.create(
            initiative=initiative,
            email=email,
            first_name="",
            last_name="",
            position=(last.position + 1) if last else 1,
            # This flow grants portal login/managership, so acceptance should
            # add the user to initiative.users (Provider-manager tier).
            is_login_invite=True,
        )
        existing = (
            User.objects.filter(email__iexact=email).first()
            or User.objects.filter(username__iexact=email).first()
        )
        if existing is None:
            user = User.objects.create_user(username=email, email=email)
            user.set_unusable_password()
            user.save()
            contact.user = user
            contact.save()
        _send_invitation(request, contact)
        messages.success(request, "Invitation sent to {0}.".format(email))
    else:
        messages.error(request, "Please enter a valid email address.")
    return redirect("portal:obc_initiative_users", initiative_id=initiative.pk)


@initiative_access_required
def provider_notification_prefs(request, initiative_id):
    initiative = get_object_or_404(Initiative, pk=initiative_id)
    contacts = initiative.provider_contacts.all()
    if not can_manage_initiative(request.user, initiative):
        # A Contact-tier user sees and edits only their own preference row.
        own_contact = linked_contact(request.user, initiative)
        contacts = contacts.filter(pk=own_contact.pk) if own_contact else (
            contacts.none()
        )
    if request.method == "POST":
        for contact in contacts:
            frequency = request.POST.get("frequency_{0}".format(contact.pk))
            if frequency in VALID_FREQUENCIES:
                contact.notification_frequency = frequency
                contact._actor = request.user
                contact.save()
        messages.success(request, "Notification preferences updated.")
        return redirect(
            "portal:provider_notification_prefs", initiative_id=initiative.pk
        )
    return render(
        request,
        "portal/provider_notification_prefs.html",
        {
            "initiative": initiative,
            "contacts": contacts,
            "choices": NOTIFICATION_FREQUENCY_CHOICES,
            "is_obc": is_obc_staff(request.user),
        },
    )


@login_required
def download_document(request, doc_id):
    document = get_object_or_404(Document, pk=doc_id)
    if not _user_can_read_document(request.user, document):
        raise PermissionDenied("You may not access this document.")
    response = FileResponse(open(document.file.path, "rb"))
    response["Content-Disposition"] = 'attachment; filename="{0}"'.format(
        document.original_filename or os.path.basename(document.file.name)
    )
    response["Content-Length"] = document.file.size
    return response


@login_required
@require_POST
def bulk_download(request):
    ids = request.POST.getlist("document_ids")
    documents = [
        document
        for document in Document.objects.filter(pk__in=ids).select_related(
            "initiative", "document_type"
        )
        if _user_can_read_document(request.user, document)
    ]
    return _stream_zip(documents)


def _link_contact_to_user(
    contact, user, first_name=None, last_name=None, job_title=None
):
    """Attach an accepted contact to a user and grant access.

    Only a login invite (created via the OBC Manage-Users flow) confers
    Provider-manager tier by adding the user to ``initiative.users``. A
    Contacts-pane invitee is linked to the contact and placed in the "Provider
    Members" auth group (so template/permission checks resolve) but is NOT made
    an initiative manager — they get Contact-tier access only.
    """
    if contact.is_login_invite:
        contact.initiative.users.add(user)
    group, _ = Group.objects.get_or_create(name=PROVIDER_MEMBERS_GROUP)
    user.groups.add(group)
    contact.user = user
    if first_name:
        contact.first_name = first_name
    if last_name:
        contact.last_name = last_name
    if job_title:
        contact.job_title = job_title
    contact.accepted_at = timezone.now()
    contact._actor = user
    contact.save()


def accept_invite(request, token):
    contact = get_object_or_404(ProviderContact, invite_token=token)
    if contact.accepted_at:
        return render(
            request,
            "portal/accept_invite.html",
            {"already_accepted": True, "contact": contact},
        )

    existing_user = (
        User.objects.filter(email__iexact=contact.email).first()
        or User.objects.filter(username__iexact=contact.email).first()
    )
    # A detail-less invite account (created by invite-by-email) has no usable
    # password yet, so the invitee may set one. Any OTHER existing account is a
    # real account whose password must never be reset from this endpoint.
    is_invite_account = (
        contact.user_id is not None and not contact.user.has_usable_password()
    )

    if existing_user is not None and not is_invite_account:
        if request.user.is_authenticated and request.user.pk == existing_user.pk:
            # Logged in as the matching account. Require an explicit POST so an
            # email-scanner that GETs the link cannot auto-consume the invite.
            if request.method == "POST":
                _link_contact_to_user(contact, existing_user)
                messages.success(request, "Invitation accepted.")
                return redirect(
                    "portal:provider_initiative_documents",
                    initiative_id=contact.initiative_id,
                )
            return render(
                request,
                "portal/accept_invite.html",
                {"confirm_only": True, "contact": contact},
            )
        return render(
            request,
            "portal/accept_invite.html",
            {"existing_account": True, "contact": contact},
        )

    # New signup or detail-less invite account: collect a profile + password.
    # GET only ever renders the form; the account is created/activated on POST,
    # so an auto-clicked link never consumes the invitation.
    if request.method == "POST":
        form = AcceptInviteForm(request.POST)
        if form.is_valid():
            if is_invite_account:
                user = contact.user
            else:
                user = User.objects.create_user(
                    username=contact.email, email=contact.email
                )
            user.set_password(form.cleaned_data["password1"])
            user.first_name = form.cleaned_data["first_name"]
            user.last_name = form.cleaned_data["last_name"]
            user.save()
            _link_contact_to_user(
                contact,
                user,
                first_name=form.cleaned_data["first_name"],
                last_name=form.cleaned_data["last_name"],
                job_title=form.cleaned_data["job_title"],
            )
            login(
                request,
                user,
                backend="django.contrib.auth.backends.ModelBackend",
            )
            return redirect(
                "portal:provider_initiative_documents",
                initiative_id=contact.initiative_id,
            )
    else:
        form = AcceptInviteForm(
            initial={
                "first_name": contact.first_name,
                "last_name": contact.last_name,
                "job_title": contact.job_title,
            }
        )
    return render(
        request,
        "portal/accept_invite.html",
        {"form": form, "contact": contact},
    )


@obc_staff_required
def obc_manage_staff(request):
    """OBC action: control which user accounts can access the OBC backend."""
    obc_group, _ = Group.objects.get_or_create(name=OBC_TEAM_GROUP)
    form = StaffUserForm()
    if request.method == "POST":
        if request.POST.get("remove_user"):
            user = get_object_or_404(User, pk=request.POST["remove_user"])
            if user == request.user:
                messages.warning(
                    request,
                    "You cannot remove your own staff access.",
                )
            elif user.is_superuser:
                messages.warning(
                    request,
                    "You cannot remove staff access from a superuser.",
                )
            else:
                user.is_staff = False
                user.save()
                user.groups.remove(obc_group)
                messages.success(
                    request,
                    "Removed staff access from {0}.".format(
                        user.email or user.username
                    ),
                )
            return redirect("portal:obc_manage_staff")
        form = StaffUserForm(request.POST)
        if form.is_valid():
            form.user.is_staff = True
            form.user.save()
            form.user.groups.add(obc_group)
            messages.success(
                request,
                "Made {0} a member of staff.".format(
                    form.user.email or form.user.username
                ),
            )
            return redirect("portal:obc_manage_staff")
    return render(
        request,
        "portal/obc_manage_staff.html",
        {
            "form": form,
            "members": User.objects.filter(is_staff=True).order_by(
                "last_name", "username"
            ),
        },
    )
