import os

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models.functions import Lower
from django.http import HttpResponse, FileResponse
from django.shortcuts import (
    render,
    get_object_or_404,
    redirect,
    reverse,
    Http404,
)
from django.utils import timezone
from django.views.decorators.http import require_POST
from fluid_permissions.decorators import user_in_authorised_group

from access import forms as access_forms
from access import models as access_models
from initiatives import models as initiative_models
from intrepid.security import user_is_initiative_manager
from intrepid.utils import return_or_elsewhere
from invoicing import models as invoicing_models
from package import models, forms, utils
from vocab import models as vocab_models
from cms import models as cms_models


def initiative_list(request) -> HttpResponse:
    """
    List all initiatives that the user has access to.
    :param request: the request
    :return: the response
    """
    search_on = False
    packages = models.Package.objects.filter(
        active=True,
    ).order_by(Lower("name"))

    subject_pks = []
    for package in packages:
        for subject in package.subjects.all():
            subject_pks.append(subject.pk)

    subjects = vocab_models.SubjectVocab.objects.filter(
        pk__in=set(subject_pks)
    )
    initiatives = initiative_models.Initiative.objects.filter(
        active=True,
    )

    if request.session.get("country", None):
        packages = utils.add_pre_calc_to_objects(
            request.session.get("country"),
            packages,
        )

    initiative = request.GET.get("initiative")
    subject = request.GET.get("subject")
    sort = request.GET.get("sort")
    standards = request.GET.getlist("standards", [])

    if subject and subject != "all":
        subject = vocab_models.SubjectVocab.objects.filter(
            pk=subject,
        )
        packages = packages.filter(subjects__in=subject)
    if initiative and initiative != "all":
        packages = packages.filter(initiative__pk=initiative)
    if sort:
        packages = packages.order_by("-{}".format(sort))
    if standards:
        standards_q = vocab_models.StandardVocab.objects.filter(
            pk__in=standards,
        )
        queries = []
        for standard in standards_q:
            queries.append(
                packages.filter(standards_attested__standard=standard)
            )
        packages = packages.intersection(*queries)

    if subject or sort or initiative:
        search_on = True

    template = "base/frontend/quote/packages.html"
    context = {
        "packages": packages,
        "subjects": subjects,
        "search_on": search_on,
        "standards": vocab_models.StandardVocab.objects.all(),
        "get_standards": standards,
        "initiatives": initiatives,
        "country_form": forms.CountryForm(
            session_country_code=request.session["country"]
        ),
    }
    return render(
        request,
        template,
        context,
    )


def collective_list(request) -> HttpResponse:
    """
    List all collectives that the user has access to.
    :param request: the request
    :return: the response
    """
    meta_packages = models.MetaPackage.objects.filter(
        active=True,
    ).order_by("-recommended", "name")

    if request.session.get("country", None):
        utils.add_pre_calc_to_meta_objects(
            request.session.get("country"),
            meta_packages,
        )

    template = "base/frontend/quote/collective_list.html"
    context = {
        "meta_packages": meta_packages,
        "search_on": False,
        "collectives_only": True,
        "country_form": forms.CountryForm(
            session_country_code=request.session["country"]
        ),
    }
    return render(
        request,
        template,
        context,
    )


def package_info(request, package_id) -> HttpResponse:
    """
    Display information about a package.
    :param request: the request
    :param package_id: the package ID
    :return: the response
    """
    try:
        package = models.Package.objects.get(pk=package_id, active=True)
        package_type = "package"
    except models.Package.DoesNotExist:
        try:
            package = models.MetaPackage.objects.get(
                pk=package_id, active=True
            )
            package_type = "meta"
        except models.MetaPackage.DoesNotExist:
            raise Http404

    template = "package/info.html"
    context = {
        "package": package,
        "package_type": package_type,
    }
    return render(
        request,
        template,
        context,
    )


@login_required
def list_signups(request) -> HttpResponse:
    """
    List all signups that the user has access to.
    :param request: the request
    :return: the response
    """
    # set in middleware
    signups = request.signups

    template = "package/signups.html"
    context = {
        "signups": signups,
    }
    return render(
        request,
        template,
        context,
    )


@user_is_initiative_manager
def process_signup(
    request, initiative_id, package_id, signup_id
) -> HttpResponse:
    """
    Process a signup.
    :param request: the request
    :param initiative_id: the initiative ID
    :param package_id: the package ID
    :param signup_id: the signup ID
    :return: the response
    """
    # set in middleware
    signup = models.PackageSignup.objects.get(
        pk=signup_id, associated_package__initiative_id=initiative_id
    )
    try:
        custom_document = models.CustomPackageDocument.objects.get(
            package_signup=signup,
        )
    except models.CustomPackageDocument.DoesNotExist:
        custom_document = None
    form = forms.CustomDocumentForm(
        instance=custom_document,
        package_signup=signup,
    )

    if request.POST:
        if "approve" in request.POST:
            signup.initiative_approved = timezone.now()
            signup.initiative_approved_by = request.user
            signup.save()
            return redirect(
                reverse(
                    "process_signup",
                    kwargs={
                        "initiative_id": initiative_id,
                        "package_id": package_id,
                        "signup_id": signup_id,
                    },
                )
            )
        if "submit" in request.POST:
            form = forms.CustomDocumentForm(
                request.POST,
                request.FILES,
                instance=custom_document,
                package_signup=signup,
            )
            if form.is_valid():
                form.save()
                signup.associated_order.rebuild_docs(request)
                return redirect(
                    reverse(
                        "process_signup",
                        kwargs={
                            "initiative_id": initiative_id,
                            "package_id": package_id,
                            "signup_id": signup_id,
                        },
                    )
                )

    template = "package/process_signup.html"
    context = {
        "signup": signup,
        "form": form,
    }
    return render(
        request,
        template,
        context,
    )


