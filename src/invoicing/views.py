from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect, reverse

from initiatives import models as im
from intrepid.security import user_is_initiative_manager
from invoicing import forms, models
from package import models as pm


@login_required
def list_order_invoices(request, payment_processor_id) -> HttpResponse:
    """
    Displays a list of an order's invoices.
    :param request: the request
    :param payment_processor_id: the payment processor ID
    :return: an HttpResponse
    """
    if request.user.is_staff:
        payment_processor = get_object_or_404(
            models.PaymentProcessor,
            pk=payment_processor_id,
        )
    else:
        payment_processor = get_object_or_404(
            models.PaymentProcessor,
            pk=payment_processor_id,
            managers=request.user,
        )
    orders = pm.Order.objects.filter(
        packagesignup__associated_package__bandingtypecurrencyentry__payment_processor=payment_processor,
        status="complete",
    ).distinct()

    processor_orders = []

    # now check whether each order has any signups that this processor should
    # handle
    if request.user.is_staff or request.user.is_superuser:
        processor_orders = orders
        pass
    else:
        for order in orders:
            if order.has_processor(request.user):
                processor_orders.append(order)

    template = "invoicing/list_order_invoices.html"
    context = {
        "orders": processor_orders,
        "payment_processor": payment_processor,
    }
    return render(
        request,
        template,
        context,
    )


@login_required
def detail_invoice(request, payment_processor_id, order_id) -> HttpResponse:
    """
    Shows details of an invoice.
    :param request: the request
    :param payment_processor_id: the payment processor ID
    :param order_id: the order ID
    :return: an HttpResponse
    """
    if request.user.is_staff:
        payment_processor = get_object_or_404(
            models.PaymentProcessor,
            pk=payment_processor_id,
        )
    else:
        payment_processor = get_object_or_404(
            models.PaymentProcessor,
            pk=payment_processor_id,
            managers=request.user,
        )
    order = get_object_or_404(pm.Order, pk=order_id)
    status_form = forms.StatusForm()

    if not request.user.is_staff:
        # we have to handle it this way to avoid the weird Distinct collision
        # bug
        try:
            order = pm.Order.objects.filter(
                pk=order_id,
                packagesignup__associated_package__bandingtypecurrencyentry__payment_processor=payment_processor,
            ).distinct()

            # perform this as a separate operation so that order is always set
            # to an empty queryset if the index doesn't exist, which allows
            # for the signups query below
            order = order[0]
        except (pm.Order.DoesNotExist, IndexError):
            pass

    signups = order.packagesignup_set.all()

    if request.user.is_staff or request.user.is_superuser:
        pass
    else:
        # filter by payment processor
        to_remove = []

        for signup in signups:
            if (
                signup.payment_processor
                and not signup.payment_processor.is_member(request.user)
            ):
                # user is not a payment processor for this signup
                to_remove.append(signup)
            elif not signup.payment_processor:
                # this signup has no payment processor
                to_remove.append(signup)

        # exclude non-owned items from the queryset
        for remove in to_remove:
            signups = signups.exclude(pk=remove.pk)

    if request.POST:
        fire_redirect = True

        if "signup" in request.POST:
            signup_id = request.POST.get("signup")
            signup = signups.get(
                pk=signup_id,
            )
            models.SignupInvoice.objects.get_or_create(
                payment_processor=payment_processor,
                signup=signup,
                defaults={
                    "status": "new",
                },
            )

        if "signupinvoice" in request.POST:
            signupinvoice_id = request.POST.get("signupinvoice")
            status = request.POST.get("status")

            if signupinvoice_id and status:
                signup = get_object_or_404(
                    models.SignupInvoice,
                    pk=signupinvoice_id,
                    signup__in=signups,
                )
                signup.status = status
                signup.save()
                messages.add_message(
                    request, messages.SUCCESS, "Invoice status update."
                )
            else:
                messages.add_message(
                    request,
                    messages.ERROR,
                    "No Invoice ID or Status supplied.",
                )

        if fire_redirect:
            return redirect(
                reverse(
                    "detail_invoice",
                    kwargs={
                        "payment_processor_id": payment_processor.pk,
                        "order_id": order.pk,
                    },
                )
            )

    template = "invoicing/detail_invoice.html"
    context = {
        "payment_processor": payment_processor,
        "order": order,
        "signups": signups,
        "status_form": status_form,
    }
    return render(
        request,
        template,
        context,
    )


