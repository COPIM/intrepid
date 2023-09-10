from datetime import datetime

from django.http import Http404, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect, reverse

from initiatives import models as im
from package import models as pm
from thoth import models


def get_initiative(package_or_initiative, identifier) -> im.Initiative:
    """
    Get initiative from package or initiative identifier
    :param package_or_initiative: type of identifier
    :param identifier: the identifier
    :return: initiative
    """
    initiative = None
    if package_or_initiative == "package":
        package = get_object_or_404(
            pm.Package,
            pk=identifier,
            initiative__isnull=False,
            active=True,
        )
        initiative = package.initiative
    elif package_or_initiative == "initiative":
        initiative = get_object_or_404(
            im.Initiative,
            pk=identifier,
            active=True,
        )

    return initiative


def summary_package_initiative(
    request, package_or_initiative, identifier
) -> HttpResponse:
    """
    Summary page for package or initiative
    :param request: the request
    :param package_or_initiative: type of identifier
    :param identifier: the identifier
    :return: the response
    """
    initiative = get_initiative(package_or_initiative, identifier)

    if not initiative:
        raise Http404("No package or initiative found.")

    works = models.Work.objects.filter(
        publisher__thoth_id=initiative.thoth_id
    ).order_by("-published_date")[:6]

    template = "summary/summary.html"
    context = {
        "initiative": initiative,
        "package": initiative.packages.filter(active=True).first(),
        "package_or_initiative": package_or_initiative,
        "identifier": identifier,
        "works": works,
    }
    return render(
        request,
        template,
        context,
    )


def summary_more_info(
    request, package_or_initiative, identifier
) -> HttpResponse:
    """
    Summary page for package or initiative
    :param request: the request
    :param package_or_initiative: type of identifier
    :param identifier: the identifier
    :return: the response
    """
    initiative = get_initiative(package_or_initiative, identifier)

    template = "summary/more_info.html"
    context = {
        "initiative": initiative,
        "package": initiative.packages.filter(active=True).first(),
        "package_or_initiative": package_or_initiative,
        "identifier": identifier,
    }
    return render(
        request,
        template,
        context,
    )


def summary_pricing(request, package_or_initiative, identifier) -> HttpResponse:
    """
    Summary page for package or initiative
    :param request: the request
    :param package_or_initiative: type of identifier
    :param identifier: the identifier
    :return: the response
    """
    initiative = get_initiative(package_or_initiative, identifier)

    template = "summary/pricing.html"
    context = {
        "initiative": initiative,
        "package": initiative.packages.filter(active=True).first(),
        "package_or_initiative": package_or_initiative,
        "identifier": identifier,
    }
    return render(
        request,
        template,
        context,
    )


def summary_meta_package(request, package_id) -> HttpResponse:
    """
    Summary page for meta package
    :param request: the request
    :param package_id: the package id
    :return: the response
    """
    package_type = None
    try:
        package = pm.Package.objects.get(pk=package_id, active=True)
        return redirect(
            reverse(
                "summary_package_initiative",
                kwargs={
                    "package_or_initiative": package,
                    "identifier": package.pk,
                },
            )
        )
    except pm.Package.DoesNotExist:
        try:
            package = pm.MetaPackage.objects.get(pk=package_id, active=True)
            package_type = "meta"
        except pm.MetaPackage.DoesNotExist:
            raise Http404

    thoth_ids = [
        initiative.thoth_id for initiative in package.initiative_list()
    ]
    works = (
        models.Work.objects.filter(
            publisher__thoth_id__in=thoth_ids,
        )
        .exclude(published_date="n.d.")
        .order_by("-published_date")[:6]
    )

    template = "package/info.html"
    context = {
        "package": package,
        "package_type": package_type,
        "works": works,
    }
    return render(
        request,
        template,
        context,
    )