@user_is_initiative_manager
def package_access_control_change(
    request, signup_id, initiative_id, access_type
) -> HttpResponse:
    """
    Change the access control for a package.
    :param request: the request
    :param signup_id: the signup ID
    :param initiative_id: the initiative ID
    :param access_type: the access type
    :return: the response
    """
    # get the signup (the filter on package initiative in request.initiatives
    # ensures that the user has permission to edit this signup)
    signup = get_object_or_404(
        models.PackageSignup,
        pk=signup_id,
        associated_package__initiative__in=request.initiatives,
    )

    initiative = None

    if not request.POST:
        initiative = get_object_or_404(
            initiative_models.Initiative, pk=initiative_id
        )

        dummy_instance = access_models.AccessLog()
        dummy_instance.access_type = access_type

        form = access_forms.AccessLogForm(
            signup=signup, request=request, instance=dummy_instance
        )
    else:
        form = access_forms.AccessLogForm(
            request.POST, signup=signup, request=request
        )

        if form.is_valid:
            form.save()
            return redirect(
                reverse(
                    "package_access_control",
                    kwargs={
                        "package_id": signup.associated_package.pk,
                        "initiative_id": initiative_id,
                    },
                )
            )

    if not initiative:
        initiative = get_object_or_404(
            initiative_models.Initiative, pk=initiative_id
        )

    template = "package/change_access.html"
    context = {"form": form, "initiative": initiative}

    return render(request, template, context)


@user_is_initiative_manager
def package_access_control(request, package_id, initiative_id) -> HttpResponse:
    """
    Display the access control for a package.
    :param request: the request
    :param package_id: the package ID
    :param initiative_id: the initiative ID
    :return: the response
    """
    # set in middleware
    signups = request.signups

    initiative = get_object_or_404(
        initiative_models.Initiative, pk=initiative_id
    )

    package = get_object_or_404(
        models.Package, pk=package_id, initiative=initiative_id
    )

    # set a property on each signup of whether access has been granted
    # or revoked
    for signup in signups:
        try:
            access_state = access_models.AccessLog.objects.filter(
                signup__associated_package=package
            ).order_by("-date_stamp")[0]

            if access_state.access_type == "grant":
                signup.access = True
            else:
                signup.access = False
        except IndexError:
            signup.access = False
            pass

    template = "package/access_control.html"
    context = {
        "signups": signups,
        "package": package,
        "initiative": initiative,
    }
    return render(
        request,
        template,
        context,
    )


@user_is_initiative_manager
@require_POST
def package_standards_attest_delete(
    request, package_id, initiative_id, standard_id
) -> HttpResponse:
    """
    Delete a standard attestation.
    :param request: the request
    :param package_id: the package ID
    :param initiative_id: the initiative ID
    :param standard_id: the standard ID
    :return: the response
    """
    package = get_object_or_404(
        models.Package, pk=package_id, initiative=initiative_id
    )

    standard = get_object_or_404(vocab_models.StandardVocab, pk=standard_id)

    try:
        vocab_models.PackageStandardAttestation.objects.get(
            package=package, standard=standard
        ).delete()
        vocab_models.AttestationHistory.objects.create(
            standard=standard,
            package=package,
            add_or_remove="removed",
        )
    except vocab_models.PackageStandardAttestation.DoesNotExist:
        raise Http404

    return redirect(
        reverse(
            "package_standards",
            kwargs={"package_id": package_id, "initiative_id": initiative_id},
        )
    )


@user_is_initiative_manager
def package_standards_attest(
    request, package_id, initiative_id, standard_id
) -> HttpResponse:
    """
    Attest to a standard.
    :param request: the request
    :param package_id: the package ID
    :param initiative_id: the initiative ID
    :param standard_id: the standard ID
    :return: the response
    """
    package = get_object_or_404(
        models.Package, pk=package_id, initiative=initiative_id
    )

    standard = get_object_or_404(vocab_models.StandardVocab, pk=standard_id)

    initiative = get_object_or_404(
        initiative_models.Initiative, pk=initiative_id
    )

    try:
        attest = vocab_models.PackageStandardAttestation.objects.get(
            package=package, standard=standard
        )
    except vocab_models.PackageStandardAttestation.DoesNotExist:
        attest = None

    if request.POST:
        form = forms.StandardsAttestForm(
            request.POST, instance=attest, package=package, standard=standard
        )

        if form.is_valid():
            form.save()
            vocab_models.AttestationHistory.objects.create(
                standard=standard,
                package=package,
                add_or_remove="added",
            )

        return redirect(
            reverse(
                "package_standards",
                kwargs={
                    "package_id": package_id,
                    "initiative_id": initiative_id,
                },
            )
        )
    else:
        form = forms.StandardsAttestForm(
            instance=attest, package=package, standard=standard
        )

    template = "package/manage/new_edit_standard_attest.html"
    context = {
        "package": package,
        "initiative": initiative,
        "form": form,
        "standard": standard,
    }
    return render(
        request,
        template,
        context,
    )


@user_is_initiative_manager
def package_standards(request, package_id, initiative_id) -> HttpResponse:
    """
    Display the standards for a package.
    :param request: the request
    :param package_id: the package ID
    :param initiative_id: the initiative ID
    :return: the response
    """
    package = get_object_or_404(
        models.Package, pk=package_id, initiative=initiative_id
    )

    if request.POST and "add_new" in request.POST:
        return redirect(
            reverse(
                "package_standards_attest",
                kwargs={
                    "package_id": package_id,
                    "initiative_id": initiative_id,
                    "standard_id": request.POST["standards"][0],
                },
            )
        )

    initiative = get_object_or_404(
        initiative_models.Initiative, pk=initiative_id
    )

    standard_attests = vocab_models.PackageStandardAttestation.objects.filter(
        package=package
    )

    template = "package/manage/standards.html"
    context = {
        "standard_attests": standard_attests,
        "package": package,
        "initiative": initiative,
        "standards_list": forms.StandardsTypeField(),
    }
    return render(
        request,
        template,
        context,
    )


@user_is_initiative_manager
def package_contacts(request, package_id, initiative_id) -> HttpResponse:
    """
    Display the contacts for a package.
    :param request: the request
    :param package_id: the package ID
    :param initiative_id: the initiative ID
    :return: the response
    """
    # the middleware gives us request.initiatives for initiatives owned
    # by the logged-in user
    contacts = access_models.Contact.objects.filter(
        initiative__in=request.initiatives
    )

    package = get_object_or_404(
        models.Package, pk=package_id, initiative=initiative_id
    )

    if request.POST:
        signup_ids = request.POST.getlist("signup_contact")
        access_ids = request.POST.getlist("access_contact")

        package.set_contacts(signup_ids, "signup_contacts")
        package.set_contacts(access_ids, "access_contacts")

        return redirect(
            reverse(
                "package_contacts",
                kwargs={
                    "package_id": package_id,
                    "initiative_id": initiative_id,
                },
            )
        )

    template = "package/manage/contacts.html"
    context = {"signup_contacts": contacts, "package": package}
    return render(
        request,
        template,
        context,
    )