@user_is_initiative_manager
def list_order_invoices_initiative(request, initiative_id) -> HttpResponse:
    """
    Displays a list of an order's invoices.
    :param request: the request
    :param initiative_id: the initiative ID
    :return: an HttpResponse
    """
    initiative = get_object_or_404(
        im.Initiative,
        pk=initiative_id,
    )
    orders = pm.Order.objects.filter(
        packagesignup__associated_package__initiative=initiative,
        packagesignup__associated_package__bandingtypecurrencyentry__payment_processor=None,
        status="complete",
    ).distinct()

    template = "invoicing/list_order_invoices_initiative.html"
    context = {
        "orders": orders,
        "initiative": initiative,
    }
    return render(
        request,
        template,
        context,
    )


@user_is_initiative_manager
def detail_invoice_initiative(request, initiative_id, order_id) -> HttpResponse:
    """
    Invoice detailing for an initiative.
    :param request: a request object
    :param initiative_id: an initiative ID
    :param order_id: an order ID
    :return: an HttpResponse
    """
    initiative = get_object_or_404(
        im.Initiative,
        pk=initiative_id,
    )
    order = get_object_or_404(
        pm.Order,
        pk=order_id,
    )
    signups = pm.PackageSignup.objects.filter(
        associated_order=order,
        associated_package__initiative=initiative,
    )
    status_form = forms.StatusForm()

    if request.POST:
        fire_redirect = True

        if "signup" in request.POST:
            signup_id = request.POST.get("signup")
            signup = signups.get(
                pk=signup_id,
            )
            models.SignupInvoice.objects.get_or_create(
                payment_processor=None,
                signup=signup,
                defaults={
                    "status": "new",
                },
            )

        if "signupinvoice" in request.POST:
            signupinvoice_id = request.POST.get("signupinvoice")
            status = request.POST.get("status")

            if signupinvoice_id and status:
                signup = get_object_or_404(
                    models.SignupInvoice,
                    pk=signupinvoice_id,
                    signup__in=signups,
                )
                signup.status = status
                signup.save()
                messages.add_message(
                    request, messages.SUCCESS, "Invoice status update."
                )
            else:
                messages.add_message(
                    request,
                    messages.ERROR,
                    "No Invoice ID or Status supplied.",
                )

        if fire_redirect:
            return redirect(
                reverse(
                    "detail_invoice_initiative",
                    kwargs={
                        "initiative_id": initiative.pk,
                        "order_id": order.pk,
                    },
                )
            )

    template = "invoicing/detail_invoice_initiative.html"
    context = {
        "initiative": initiative,
        "order": order,
        "signups": signups,
        "status_form": status_form,
    }
    return render(
        request,
        template,
        context,
    )


@staff_member_required
def list_payment_processors(request) -> HttpResponse:
    """
    Create a list of payment processors
    :param request: a request object
    :return: an HttpResponse
    """
    payment_processors = models.PaymentProcessor.objects.all()

    if request.POST and "delete" in request.POST:
        id_to_delete = request.POST.get("delete")
        processor = get_object_or_404(
            models.PaymentProcessor,
            pk=id_to_delete,
        )
        processor.delete()
        messages.add_message(
            request,
            messages.ERROR,
            "Payment Processor deleted.",
        )
        return redirect(
            reverse("list_payment_processors"),
        )

    template = "invoicing/list_payment_processors.html"
    context = {
        "payment_processors": payment_processors,
    }
    return render(request, template, context)


@staff_member_required
def edit_payment_processor(request, processor_id=None) -> HttpResponse:
    """
    Edit a payment processor
    :param request: a request object
    :param processor_id: a payment processor ID
    :return: an HttpResponse
    """
    processor = None
    if processor_id:
        processor = get_object_or_404(
            models.PaymentProcessor,
            pk=processor_id,
        )

    form = forms.PaymentProcessorForm(
        instance=processor,
    )
    if request.POST:
        form = forms.PaymentProcessorForm(
            request.POST,
            instance=processor,
        )
        if form.is_valid():
            form.save()
            messages.add_message(
                request,
                messages.SUCCESS,
                "Payment Processor saved.",
            )
            return redirect(
                "list_payment_processors",
            )

    template = "invoicing/edit_payment_processors.html"
    context = {
        "form": form,
        "processor": processor,
    }
    return render(
        request,
        template,
        context,
    )
