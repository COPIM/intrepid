from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import render, reverse, redirect, get_object_or_404
from fluid_permissions.decorators import user_in_authorised_group

from initiatives import models as im
from intrepid.security import user_is_initiative_manager
from package import models, utils, forms


@user_in_authorised_group
def order_list(request) -> HttpResponse:
    """
    List all orders.
    :param request: the request
    :return: the response
    """
    filters = request.GET.getlist("filter")
    if not filters:
        filters = ["new", "provisional", "complete", "lapsed"]

    orders = models.Order.objects.filter(
        status__in=filters,
    )

    if request.POST:
        order_pk = request.POST.get("delete")
        order_to_delete = get_object_or_404(
            models.Order,
            pk=order_pk,
        )
        order_to_delete.delete()
        messages.add_message(
            request,
            messages.SUCCESS,
            "Order deleted",
        )
        redirect_url = reverse("order_list")
        filter_params = "&filter=".join(filters)
        return redirect("{}?filter={}".format(redirect_url, filter_params))

    template = "orders/order_list.html"
    context = {
        "orders": orders,
        "filters": filters,
    }
    return render(
        request,
        template,
        context,
    )


@user_in_authorised_group
def order_detail(request, order_id) -> HttpResponse:
    """
    Detail view for an order.
    :param request: the request
    :param order_id: the order id
    :return: the response
    """
    order = get_object_or_404(
        models.Order,
        pk=order_id,
    )
    if request.POST:
        if "remove" in request.POST:
            signup_id = request.POST.get("remove")
            signup_to_delete = get_object_or_404(
                models.PackageSignup,
                pk=signup_id,
                associated_order=order,
            )
            signup_to_delete.delete()
            messages.add_message(
                request,
                messages.WARNING,
                "Signup removed from Order.",
            )
            regenerated_frozen_zip = utils.generate_package_docs_zip(
                order, request
            )

            order.document = regenerated_frozen_zip
            order.save()
        if "rebuild_docs" in request.POST:
            order.rebuild_docs(request)
            messages.add_message(
                request,
                messages.SUCCESS,
                "Documents rebuilt.",
            )
        return redirect(
            reverse(
                "order_detail",
                kwargs={
                    "order_id": order.pk,
                },
            )
        )
    template = "orders/order_detail.html"
    context = {
        "order": order,
        "packages": order.package_set,
    }
    return render(
        request,
        template,
        context,
    )


@user_in_authorised_group
def order_edit_create(request, order_id=None) -> HttpResponse:
    """
    Edit or create an order.
    :param request: the request
    :param order_id: the order id
    :return: the response
    """
    order = None

    if order_id:
        order = get_object_or_404(
            models.Order,
            pk=order_id,
        )
    form = forms.OrderForm(
        instance=order,
    )

    if request.POST:
        form = forms.OrderForm(
            request.POST,
            instance=order,
        )
        if form.is_valid():
            order = form.save()
            messages.add_message(
                request,
                messages.SUCCESS,
                "Order saved.",
            )
            return redirect(
                reverse(
                    "order_detail",
                    kwargs={"order_id": order.pk},
                )
            )

    template = "orders/order_edit_create.html"
    context = {
        "order": order,
        "form": form,
    }
    return render(
        request,
        template,
        context,
    )


@user_is_initiative_manager
def initiative_order_list(request, initiative=None) -> HttpResponse:
    """
    List all orders for an initiative.
    :param request: the request
    :param initiative: the initiative
    :return: the response
    """

    filters = request.GET.getlist("filter")
    if not filters:
        filters = ["new", "provisional", "complete", "lapsed"]

    orders = models.Order.objects.filter(
        status__in=filters,
        initiative=initiative,
    )

    if request.POST:
        order_pk = request.POST.get("delete")
        order_to_delete = get_object_or_404(
            models.Order,
            pk=order_pk,
            initiative=initiative,
        )
        order_to_delete.delete()
        messages.add_message(
            request,
            messages.SUCCESS,
            "Order deleted",
        )
        redirect_url = reverse("order_list")
        filter_params = "&filter=".join(filters)
        return redirect("{}?filter={}".format(redirect_url, filter_params))

    template = "orders/order_list.html"
    context = {
        "orders": orders,
        "filters": filters,
        "initiative": initiative,
    }
    return render(
        request,
        template,
        context,
    )


@user_is_initiative_manager
def initiative_order_create(request, initiative, order_id=None) -> HttpResponse:
    """
    Create an order for an initiative.
    :param request: the request
    :param initiative: the initiative
    :param order_id: the order id
    :return: the response
    """
    order = None
    if order_id:
        order = get_object_or_404(
            models.Order,
            pk=order_id,
        )
    form = forms.OrderForm(
        instance=order,
        initiative=initiative,
    )

    if request.POST:
        form = forms.OrderForm(
            request.POST,
            instance=order,
            initiative=initiative,
        )
        if form.is_valid():
            order = form.save()
            messages.add_message(
                request,
                messages.SUCCESS,
                "Order saved.",
            )
            return redirect(
                reverse(
                    "initiative_order_detail",
                    kwargs={"initiative": initiative.pk, "order_id": order.pk},
                )
            )

    template = "orders/order_edit_create.html"
    context = {
        "order": order,
        "form": form,
    }
    return render(
        request,
        template,
        context,
    )