def view_baskets(request) -> HttpResponse:
    """
    View the baskets for the user.
    :param request: the request
    :return: the response
    """
    if request.user.is_authenticated:
        baskets = models.Basket.objects.filter(
            account=request.user,
            active=True,
        )
        orders = models.Order.objects.filter(
            associated_user=request.user,
        )
    else:
        baskets = models.Basket.objects.filter(
            session_id=request.session.session_key,
            active=True,
        )
        orders = None

    if request.POST and "basket_to_delete" in request.POST:
        baskets.filter(pk=request.POST.get("basket_to_delete")).delete()
        messages.add_message(
            request,
            messages.SUCCESS,
            "Basket deleted.",
        )
        return redirect(reverse("basket_list"))

    template = ("package/view_baskets.html",)
    context = {
        "baskets": baskets,
        "orders": orders,
    }
    return render(
        request,
        template,
        context,
    )


def view_basket(request, basket_id) -> HttpResponse:
    """
    View a basket.
    :param request: the request
    :param basket_id: the basket ID
    :return: the response
    """
    identifier = (
        request.user if request.user.is_authenticated else request.session
    )
    identifier_type = "user" if request.user.is_authenticated else "session"

    # prefetch all CMS text objects to avoid template hits
    final_prefetched = {o.key: o for o in cms_models.SiteText.objects.all()}

    (
        site_percentage,
        currency_converted,
        converted_total,
        converted_currency,
        currency_conversion_total,
        site_percentage_value,
    ) = (None, None, None, None, None, None)

    if request.user.is_authenticated:
        basket = get_object_or_404(
            models.Basket,
            pk=basket_id,
            account=request.user,
            active=True,
        )
    else:
        basket = get_object_or_404(
            models.Basket,
            pk=basket_id,
            session_id=request.session.session_key,
            active=True,
        )

    banding_types = basket.get_best_bandings_for_form(
        identifier, identifier_type
    )
    fte_form = forms.FTEForm(
        user_session=request.session,
        user=request.user if request.user.is_authenticated else None,
        banding_types=banding_types,
    )

    message = utils.check_basket_for_disabled_signups(request, basket)

    if request.POST:
        fte_form = forms.FTEForm(
            request.POST,
            user_session=request.session,
            user=request.user if request.user.is_authenticated else None,
            banding_types=banding_types,
        )
        if fte_form.is_valid():
            fte_form.save()
            url = "{}#form_start".format(
                reverse(
                    "basket_detail",
                    kwargs={"basket_id": basket_id},
                )
            )
            return redirect(url)

    package_costs, currency_totals = basket.cost(
        identifier=identifier, identifier_type=identifier_type
    )

    user_currency = utils.get_user_currency(identifier, identifier_type)

    banding_list = []

    for package in basket.packages.all():
        for obj in package.bandingtypeentry_set.all().order_by(
            "banding_type__name"
        ):
            banding_list.append(obj)

    all_prices_found = True
    for price in package_costs:
        if not price["banding"] or price["cost"] == 0:
            all_prices_found = False
            break

    if all_prices_found:
        if len(currency_totals) > 1:
            (
                site_percentage,
                converted_total,
                converted_currency,
                currency_conversion_total,
                site_percentage_value,
            ) = utils.convert_currency_totals(
                request=request,
                identifier_type=identifier_type,
                identifier=identifier,
                totals=currency_totals,
            )
            currency_converted = True
        else:
            (
                site_percentage,
                site_percentage_value,
            ) = utils.calculate_site_percentage(
                request,
                currency_totals,
            )

    # User clicks the proceed button
    if "complete" in request.POST:
        if (
            not request.site.enable_signup
            or not request.site.enable_meta_package_signup
            or not request.site.enable_individual_package_signup
        ):
            if message:
                messages.add_message(request, messages.ERROR, message)
                return redirect(
                    reverse(
                        "basket_detail",
                        kwargs={"basket_id": basket.pk},
                    )
                )

        # Create the order here.
        order = models.Order.objects.create(
            associated_user=(
                request.user if request.user.is_authenticated else None
            ),
            session_id=request.session.session_key,
            basket=basket,
            valid_period="{0} to {1}".format(
                timezone.now().year, timezone.now().year + 1
            ),
            order_date=timezone.now(),
            converted_currency=converted_currency,
            converted_value=currency_conversion_total,
            platform_fee=site_percentage_value,
        )
        return redirect(
            reverse(
                "start_checkout",
                kwargs={"order_id": order.pk},
            )
        )

    template = "package/view_basket.html"
    context = {
        "basket": basket,
        "fte_form": fte_form,
        "package_costs": package_costs,
        "currency_totals": currency_totals,
        "conflicting_packages": basket.list_of_conflicting_packages(),
        "bandings": banding_list,
        "has_all_prices": all_prices_found,
        "message": message,
        "site_percentage": site_percentage,
        "currency_converted": currency_converted,
        "converted_total": converted_total,
        "converted_currency": converted_currency,
        "user_currency": user_currency,
        "prefetched": final_prefetched,
    }
    return render(
        request,
        template,
        context,
    )


def manage_basket(
    request, package_id=None, meta_package_id=None
) -> HttpResponse:
    """
    Manage a basket.
    :param request: the request
    :param package_id: the package ID
    :param meta_package_id: the meta package ID
    :return: the response
    """
    basket, package, meta_package = None, None, None

    if request.user.is_authenticated:
        baskets = models.Basket.objects.filter(
            account=request.user,
            active=True,
        )
    else:
        baskets = models.Basket.objects.filter(
            session_id=request.session.session_key,
            active=True,
        )

    basket = baskets.first()

    if request.POST:
        if "basket_id" in request.POST:
            if request.user.is_authenticated:
                basket = get_object_or_404(
                    models.Basket,
                    pk=request.POST.get("basket_id"),
                    account=request.user,
                    active=True,
                )
            else:
                basket = get_object_or_404(
                    models.Basket,
                    pk=request.POST.get("basket_id"),
                    session_id=request.session.session_key,
                    active=True,
                )

    if package_id:
        package = get_object_or_404(
            models.Package,
            pk=package_id,
            active=True,
            meta_only=False,
        )
    elif meta_package_id:
        meta_package = get_object_or_404(
            models.MetaPackage,
            pk=meta_package_id,
            active=True,
        )

    if not package and not meta_package:
        raise Http404("No package or meta package found.")

    if not baskets:
        kwargs = {
            "name": "{} Basket".format(timezone.now().date()),
            "active": True,
        }
        if request.user.is_authenticated:
            kwargs["account"] = request.user
        else:
            kwargs["session_id"] = request.session.session_key
        basket = models.Basket.objects.create(
            **kwargs,
        )

    if basket:
        if package_id and package in basket.packages.all():
            messages.add_message(
                request,
                messages.WARNING,
                "The package you selected has already been added to this quote.",
            )
            return redirect(
                reverse(
                    "basket_detail",
                    kwargs={"basket_id": basket.pk},
                )
            )
        elif package_id:
            basket.packages.add(package)
        elif meta_package_id:
            basket.meta_packages.add(meta_package)

        messages.add_message(
            request,
            messages.SUCCESS,
            "{} added to basket.".format(
                package.name if package else meta_package.name,
            ),
        )

        return redirect(
            reverse(
                "basket_detail",
                kwargs={"basket_id": basket.pk},
            )
        )
    template = "package/manage_basket.html"
    context = {
        "basket": basket,
        "baskets": baskets,
        "package": package,
        "meta_package": meta_package,
    }
    return render(
        request,
        template,
        context,
    )


