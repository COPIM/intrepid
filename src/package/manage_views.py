from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render, redirect, reverse, get_object_or_404
from fluid_permissions.decorators import user_in_authorised_group

from intrepid.security import user_is_initiative_manager
from package import models, forms


@user_is_initiative_manager
def start_package(request, initiative) -> HttpResponse:
    """
    Allows creation of a package.
    :param request: the request object
    :param initiative: the initiative object
    :return: the response object
    """
    banding_types = models.BandingType.objects.filter(active=True)
    template = "package/manage/start_package.html"
    context = {
        "banding_types": banding_types,
        "initiative": initiative,
    }
    return render(
        request,
        template,
        context,
    )


@user_is_initiative_manager
def create_package(request, initiative, banding_type_id) -> HttpResponse:
    """
    Allows creation of a package.
    :param request: the request object
    :param initiative: the initiative object
    :param banding_type_id: the banding type id
    :return: the response object
    """
    banding_type = get_object_or_404(
        models.BandingType,
        pk=banding_type_id,
    )
    form = forms.ManagePackageForm(
        current_initiative=initiative,
        banding_type=banding_type,
        user=request.user,
    )
    if request.POST:
        form = forms.ManagePackageForm(
            request.POST,
            request.FILES,
            current_initiative=initiative,
            banding_type=banding_type,
            user=request.user,
        )
        if form.is_valid():
            package, bte, btce = form.save()
            package.save_price_data(form)
            messages.add_message(
                request,
                messages.SUCCESS,
                "Package Information Saved.",
            )
            return redirect(
                reverse(
                    "manage_package_banding_currencies_prices",
                    kwargs={
                        "initiative_id": initiative.pk,
                        "package_id": package.pk,
                        "banding_id": bte.pk,
                        "currency_id": btce.pk,
                    },
                )
            )
    template = "package/manage/create_package.html"
    context = {
        "initiative": initiative,
        "form": form,
    }
    return render(request, template, context)


@user_is_initiative_manager
def manage_package(request, initiative, package_id) -> HttpResponse:
    """
    Allows creation or editing of a package.
    :param request: the request object
    :param initiative: the initiative object
    :param package_id: the package id
    :return: the response object
    """
    package = get_object_or_404(
        models.Package,
        pk=package_id,
        initiative=initiative,
    )
    form = forms.ManagePackageForm(
        instance=package,
        current_initiative=initiative,
        banding_type=package.banding_type,
        user=request.user,
    )
    if request.POST:
        form = forms.ManagePackageForm(
            request.POST,
            request.FILES,
            instance=package,
            current_initiative=initiative,
            banding_type=package.banding_type,
            user=request.user,
        )
        if form.is_valid():
            form.save()
            form.save_m2m()
            messages.add_message(
                request,
                messages.SUCCESS,
                "Package Information Saved.",
            )
            return redirect(
                reverse(
                    "initiative_packages",
                    kwargs={"initiative": initiative.pk},
                )
            )

    template = "package/manage/package.html"
    context = {
        "package": package,
        "initiative": initiative,
        "form": form,
    }
    return render(request, template, context)


@user_in_authorised_group
def list_meta_packages(request) -> HttpResponse:
    """
    List all meta packages
    :param request: the request object
    :return: the response object
    """
    meta_packages = models.MetaPackage.objects.all()

    if request.POST and "delete" in request.POST:
        id_to_delete = request.POST.get("delete")
        meta_package = get_object_or_404(
            models.MetaPackage,
            pk=id_to_delete,
        )
        meta_package.delete()
        messages.add_message(
            request,
            messages.ERROR,
            "Meta Package deleted.",
        )
        return redirect(
            reverse(
                "list_meta_packages",
            )
        )

    template = "package/staff/list_meta_packages.html"
    context = {
        "meta_packages": meta_packages,
    }
    return render(
        request,
        template,
        context,
    )


@user_in_authorised_group
def manage_meta_package(request, package_id=None) -> HttpResponse:
    """
    Manage a meta package
    :param request: the request object
    :param package_id: the package id
    :return: the response object
    """
    package = None
    if package_id:
        package = get_object_or_404(
            models.MetaPackage,
            pk=package_id,
        )

    form = forms.MetaPackageForm(
        instance=package,
    )
    if request.POST:
        form = forms.MetaPackageForm(
            request.POST,
            request.FILES,
            instance=package,
        )
        if form.is_valid():
            form.save()
            form.save_m2m()
            messages.add_message(
                request,
                messages.SUCCESS,
                "Meta Package Saved.",
            )
            return redirect(reverse("list_meta_packages"))
    template = "package/staff/meta_package.html"
    context = {
        "package": package,
        "form": form,
    }
    return render(
        request,
        template,
        context,
    )
