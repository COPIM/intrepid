"""
Permission helpers and decorators for the portal.

Two complementary layers protect every view:

* Layer A — per-Provider scoping for Provider Members, reusing the existing
  ``intrepid.security.user_is_initiative_manager`` decorator.
* Layer B — per-document-type read/write granularity for the OBC team, via the
  ``user_can`` helper and ``requires_doc_type`` decorator defined here.
"""

import functools

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from portal.models import Document, DocumentTypePermission

OBC_TEAM_GROUP = "OBC Team"


def is_obc_staff(user):
    """Return whether ``user`` is treated as full-access OBC staff.

    Superusers and Django staff have blanket access (matching the existing
    ``intrepid.security`` convention); members of the seeded "OBC Team" group
    are also OBC staff.
    """
    if not user.is_authenticated:
        return False
    return (
        user.is_superuser
        or user.is_staff
        or user.groups.filter(name=OBC_TEAM_GROUP).exists()
    )


def user_can(user, action, doc_type):
    """Return whether ``user`` may perform ``action`` on ``doc_type``.

    ``action`` is ``"read"`` or ``"write"`` (write covers upload/edit/delete).
    OBC staff may do anything; everyone else is checked against the per-type,
    per-group ``DocumentTypePermission`` rows for the groups they belong to.
    """
    if is_obc_staff(user):
        return True
    if not user.is_authenticated:
        return False
    qs = DocumentTypePermission.objects.filter(
        document_type=doc_type,
        group__in=user.groups.all(),
    )
    if action == "read":
        return qs.filter(can_read=True).exists()
    return qs.filter(can_write=True).exists()


def has_doc_type_access(user):
    """Whether ``user`` has any per-document-type read permission."""
    if not user.is_authenticated:
        return False
    return DocumentTypePermission.objects.filter(
        group__in=user.groups.all(), can_read=True
    ).exists()


def readable_document_types(user):
    """Return the document types ``user`` may read (all, for OBC staff)."""
    from portal.models import DocumentType

    if is_obc_staff(user):
        return DocumentType.objects.all()
    return DocumentType.objects.filter(
        permissions__group__in=user.groups.all(),
        permissions__can_read=True,
    ).distinct()


def obc_area_required(view):
    """Allow OBC staff or any user holding a document-type read permission."""

    @functools.wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        if is_obc_staff(request.user) or has_doc_type_access(request.user):
            return view(request, *args, **kwargs)
        raise PermissionDenied("You do not have access to the OBC area.")

    return wrapper


def obc_staff_required(view):
    """Restrict a view to full-access OBC staff only.

    Used for actions that inherently span every Provider and document type
    (bulk import, sending invitations), where a read-only per-type permission
    is not sufficient.
    """

    @functools.wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        if is_obc_staff(request.user):
            return view(request, *args, **kwargs)
        raise PermissionDenied("This action is restricted to OBC staff.")

    return wrapper


def requires_doc_type(action):
    """Decorate a document detail/edit/delete view with a Layer B check.

    The view must take a ``doc_id`` keyword argument; the document's type is
    resolved and ``user_can(request.user, action, doc_type)`` must pass.
    """

    def decorator(view):
        @functools.wraps(view)
        @login_required
        def wrapper(request, *args, **kwargs):
            document = get_object_or_404(Document, pk=kwargs.get("doc_id"))
            if not user_can(request.user, action, document.document_type):
                raise PermissionDenied(
                    "You do not have permission to {0} this document.".format(
                        action
                    )
                )
            return view(request, *args, **kwargs)

        return wrapper

    return decorator