@transaction.atomic
def create_checkout_documents(request, order_id=None) -> HttpResponse:
    """
    Creates the zip files and documents in the document centre
    :param request: the request object
    :param order_id: the order ID that is being checked out
    :return: needs to return an HTTP status code
    """
    if request.user.is_authenticated:
        order = get_object_or_404(
            models.Order,
            pk=order_id,
            associated_user=request.user,
        )
        identifier_type = "user"
        identifier = request.user
    else:
        order = get_object_or_404(
            models.Order,
            pk=order_id,
            session_id=request.session.session_key,
        )
        identifier_type = "session"
        identifier = request.session

    # grab the basket costs
    costs, currency_totals = order.basket.cost(
        identifier=identifier, identifier_type=identifier_type
    )

    for package_cost in costs:
        package = package_cost.get("package")
        cost = package_cost.get("cost")
        banding = package_cost.get("banding")
        # create signup objects for each of these and associate them
        # with the order

        models.PackageSignup.objects.create(
            associated_user=(
                request.user if request.user.is_authenticated else None
            ),
            associated_session=request.session.session_key,
            associated_order=order,
            associated_package=package,
            price=cost.value,
            currency=cost.country if cost.country else package.default_country,
            status="provisional",
            banding=banding,
        )

        # Generate a new frozen zip.Z
        frozen_document = utils.generate_package_docs_zip(order, request)
        # Unlink the old one.
        utils.unlink_frozen_doc(order)

        # Set the document and save.
        order.document = frozen_document
        order.save()

        # set the basket as inactive now we have an order record.
        order.basket.active = False
        order.basket.save()

    return redirect(
        reverse(
            "order_form",
            kwargs={
                "order_id": order.pk,
            },
        )
    )


@transaction.atomic
def order_form(request, order_id) -> HttpResponse:
    """
    Display an order form
    :param request: the request
    :param order_id: the order ID
    :return: an HttpResponse
    """
    order_amount = ""
    platform_fee = ""
    total = ""

    if request.user.is_authenticated:
        order = get_object_or_404(
            models.Order,
            pk=order_id,
            associated_user=request.user,
        )
        identifier_type = "user"
        identifier = request.user
    else:
        order = get_object_or_404(
            models.Order,
            pk=order_id,
            session_id=request.session.session_key,
        )
        identifier_type = "session"
        identifier = request.session

    if order.converted_currency and order.converted_value:
        if request.POST:
            multiplier = request.POST.get("term_length", 1)
        else:
            multiplier = 1

        order.converted_value = order.converted_value * int(multiplier)
        order.platform_fee = order.platform_fee * int(multiplier)

        order_amount = "Offers: {} {}".format(
            order.converted_currency, order.converted_value
        )
        platform_fee = "OBC Processing Fee: {} {}".format(
            order.converted_currency, order.platform_fee
        )
        total = "Total: {}".format(
            utils.format_price(
                (order.converted_value + order.platform_fee),
                order.converted_currency,
            )
        )
    else:
        costs, currency_totals = order.basket.cost(identifier, identifier_type)
        for k, v in currency_totals.items():
            if request.POST:
                multiplier = request.POST.get("term_length", 1)
            else:
                multiplier = 1

            v = v * int(multiplier)
            order.platform_fee = order.platform_fee * int(multiplier)

            order_amount = utils.format_price(v, k)
            platform_fee = utils.format_price(order.platform_fee, k)

            total = utils.format_price((v + order.platform_fee), k)

    signups = order.packagesignup_set.all()
    form = forms.GeneratedForm(
        order=order,
        fields_required=True,
        email_address=(
            request.user.email if request.user.is_authenticated else ""
        ),
    )

    if request.POST:
        form = forms.GeneratedForm(
            request.POST,
            order=order,
            fields_required=True,
            email_address=(
                request.user.email if request.user.is_authenticated else ""
            ),
        )

        # check if it's a state change
        is_changed = request.GET.get("changed", "")

        if form.is_valid() and is_changed == "":
            order.save_order_form(form)
            order.status = "provisional"
            order.save()

            # now process the order form answers against the signups
            # this parcels out the data to signups
            order.parcel_data(signups)

            utils.send_new_order_notification(
                order,
                request,
                identifier,
                identifier_type,
            )

            return redirect(
                reverse(
                    "new_order_complete",
                    kwargs={"order_id": order.pk},
                )
            )

    template = "package/checkout/order_form.html"
    context = {
        "order": order,
        "signups": signups,
        "form": form,
        "order_amount": order_amount,
        "platform_fee": platform_fee,
        "total": total,
    }
    return render(
        request,
        template,
        context,
    )