@user_is_initiative_manager
def initiative_order_detail(request, initiative, order_id) -> HttpResponse:
    """
    Detail view for an order.
    :param request: the request
    :param initiative: the initiative
    :param order_id: the order id
    :return: the response
    """
    order = get_object_or_404(
        models.Order,
        pk=order_id,
        initiative=initiative,
    )
    if request.POST:
        if "remove" in request.POST:
            signup_id = request.POST.get("remove")
            signup_to_delete = get_object_or_404(
                models.PackageSignup,
                pk=signup_id,
                associated_order=order,
                associated_order__initiative=initiative,
            )
            signup_to_delete.delete()
            messages.add_message(
                request,
                messages.WARNING,
                "Signup removed from Order.",
            )
            regenerated_frozen_zip = utils.generate_package_docs_zip(
                order, request
            )
            order.document = regenerated_frozen_zip
            order.save()
        if "rebuild_docs" in request.POST:
            order.rebuild_docs(request)
            messages.add_message(
                request,
                messages.SUCCESS,
                "Documents rebuilt.",
            )
        return redirect(
            reverse(
                "initiative_order_detail",
                kwargs={
                    "initiative": initiative.pk,
                    "order_id": order.pk,
                },
            )
        )
    template = "orders/order_detail.html"
    context = {
        "order": order,
        "packages": order.package_set,
        "initiative": initiative,
    }
    return render(
        request,
        template,
        context,
    )


@user_in_authorised_group
def order_add_image(request, order_id) -> HttpResponse:
    """
    Add an image to an order.
    :param request: the request
    :param order_id: the order id
    :return: the response
    """
    order = get_object_or_404(
        models.Order,
        pk=order_id,
    )
    form = forms.PrivateImageForm(
        order=order,
    )
    if request.POST:
        form = forms.PrivateImageForm(
            request.POST,
            request.FILES,
            order=order,
        )
        if form.is_valid():
            form.save()
            messages.add_message(
                request,
                messages.SUCCESS,
                "Image uploaded",
            )
            return redirect(
                reverse(
                    "order_detail",
                    kwargs={"order_id": order.pk},
                )
            )
    template = "orders/order_add_image.html"
    context = {
        "order": order,
        "form": form,
    }
    return render(
        request,
        template,
        context,
    )


@user_in_authorised_group
def order_serve_image(request, order_id, image_id) -> HttpResponse:
    """
    Serve an image from an order.
    :param request: the request
    :param order_id: the order id
    :param image_id: the image id
    :return: the response
    """
    order = get_object_or_404(
        models.Order,
        pk=order_id,
    )
    try:
        image = order.private_images.get(pk=image_id)
    except Exception:
        raise Http404

    return image.serve_image_file()


@login_required
def order_add_package(request, order_id, initiative=None) -> HttpResponse:
    """
    Add a package to an order.
    :param request: the request
    :param order_id: the order id
    :param initiative: the initiative
    :return: the response
    """
    order = get_object_or_404(
        models.Order,
        pk=order_id,
    )
    if initiative:
        initiative = get_object_or_404(
            im.Initiative,
            pk=initiative,
            users=request.user,
        )

    packages = (
        models.Package.objects.all()
        .exclude(id__in=[package.pk for package in order.package_set])
        .order_by(
            "initiative__name",
        )
    )

    if initiative:
        if not request.user.is_staff:
            if request.user not in initiative.users.all():
                raise PermissionError(
                    "You do not have permission to edit this page."
                )
            if not order.initiative == initiative:
                raise PermissionError(
                    "You do not have permission to edit this page."
                )

        packages = packages.filter(initiative=initiative)

    if request.POST and "add" in request.POST:
        package_id = request.POST.get("add")
        package = get_object_or_404(
            models.Package,
            pk=package_id,
        )
        price, banding = utils.get_price_for_package(
            package=package,
            identifier=request.user,
            identifier_type="user",
            country=order.associated_user.profile.default_currency
            if request.user
            else None,
        )

        models.PackageSignup.objects.create(
            associated_user=order.associated_user,
            associated_order=order,
            associated_package=package,
            price=price.value,
            currency=price.country,
            banding=banding,
        )

        # Generate new docs, remove old and assign new.
        order.rebuild_docs(request)

        messages.add_message(
            request,
            messages.SUCCESS,
            "Package added to order.",
        )
        if initiative:
            return redirect(
                reverse(
                    "initiative_order_detail",
                    kwargs={
                        "initiative": initiative.pk,
                        "order_id": order.pk,
                    },
                )
            )
        return redirect(
            reverse(
                "order_detail",
                kwargs={
                    "order_id": order.pk,
                },
            )
        )
    template = "orders/order_add_package.html"
    context = {
        "order": order,
        "packages": packages,
    }
    return render(
        request,
        template,
        context,
    )
