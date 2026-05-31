"""
Views for the document management portal.

The same screens serve both audiences; what differs is the data shown, which is
governed by the permission checks in ``portal.permissions`` (Layer B, OBC) and
``intrepid.security.user_is_initiative_manager`` (Layer A, Providers).
"""

import os
import zipfile
from io import BytesIO

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.http import FileResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST

from initiatives.models import Initiative
from intrepid.security import user_is_initiative_manager
from mail.models import EmailTemplate
from portal import bulk_import, notifications
from portal.forms import (
    AcceptInviteForm,
    BulkImportZipForm,
    DocumentEditForm,
    DocumentUploadForm,
    InitiativeUserForm,
    ProviderContactForm,
)
from portal.models import (
    NOTIFICATION_FREQUENCY_CHOICES,
    BulkImportJob,
    ContactChangeLog,
    Document,
    DocumentType,
    ProviderContact,
)
from portal.permissions import (
    has_doc_type_access,
    is_obc_staff,
    obc_area_required,
    obc_staff_required,
    readable_document_types,
    requires_doc_type,
    user_can,
)

PROVIDER_MEMBERS_GROUP = "Provider Members"
VALID_FREQUENCIES = {choice[0] for choice in NOTIFICATION_FREQUENCY_CHOICES}


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
            Q(display_name__icontains=search)
            | Q(original_filename__icontains=search)
        )
    return queryset


def _user_can_read_document(user, document):
    """Whether ``user`` may read ``document`` under either permission layer."""
    if is_obc_staff(user):
        return True
    if document.initiative in user.Initiatives.all():
        return True
    return user_can(user, "read", document.document_type)


def _stream_zip(documents, filename="documents.zip"):
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        used = set()
        for document in documents:
            arcname = document.original_filename or os.path.basename(
                document.file.name
            )
            # Avoid clobbering identically-named files within the archive.
            candidate, counter = arcname, 1
            while candidate in used:
                stem, ext = os.path.splitext(arcname)
                candidate = "{0} ({1}){2}".format(stem, counter, ext)
                counter += 1
            used.add(candidate)
            archive.write(document.file.path, arcname=candidate)
    buffer.seek(0)
    response = StreamingHttpResponse(buffer, content_type="application/zip")
    response["Content-Disposition"] = 'attachment; filename="{0}"'.format(
        filename
    )
    return response


@login_required
def index(request):
    if is_obc_staff(request.user) or has_doc_type_access(request.user):
        return redirect("portal:obc_dashboard")
    initiatives = request.user.Initiatives.all()
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
                raise PermissionDenied(
                    "You may not upload this document type."
                )
            reporting_month = form.cleaned_data["reporting_month"]
            created = 0
            for upload in form.cleaned_data["file"]:
                document = Document(
                    initiative=initiative,
                    document_type=doc_type,
                    reporting_month=reporting_month,
                    uploaded_by=request.user,
                    original_filename=upload.name,
                )
                document.file.save(upload.name, upload, save=False)
                document.save()
                created += 1
            messages.success(
                request, "Uploaded {0} document(s).".format(created)
            )
            return redirect(
                "portal:obc_initiative_detail", initiative_id=initiative.pk
            )
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
        messages.success(
            request, "Imported {0} document(s).".format(created)
        )
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
        return redirect(
            "portal:obc_initiative_detail", initiative_id=initiative_id
        )
    return render(
        request, "portal/obc_document_delete.html", {"document": document}
    )


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


@login_required
def provider_initiative_picker(request):
    initiatives = request.user.Initiatives.all()
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


@user_is_initiative_manager
def provider_initiative_documents(request, initiative_id):
    initiative = get_object_or_404(Initiative, pk=initiative_id)
    documents = _filter_documents(
        Document.objects.filter(initiative=initiative).select_related(
            "document_type"
        ),
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
        },
    )


@user_is_initiative_manager
def provider_manage_contacts(request, initiative_id):
    initiative = get_object_or_404(Initiative, pk=initiative_id)
    if request.method == "POST":
        contact_id = request.POST.get("contact_id")
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
            return redirect(
                "portal:obc_initiative_users", initiative_id=initiative.pk
            )
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
            "members": initiative.users.all().order_by(
                "last_name", "username"
            ),
        },
    )


@obc_staff_required
@require_POST
def send_invite(request, contact_id):
    """OBC action: email a contact their one-time invitation link."""
    contact = get_object_or_404(ProviderContact, pk=contact_id)
    url = request.build_absolute_uri(
        reverse(
            "portal:accept_invite",
            kwargs={"token": contact.invite_token},
        )
    )
    try:
        template = EmailTemplate.objects.get(name="provider_invite")
        template.send(to=contact.email, context={"contact": contact, "url": url})
    except EmailTemplate.DoesNotExist:
        pass
    contact.invited_at = timezone.now()
    contact.save()
    messages.success(
        request, "Invitation sent to {0}.".format(contact.email)
    )
    return redirect(
        "portal:provider_manage_contacts",
        initiative_id=contact.initiative_id,
    )


@user_is_initiative_manager
def provider_notification_prefs(request, initiative_id):
    initiative = get_object_or_404(Initiative, pk=initiative_id)
    contacts = initiative.provider_contacts.all()
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
    """Attach an accepted contact to a user and grant Provider access."""
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

    # Security: this endpoint is unauthenticated, so it must never set a
    # password on a pre-existing account. If an account already exists for the
    # invited email, the person must sign in as that account to accept.
    existing_user = User.objects.filter(email=contact.email).first()
    if existing_user is not None:
        if (
            request.user.is_authenticated
            and request.user.pk == existing_user.pk
        ):
            _link_contact_to_user(contact, existing_user)
            messages.success(request, "Invitation accepted.")
            return redirect(
                "portal:provider_initiative_documents",
                initiative_id=contact.initiative_id,
            )
        return render(
            request,
            "portal/accept_invite.html",
            {
                "existing_account": True,
                "already_accepted": False,
                "contact": contact,
            },
        )

    if request.method == "POST":
        form = AcceptInviteForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=contact.email,
                email=contact.email,
                password=form.cleaned_data["password1"],
            )
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
        {"form": form, "contact": contact, "already_accepted": False},
    )