@login_required
def order_provisional(request, order_id) -> HttpResponse:
    """
    Display a provisional order.
    :param request: the request
    :param order_id: the order ID
    :return: an HttpResponse
    """
    order = get_object_or_404(
        models.Order,
        pk=order_id,
        associated_user=request.user,
    )

    if order.status == "complete":
        return redirect(
            reverse(
                "order_complete",
                kwargs={
                    "order_id": order_id,
                },
            )
        )
    elif order.status in ["new", "lapsed"]:
        raise Http404

    signups = order.packagesignup_set.all()
    contact_rows = utils.provisional_page_table_rows(
        order,
    )
    if request.POST and "approve" in request.POST:
        package_signup_id = request.POST.get("approve")
        package_signup = get_object_or_404(
            models.PackageSignup,
            pk=package_signup_id,
            associated_order=order,
        )
        package_signup.organisation_approved = timezone.now()
        package_signup.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            "Package approved.",
        )
        url = reverse(
            "order_provisional",
            kwargs={"order_id": order.pk},
        )
        return redirect(
            "{url}#approval_table".format(url=url),
        )

    template = "package/checkout/order_provisional.html"
    context = {
        "order": order,
        "signups": signups,
        "contact_rows": contact_rows,
    }
    return render(
        request,
        template,
        context,
    )


@login_required
def order_complete(request, order_id) -> HttpResponse:
    """
    Display a completed order.
    :param request: the request
    :param order_id: the order ID
    :return: an HttpResponse
    """
    order = get_object_or_404(
        models.Order,
        pk=order_id,
        associated_user=request.user,
        status="complete",
    )
    signups = order.packagesignup_set.all()
    contact_rows = utils.provisional_page_table_rows(
        order,
    )
    template = "package/checkout/order_complete.html"
    context = {
        "order": order,
        "signups": signups,
        "contact_rows": contact_rows,
    }
    return render(
        request,
        template,
        context,
    )


@require_POST
def remove_from_basket(
    request, basket_id, package_id=None, meta_package_id=None
) -> HttpResponse:
    """
    Remove a package from a basket.
    :param request: the request
    :param basket_id: the basket ID
    :param package_id: the package ID
    :param meta_package_id: the meta package ID
    :return: an HttpResponse
    """
    package = None
    if request.user.is_authenticated:
        basket = get_object_or_404(
            models.Basket,
            pk=basket_id,
            account=request.user,
        )
    else:
        basket = get_object_or_404(
            models.Basket,
            pk=basket_id,
            session_id=request.session.session_key,
        )
    if package_id:
        package = get_object_or_404(
            models.Package,
            pk=package_id,
        )
        basket.packages.remove(package)
    elif meta_package_id:
        package = get_object_or_404(
            models.MetaPackage,
            pk=meta_package_id,
        )
        basket.meta_packages.remove(package)

    if package:
        messages.add_message(
            request,
            messages.SUCCESS,
            "{} removed from Quote".format(package.name),
        )

    return redirect(
        reverse(
            "basket_detail",
            kwargs={
                "basket_id": basket.pk,
            },
        )
    )


@user_in_authorised_group
def form_elements_setup(request) -> HttpResponse:
    """
    This function lists all the form elements
    :param request: request object
    :return: HttpResponse object
    """
    form_elements = models.AggregateFormElement.objects.all().order_by("order")

    template = "package/list_form_elements.html"

    context = {
        "form_elements": form_elements,
        "sort_url": reverse("form_element_order"),
    }

    return render(request, template, context)


@user_in_authorised_group
def form_element_delete(request, form_element_id) -> HttpResponse:
    """
    This function deletes a form element
    :param request: request object
    :param form_element_id: the form element_id to delete
    :return: HttpResponse object
    """
    if request.POST and "delete" in request.POST:
        instance = get_object_or_404(
            models.AggregateFormElement, pk=form_element_id
        )
        instance.delete()

    return redirect(reverse("form_element_setup"))


@user_is_initiative_manager
def form_element_package_delete(
    request, initiative_id, package_id, form_element_id
) -> HttpResponse:
    """
    This function deletes an affiliation of a form element with a package
    :param request: request object
    :param initiative_id: the initiative ID
    :param package_id: the package ID
    :param form_element_id: the form element_id to delete
    :return: HttpResponse object
    """

    if request.POST and "delete" in request.POST:
        instance = get_object_or_404(
            models.PackageFormElement, pk=form_element_id
        )
        instance.delete()

    return package_data(
        request, initiative_id=initiative_id, package_id=package_id
    )


@user_in_authorised_group
def form_element_create(request, form_element_id=None) -> HttpResponse:
    """
    This function creates a new form element
    :param request: request object
    :param form_element_id: the form element_id to edit
    :return: HttpResponse object
    """
    instance = None

    if form_element_id:
        instance = get_object_or_404(
            models.AggregateFormElement, pk=form_element_id
        )

    form = forms.FormElementForm(instance=instance)

    if request.POST:
        form = forms.FormElementForm(request.POST, instance=instance)

        if form.is_valid():
            form.save()
            messages.add_message(
                request,
                messages.SUCCESS,
                "Form Element Information Saved.",
            )
            return redirect(reverse("form_element_setup"))

    template = "package/create_form_element.html"

    context = {"form": form}

    return render(request, template, context)


@user_in_authorised_group
def package_approval(request) -> HttpResponse:
    """
    This function lists all the packages awaiting approval
    :param request: request object
    :return: HttpResponse object
    """
    packages_awaiting_approval = models.Package.objects.filter(
        active=False,
    )

    if request.POST:
        if "approve" in request.POST:
            package_id = request.POST.get("approve")
            package = get_object_or_404(
                models.Package,
                pk=package_id,
            )
            package.active = True
            package.save()
            messages.add_message(
                request,
                messages.SUCCESS,
                "Package approved.",
            )
        elif "delete" in request.POST:
            package_id = request.POST.get("delete")
            package = get_object_or_404(
                models.Package,
                pk=package_id,
            )
            package.delete()
            messages.add_message(
                request,
                messages.ERROR,
                "Package deleted.",
            )

        return redirect(
            reverse(
                "package_approval",
            )
        )

    template = "package/staff/approval.html"
    context = {
        "packages_awaiting_approval": packages_awaiting_approval,
    }
    return render(
        request,
        template,
        context,
    )


@require_POST
@user_in_authorised_group
def form_elements_order(request) -> HttpResponse:
    """
    Reorders the Form Elements list, posted via AJAX.
    :param request: HttpRequest object
    :return: HttpResponse object
    """

    ids = request.POST.getlist("form_element[]")
    ids = [int(_id) for _id in ids]

    for fe in models.AggregateFormElement.objects.all():
        fe.order = ids.index(fe.pk)
        fe.save()

    return HttpResponse("Thanks")


