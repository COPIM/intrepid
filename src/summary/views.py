from datetime import datetime

from django.http import Http404, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect, reverse

from initiatives import models as im
from package import models as pm, utils as pu
from thoth import models
from cms import models as cms_models


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

    works = (
        models.Work.objects.filter(publisher__thoth_id=initiative.thoth_id)
        .exclude(published_date="n.d.")
        .order_by("-published_date")
    )

    work_list = []
    to_shunt = []

    for work in works:
        if work.published_date == "n.d.":
            to_shunt.append(work)
        elif (
            datetime.strptime(work.published_date, "%Y-%m-%d") > datetime.now()
        ):
            to_shunt.append(work)
        work_list.append(work)

    # push all n.d. results to the back of the list
    for work_to_shunt in to_shunt:
        work_list.remove(work_to_shunt)
        # work_list.append(work_to_shunt)

    pages = cms_models.PageUpdate.objects.filter(
        is_update=False,
        initiative=initiative,
    ).order_by("sequence")

    package = initiative.packages.filter(active=True).first()
    request.session.get('country')
    if request.session.get('country', None):
        pu.add_pre_calc_to_objects(
            request.session.get('country'),
            [package],
        )

    template = "summary/summary.html"
    context = {
        "initiative": initiative,
        "package": package,
        "package_or_initiative": package_or_initiative,
        "identifier": identifier,
        "works": work_list[:6],
        "additional_nav": pages,
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
    pages = cms_models.PageUpdate.objects.filter(
        is_update=False,
        initiative=initiative,
    ).order_by("sequence")

    template = "summary/more_info.html"
    context = {
        "initiative": initiative,
        "package": initiative.packages.filter(active=True).first(),
        "package_or_initiative": package_or_initiative,
        "identifier": identifier,
        "additional_nav": pages,
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
    pages = cms_models.PageUpdate.objects.filter(
        is_update=False,
        initiative=initiative,
    ).order_by("sequence")

    template = "summary/pricing.html"
    context = {
        "initiative": initiative,
        "package": initiative.packages.filter(active=True).first(),
        "package_or_initiative": package_or_initiative,
        "identifier": identifier,
        "additional_nav": pages,
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
                    "package_or_initiative": "package",
                    "identifier": package.pk,
                },
            )
        )
    except pm.Package.DoesNotExist:
        try:
            package = pm.MetaPackage.objects.get(pk=package_id, active=True)
            package_type = "meta"
            if request.session.get('country', None):
                pu.add_pre_calc_to_meta_objects(
                    request.session.get('country'),
                    [package],
                )
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
