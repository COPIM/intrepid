from django.contrib.auth.decorators import login_required
from django.db.models.functions import Lower
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from fluid_permissions import decorators

from cms import models as cms_models
from initiatives import forms
from initiatives import models
from intrepid.security import user_is_initiative_manager
from package import models as pm


@decorators.user_in_authorised_group
def initiative_list(request) -> HttpResponse:
    """
    List all initiatives
    :param request: the request
    :return: an HTTP response
    """
    initiatives = models.Initiative.objects.all()
    template = "initiatives/list.html"
    context = {
        "initiatives": initiatives,
    }
    return render(
        request,
        template,
        context,
    )


def public_initiative_list(request) -> HttpResponse:
    """
    List all active public initiatives
    :param request: the request
    :return: an HTTP response
    """
    initiatives = models.Initiative.objects.filter(active=True).order_by(
        Lower("name")
    )

    template = "base/frontend/initiatives.html"
    context = {
        "initiatives": initiatives,
    }
    return render(
        request,
        template,
        context,
    )


def public_initiative(request, initiative_id, page_id=None) -> HttpResponse:
    """
    Show a public initiative
    :param request: the request
    :param initiative_id: the initiative id
    :param page_id: the page id
    :return: an HTTP response
    """
    initiative = get_object_or_404(
        models.Initiative, pk=initiative_id, active=True
    )
    page = None

    pages = cms_models.PageUpdate.objects.filter(
        is_update=False,
        initiative=initiative,
    ).order_by("sequence")

    if not page_id and len(pages) > 0:
        page = pages[0]
    elif page_id:
        page = get_object_or_404(
            cms_models.PageUpdate,
            pk=page_id,
            initiative=initiative_id,
        )

    updates = cms_models.PageUpdate.objects.filter(
        initiative=initiative, target_institution=None, is_update=True
    ).order_by("-created")

    featured_books = cms_models.FeaturedBook.objects.filter(
        initiative=initiative
    )

    template = "base/frontend/initiative.html"
    context = {
        "initiative": initiative,
        "pages": pages,
        "current_page": page,
        "news_items": updates,
        "additional_nav": pages,
        "featured_books": featured_books,
    }
    return render(
        request,
        template,
        context,
    )


@user_is_initiative_manager
def initiative_detail(request, initiative_id) -> HttpResponse:
    """
    Show initiative details
    :param request: the request
    :param initiative_id: the initiative id
    :return: an HTTP response
    """
    initiative = get_object_or_404(
        models.Initiative,
        pk=initiative_id,
    )

    template = "initiatives/detail.html"
    context = {
        "initiative": initiative,
    }
    return render(
        request,
        template,
        context,
    )


@user_is_initiative_manager
def initiative_edit_or_create(request, initiative_id=None) -> HttpResponse:
    """
    Edit or create an initiative
    :param request: the request
    :param initiative_id: the initiative id
    :return: an HTTP response
    """
    initiative = (
        get_object_or_404(
            models.Initiative,
            pk=initiative_id,
        )
        if initiative_id
        else None
    )

    if request.POST:
        form = forms.InitiativeForm(
            request.POST, request.FILES, instance=initiative, request=request
        )

        if form.is_valid():
            form.save()

        return redirect("initiative_user_initiatives")
    else:
        form = forms.InitiativeForm(instance=initiative, request=request)

    template = "initiatives/edit_initiative.html"
    context = {
        "initiative": initiative,
        "form": form,
    }
    return render(
        request,
        template,
        context,
    )


@decorators.user_in_authorised_group
def initiative_delete(request, initiative_id) -> None:
    """
    Delete an initiative: this function is not used as it is DANGEROUS
    :param request: the request. Unused.
    :param initiative_id: the initiative id. Unused.
    :return: None
    """
    # we don't have any view to delete an initiative
    # because this is such a major operation, we're leaving it in the admin
    ...


@login_required
def user_initiatives(request) -> HttpResponse:
    """
    List all initiatives for the current user
    :param request: the request
    :return: an HTTP response
    """
    if request.user.is_staff:
        users_initiatives = models.Initiative.objects.all().prefetch_related("users").prefetch_related("users__profile")
    else:
        users_initiatives = models.Initiative.objects.filter(
            users=request.user,
        ).prefetch_related("users").prefetch_related("users__profile")
    template = "initiatives/user_initiatives.html"
    context = {
        "users_initiatives": users_initiatives,
    }
    return render(
        request,
        template,
        context,
    )


@user_is_initiative_manager
def initiative_packages(request, initiative) -> HttpResponse:
    """
    List all packages for an initiative
    :param request: the request
    :param initiative: the initiative
    :return: an HTTP response
    """
    packages = pm.Package.objects.filter(initiative=initiative)
    template = "initiatives/initiative_packages.html"
    context = {
        "packages": packages,
        "initiative": initiative,
    }
    return render(
        request,
        template,
        context,
    )