@user_is_initiative_manager
def list_documents(request, initiative_id, package_id) -> HttpResponse:
    """
    List the documents for a package.
    :param request: the request
    :param initiative_id: the initiative ID
    :param package_id: the package ID
    :return: the response
    """
    package = get_object_or_404(models.Package, pk=package_id)

    documents = models.PackageDocument.objects.filter(package=package)

    template = "package/documents/list_documents.html"
    context = {
        "initiative": package.initiative,
        "package": package,
        "documents": documents,
    }
    return render(
        request,
        template,
        context,
    )


@user_is_initiative_manager
def package_data(request, initiative_id, package_id) -> HttpResponse:
    """
    List the form elements for a package.
    :param request: the request
    :param initiative_id: the initiative ID
    :param package_id: the package ID
    :return: the response
    """
    package = get_object_or_404(models.Package, pk=package_id)

    if request.POST:
        # the user has submitted data
        if "add_new" in request.POST:
            form_element = get_object_or_404(
                models.AggregateFormElement,
                pk=int(request.POST["form_fields"]),
            )

            obj, created = models.PackageFormElement.objects.get_or_create(
                package=package, form_element=form_element
            )
            obj.save()

    form_elements = models.PackageFormElement.objects.filter(
        package=package
    ).order_by("form_element__order")

    form_list_field = forms.FormListField()

    template = "package/form_elements/list_package_form_elements.html"
    context = {
        "initiative": package.initiative,
        "package": package,
        "form_elements": form_elements,
        "field_list": form_list_field,
    }
    return render(
        request,
        template,
        context,
    )


@user_is_initiative_manager
def price_debugger(request) -> HttpResponse:
    """
    Debug the price of a package.
    :param request: the request
    :return: the response
    """
    user = get_user_model()
    user_to_test, package_to_test = None, None

    result = ""

    if request.POST:
        user_to_test = get_object_or_404(user, pk=request.POST.get("user"))
        package_to_test = get_object_or_404(
            models.Package, pk=request.POST.get("package")
        )

        price, val, result = utils.explain_price(
            package_to_test, user_to_test, "user"
        )

    packages = []

    for init in initiative_models.Initiative.objects.all():
        for package in init.packages.all():
            packages.append(package)

    packages = set(packages)
    users = user.objects.all()

    template = "package/debugger.html"
    context = {
        "packages": packages,
        "user_list": users,
        "result": result,
        "user_to_test": user_to_test,
        "package_to_test": package_to_test,
    }
    return render(
        request,
        template,
        context,
    )


@user_is_initiative_manager
def add_document(request, initiative_id, package_id) -> HttpResponse:
    """
    Add a document to a package.
    :param request: the request
    :param initiative_id: the initiative ID
    :param package_id: the package ID
    :return: the response
    """
    package = get_object_or_404(models.Package, pk=package_id)

    if request.POST:
        # Save the new object
        document_form = forms.DocumentUploadForm(
            request.POST, request.FILES, package=package
        )
        if document_form.is_valid():
            document_form.save()
        else:
            print("NO")

        return return_or_elsewhere(request, "dashboard_index")
    else:
        # Present a blank form
        document_form = forms.DocumentUploadForm(package=package)

    template = "package/documents/add_document.html"
    context = {
        "initiative": package.initiative,
        "package": package,
        "form": document_form,
    }
    return render(
        request,
        template,
        context,
    )


@user_is_initiative_manager
def view_document(
    request, package_id, initiative_id, document_id
) -> FileResponse:
    """
    View a document.
    :param request: the request
    :param package_id: the package ID
    :param initiative_id: the initiative ID
    :param document_id: the document ID
    :return: the response
    """

    """
    Send a file through Django in 8KB chunks to avoid memory issues.
    """
    document = get_object_or_404(models.PackageDocument, pk=document_id)

    response = FileResponse(open(document.pdf_file.path, "rb"))
    response["Content-Disposition"] = (
        'attachment; filename="'
        + os.path.basename(document.pdf_file.name)
        + '"'
    )
    response["Content-Length"] = document.pdf_file.size
    return response


@user_is_initiative_manager
def delete_document(
    request, package_id, initiative_id, document_id
) -> HttpResponse:
    """
    Delete a document.
    :param request: the request
    :param package_id: the package ID
    :param initiative_id: the initiative ID
    :param document_id: the document ID
    :return: the response
    """
    if request.POST and "delete" in request.POST:
        instance = get_object_or_404(models.PackageDocument, pk=document_id)

        # determine if this user can delete
        if instance.package.initiative in request.user.Initiatives.all():
            instance.delete()
        else:
            raise PermissionDenied

    return redirect(
        reverse(
            "list_documents",
            kwargs={"package_id": package_id, "initiative_id": initiative_id},
        )
    )


@user_is_initiative_manager
def upload_new_document(
    request, package_id, initiative_id, document_id
) -> HttpResponse:
    """
    Upload a new document.
    :param request: the request
    :param package_id: the package ID
    :param initiative_id: the initiative ID
    :param document_id: the document ID
    :return: the response
    """
    package = get_object_or_404(
        models.Package,
        pk=package_id,
    )
    document = get_object_or_404(
        models.PackageDocument,
        pk=document_id,
        package=package,
        package__initiative__id=initiative_id,
    )
    form = forms.DocumentUploadForm(
        package=package,
        instance=document,
    )

    if request.POST and "upload" in request.POST:
        historical_record = document.create_historical_record()
        form = forms.DocumentUploadForm(
            request.POST,
            request.FILES,
            package=package,
            instance=document,
        )
        if form.is_valid():
            form.save()
            messages.add_message(
                request,
                messages.SUCCESS,
                "Revised document uploaded.",
            )
            return redirect(
                reverse(
                    "list_documents",
                    kwargs={
                        "package_id": package_id,
                        "initiative_id": initiative_id,
                    },
                )
            )
        else:
            historical_record.delete()

    template = "package/documents/add_document.html"
    context = {
        "initiative": document.package.initiative,
        "package": document.package,
        "form": form,
        "revision": True,
    }
    return render(
        request,
        template,
        context,
    )


@user_is_initiative_manager
@require_POST
def revert_document_version(
    request, package_id, initiative_id, document_id
) -> HttpResponse:
    """
    Revert a document to a previous version.
    :param request: the request
    :param package_id: the package ID
    :param initiative_id: the initiative ID
    :param document_id: the document ID
    :return: the response
    """
    package = get_object_or_404(
        models.Package,
        pk=package_id,
    )
    document = get_object_or_404(
        models.PackageDocument,
        pk=document_id,
        package=package,
        package__initiative__id=initiative_id,
    )
    version_id = request.POST.get("version_id", None)
    version = get_object_or_404(
        models.PackageDocumentHistorical,
        pk=version_id,
        package_document=document,
    )
    version.revert()
    messages.add_message(
        request,
        messages.SUCCESS,
        "Document reverted.",
    )
    return redirect(
        reverse(
            "list_documents",
            kwargs={"package_id": package_id, "initiative_id": initiative_id},
        )
    )


@user_is_initiative_manager
def delete_package(request, package_id, initiative_id) -> HttpResponse:
    """
    Delete a package.
    :param request: the request
    :param package_id: the package ID
    :param initiative_id: the initiative ID
    :return: the response
    """
    stored_id = None

    if request.POST and "delete" in request.POST:
        instance = get_object_or_404(models.Package, pk=package_id)

        stored_id = instance.initiative.id

        # determine if this user can delete
        if instance.initiative in request.user.Initiatives.all():
            instance.delete()
        else:
            raise PermissionDenied

    if not stored_id:
        instance = get_object_or_404(models.Package, pk=package_id)
        stored_id = instance.initiative.id

    return redirect(
        reverse("initiative_packages", kwargs={"initiative": stored_id})
    )


@user_is_initiative_manager
@require_POST
def delete_package_banding(
    request, package_id, initiative_id, banding_id
) -> HttpResponse:
    """
    Delete a package banding.
    :param request: the request
    :param package_id: the package ID
    :param initiative_id: the initiative ID
    :param banding_id: the banding ID
    :return: the response
    """
    stored_id = None
    package = None

    if request.POST and "delete" in request.POST:
        instance = get_object_or_404(models.BandingTypeEntry, pk=banding_id)
        package = get_object_or_404(models.Package, pk=package_id)
        stored_id = package.initiative.id

        banding_entries = package.bandingtypecurrencyentry_set.filter(
            banding_type_entry=instance
        )

        for banding_entry in banding_entries:
            # determine if this user can delete
            if package.initiative in request.user.Initiatives.all():
                if package.initiative in request.user.Initiatives.all():
                    # get all the prices for this
                    for (
                        v_banding
                    ) in (
                        banding_entry.banding_type_entry.banding_type.vocabs.all()
                    ):
                        banding = models.Banding.objects.get(
                            package=package,
                            vocab=v_banding,
                            banding_type=banding_entry.banding_type_entry.banding_type,
                        )
                        try:
                            price = models.Price.objects.get(
                                banding=banding,
                                country=banding_entry.country,
                            )

                            print("DELETING {} from {}".format(price, package))
                            price.delete()
                        except models.Price.DoesNotExist:
                            pass
            else:
                raise PermissionDenied

        instance.delete()

    if not stored_id:
        instance = get_object_or_404(models.Package, pk=package_id)
        stored_id = instance.initiative.id

    if not package:
        package = get_object_or_404(models.Package, pk=package_id)

    return redirect(
        reverse(
            "package_bandings",
            kwargs={"initiative_id": stored_id, "package_id": package.pk},
        )
    )


@user_is_initiative_manager
def delete_package_banding_currency(
    request, package_id, initiative_id, banding_id, banding_currency_id
) -> HttpResponse:
    """
    Delete a package banding currency.
    :param request: the request
    :param package_id: the package ID
    :param initiative_id: the initiative ID
    :param banding_id: the banding ID
    :param banding_currency_id: the banding currency ID
    :return: the response
    """
    stored_id = None
    package = None

    if request.POST and "delete" in request.POST:
        instance = get_object_or_404(
            models.BandingTypeCurrencyEntry, pk=banding_currency_id
        )
        package = get_object_or_404(models.Package, pk=package_id)
        stored_id = package.initiative.id
        banding_entry = models.BandingTypeCurrencyEntry.objects.get(
            pk=banding_currency_id
        )

        if package.initiative in request.user.Initiatives.all():
            # get all the prices for this
            for (
                v_banding
            ) in banding_entry.banding_type_entry.banding_type.vocabs.all():
                banding = models.Banding.objects.get(
                    package=package,
                    vocab=v_banding,
                    banding_type=banding_entry.banding_type_entry.banding_type,
                )
                try:
                    price = models.Price.objects.get(
                        banding=banding,
                        country=banding_entry.country,
                    )

                    print("DELETING {} from {}".format(price, package))
                    price.delete()
                except models.Price.DoesNotExist:
                    pass

            instance.delete()
        else:
            raise PermissionDenied

    if not stored_id:
        instance = get_object_or_404(models.Package, pk=package_id)
        stored_id = instance.initiative.id

    if not package:
        package = get_object_or_404(models.Package, pk=package_id)

    return redirect(
        reverse(
            "manage_package_banding_currencies",
            kwargs={
                "initiative_id": stored_id,
                "package_id": package.pk,
                "banding_id": banding_id,
            },
        )
    )


@user_is_initiative_manager
def manage_package_bandings(
    request, package_id, initiative_id
) -> HttpResponse:
    """
    Manage the bandings for a package.
    :param request: the request
    :param package_id: the package ID
    :param initiative_id: the initiative ID
    :return: the response
    """
    package = get_object_or_404(models.Package, pk=package_id)

    if request.POST:
        # the user has submitted data
        if "add_new" in request.POST:
            banding_type = get_object_or_404(
                models.BandingType, pk=int(request.POST["bandings"])
            )
            obj, created = models.BandingTypeEntry.objects.get_or_create(
                package=package, banding_type=banding_type
            )
            obj.save()

    prices = models.Price.objects.all()

    has_default = False

    for price in prices:
        if price.country == package.default_country:
            has_default = True
            break

    template = "package/banding/package_banding.html"
    context = {
        "package": package,
        "initiative": package.initiative,
        "bandings": package.bandingtypeentry_set.all().order_by(
            "banding_type__name"
        ),
        "bandings_list": forms.BandingTypeField(),
        "has_default": has_default,
    }
    return render(
        request,
        template,
        context,
    )


@user_is_initiative_manager
def edit_redirect_for_banding(
    request, package_id, initiative_id, banding_id
) -> HttpResponse:
    """
    Edit the redirect for a banding.
    :param request: the request
    :param package_id: the package ID
    :param initiative_id: the initiative ID
    :param banding_id: the banding ID
    :return: the response
    """
    package = get_object_or_404(models.Package, pk=package_id)
    banding_te = get_object_or_404(models.BandingTypeEntry, pk=banding_id)

    form = forms.BandingTypeEntryRedirectForm(instance=banding_te)

    if request.POST:
        form = forms.BandingTypeEntryRedirectForm(
            request.POST, instance=banding_te
        )

        if form.is_valid():
            form.save()

        return redirect(
            reverse(
                "package_bandings",
                kwargs={
                    "package_id": package.pk,
                    "initiative_id": initiative_id,
                },
            )
        )

    template = "package/banding/redirect.html"
    context = {
        "form": form,
        "package": package,
        "banding": banding_te,
        "initiative": package.initiative,
        "banding_type_entry": banding_te,
    }
    return render(
        request,
        template,
        context,
    )


@user_is_initiative_manager
def manage_package_banding_currencies(
    request, package_id, initiative_id, banding_id
) -> HttpResponse:
    """
    Manage the currencies for a package banding.
    :param request: the request
    :param package_id: the package ID
    :param initiative_id: the initiative ID
    :param banding_id: the banding ID
    :return: the response
    """
    package = get_object_or_404(models.Package, pk=package_id)
    banding = get_object_or_404(models.BandingTypeEntry, pk=banding_id)

    if request.POST:
        # the user has submitted data
        if "add_new" in request.POST:
            country_type = get_object_or_404(
                models.Country, pk=int(request.POST["currencies"])
            )
            (
                obj,
                created,
            ) = models.BandingTypeCurrencyEntry.objects.get_or_create(
                package=package,
                banding_type_entry=banding,
                country=country_type,
            )
            obj.save()
        elif "payment_processor" in request.POST:
            processor_id = request.POST.get("select_payment_processor", None)
            banding_currency_id = request.POST.get("payment_processor", None)
            processor = invoicing_models.PaymentProcessor.objects.filter(
                pk=processor_id
            ).first()
            banding_currency = models.BandingTypeCurrencyEntry.objects.filter(
                banding_type_entry=banding,
                pk=banding_currency_id,
            ).first()

            if not processor:
                messages.add_message(
                    request,
                    messages.WARNING,
                    "No payment processor found for that ID.",
                )
            else:
                banding_currency.payment_processor = processor
                banding_currency.save()
                messages.add_message(
                    request,
                    messages.SUCCESS,
                    "Payment processor saved.",
                )

            return redirect(
                reverse(
                    "manage_package_banding_currencies",
                    kwargs={
                        "package_id": package.pk,
                        "initiative_id": initiative_id,
                        "banding_id": banding.pk,
                    },
                )
            )

    country_list = forms.CurrencyField()

    currencies = models.BandingTypeCurrencyEntry.objects.filter(
        banding_type_entry=banding
    ).order_by("country")

    template = "package/banding/package_banding_currency.html"
    context = {
        "package": package,
        "initiative": package.initiative,
        "banding_type_currencies": currencies,
        "country_list": country_list,
        "banding_type_entry": banding,
    }
    return render(
        request,
        template,
        context,
    )


@user_is_initiative_manager
def manage_package_banding_currencies_prices(
    request, package_id, initiative_id, banding_id, currency_id
) -> HttpResponse:
    """
    Manage the prices for a package banding currency.
    :param request: the request
    :param package_id: the package ID
    :param initiative_id: the initiative ID
    :param banding_id: the banding ID
    :param currency_id: the currency ID
    :return: the response
    """
    package = get_object_or_404(models.Package, pk=package_id)
    banding = get_object_or_404(models.BandingTypeEntry, pk=banding_id)
    currency = get_object_or_404(
        models.BandingTypeCurrencyEntry, pk=currency_id
    )

    if request.POST:
        form = forms.ManagePackageCurrencyForm(
            request.POST,
            initiative_id=initiative_id,
            package_id=package_id,
            banding_type=banding.banding_type,
            currency=currency,
        )

        if form.is_valid:
            form.save()

            return redirect(
                reverse(
                    "manage_package_banding_currencies",
                    kwargs={
                        "package_id": package.pk,
                        "initiative_id": initiative_id,
                        "banding_id": banding_id,
                    },
                )
            )
    else:
        form = forms.ManagePackageCurrencyForm(
            initiative_id=initiative_id,
            package_id=package_id,
            banding_type=banding.banding_type,
            currency=currency,
        )

    template = "package/banding/package_banding_currency_prices.html"
    context = {
        "package": package,
        "initiative": package.initiative,
        "currency": currency,
        "banding_type_entry": banding,
        "form": form,
    }
    return render(
        request,
        template,
        context,
    )


def download_order_document(request, order_id) -> FileResponse:
    """
    Download a document for an order.
    :param request: the request
    :param order_id: the order ID
    :return: the response
    """
    if request.user.is_authenticated:
        order = get_object_or_404(
            models.Order,
            pk=order_id,
            associated_user=request.user,
        )
    else:
        order = get_object_or_404(
            models.Order,
            pk=order_id,
            session_id=request.session.session_key,
        )

    identifier = (
        request.user if request.user.is_authenticated else request.session
    )
    identifier_type = "user" if request.user.is_authenticated else "session"

    if request.GET.get("document_type") == "acceptance":
        save_path, filename = utils.generate_acceptance_doc(
            request,
            order,
            identifier,
            identifier_type,
        )
    else:
        save_path, filename = utils.generate_doc(
            request, order, identifier, identifier_type
        )

    # Serve it!
    response = FileResponse(open(save_path, "rb"))
    response["Content-Disposition"] = 'attachment; filename="{}"'.format(
        filename
    )
    os.unlink(save_path)
    return response


def new_order_complete(request, order_id) -> HttpResponse:
    """
    Show the new order complete page.
    :param request: the request
    :param order_id: the order ID
    :return: the response
    """
    if request.user.is_authenticated:
        order = get_object_or_404(
            models.Order,
            pk=order_id,
            associated_user=request.user,
        )
    else:
        order = get_object_or_404(
            models.Order,
            pk=order_id,
            session_id=request.session.session_key,
        )

    template = "package/checkout/new_order_complete.html"
    context = {
        "order": order,
    }
    return render(
        request,
        template,
        context,
    )


def change_session_country(request):
    if request.POST and "country" in request.POST:
        country_id = request.POST.get("country")
        try:
            country = models.Country.objects.get(pk=country_id)
            request.session["country"] = country.code
        except models.Country.DoesNotExist:
            pass
        return redirect(request.POST.get("next"))
