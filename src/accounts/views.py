from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.shortcuts import render, reverse, redirect, get_object_or_404
from django_otp.decorators import otp_required
from fluid_permissions import decorators, models
from two_factor.utils import default_device

from accounts import forms, utils
from accounts import models as accounts_models
from mail import models as mail_models
from package import models as package_models
from vocab import models as vocab_models


def login(request):
    """
    Redirects to the two_factor login page.
    :param request: HttpRequest
    :return: HttpRedirect
    """
    return redirect(reverse("two_factor:login"))


@login_required
def profile(request):
    """
    Allows a user to edit their profile.
    :param request: HttpRequest
    :return: HttpResponse
    """
    template = "accounts/profile.html"
    context = {
        "user": request.user,
        "default_device": default_device(request.user),
    }
    return render(request, template, context)


@login_required
def manage_account_bandings(request):
    """
    Allows a user to edit their profile.
    :param request: HttpRequest
    :return: HttpResponse
    """

    if request.POST:
        # delete all existing entries
        accounts_models.AccountBandingChoices.objects.filter(
            account=request.user
        ).delete()

        for val in request.POST:
            if val.startswith("banding"):
                if int(request.POST[val]) != 0:
                    banding_type = package_models.BandingType.objects.get(
                        pk=int(val.split("-")[1])
                    )

                    vocab = vocab_models.BandingVocab.objects.get(
                        pk=int(request.POST[val])
                    )

                    acc_band_choices = accounts_models.AccountBandingChoices

                    acc_band_choices.objects.update_or_create(
                        banding_type=banding_type,
                        account=request.user,
                        defaults={
                            "banding_type_vocab": vocab,
                        },
                    )

        return redirect("profile")

    template = "accounts/banding_setup.html"
    context = {
        "user": request.user,
        "default_device": default_device(request.user),
        "banding_types": package_models.BandingType.objects.filter(
            is_fte=False
        ).prefetch_related(
            "vocabs",
        ),
    }
    return render(request, template, context)


@login_required
def edit_profile(request):
    """
    Allows a user to edit their profile.
    :param request: HttpRequest
    :return: HttpResponse
    """
    template = "accounts/edit_profile.html"

    profile_object = accounts_models.Profile.objects.get(account=request.user)

    form = forms.ProfileForm(
        instance=profile_object, ror=profile_object.institution
    )

    user_form = forms.UserFormNoPassword(instance=request.user)

    if request.POST:
        if request.POST["inst_lookup"] == "":
            # the user has blanked the lookup box
            ror = ""
        elif request.POST["institution_ROR"] == "":
            # the user has left the lookup box as it was
            try:
                ror = profile_object.institution.ror_id
            except AttributeError:
                ror = ""
        else:
            # a new ROR has been submitted
            ror = request.POST["institution_ROR"]

        form = forms.ProfileForm(
            request.POST, request.FILES, instance=profile_object, ror=ror
        )
        user_form = forms.UserFormNoPassword(
            request.POST, request.FILES, instance=request.user
        )

        if form.is_valid():
            form.save()

        if user_form.is_valid():
            user_form.save()
        else:
            print(user_form.errors)

        return redirect(reverse("profile"))

    inst_name = ""

    ror = ""

    if profile_object and profile_object.institution:
        inst_name = profile_object.institution.institution_name
        try:
            ror = profile_object.institution.ror_id
        except AttributeError:
            pass

    context = {
        "user": request.user,
        "default_device": default_device(request.user),
        "form": form,
        "user_form": user_form,
        "initial_value": inst_name,
        "initial_ror": ror,
    }
    return render(request, template, context)


@otp_required
@decorators.user_in_authorised_group
def manage_accounts(request):
    """
    Allows a user to manage accounts on the platform.
    :param request: HttpRequest
    :return: HttpResponse
    """
    accounts = User.objects.all()
    template = "accounts/manage_accounts.html"
    context = {
        "accounts": accounts,
    }
    return render(request, template, context)


@otp_required
@staff_member_required
def manage_fluid_permissions(request):
    view_groups = models.ViewGroup.objects.all().order_by("view_name")
    groups = Group.objects.all()

    if request.POST:
        utils.process_permission_change(request)

    template = "accounts/manage_fluid_permissions.html"
    context = {
        "view_groups": view_groups,
        "groups": groups,
    }
    return render(
        request,
        template,
        context,
    )


def register(request):
    form = forms.UserForm()
    if request.POST:
        form = forms.UserForm(
            request.POST,
        )
        email = request.POST.get("email")
        if (
            email
            and User.objects.filter(
                email=email,
            ).exists()
        ):
            form.add_error(
                "email", "Account with this email address already exists."
            )

        if form.is_valid():
            user = form.save()
            accounts_models.Profile.objects.get_or_create(account=user)
            email_template = mail_models.EmailTemplate.objects.get(
                name="registration"
            )
            url = request.build_absolute_uri(
                reverse(
                    "activate",
                    kwargs={
                        "activation_code": str(user.profile.activation_code)
                    },
                )
            )
            email_template.send(
                to=user.email,
                subject="New Account",
                context={
                    "user": user,
                    "request": request,
                    "url": url,
                },
            )
            messages.add_message(
                request,
                messages.INFO,
                "Check your email for an activation link.",
            )
            return redirect(reverse("two_factor:login"))

    template = "accounts/register.html"
    context = {
        "form": form,
    }
    return render(
        request,
        template,
        context,
    )


def activate(request, activation_code):
    profile_object = get_object_or_404(
        accounts_models.Profile,
        activation_code=activation_code,
        account__is_active=False,
    )

    if request.POST:
        profile_object.account.is_active = True
        profile_object.account.save()
        profile_object.activation_code = ""
        profile_object.save()

        return redirect(
            reverse(
                "two_factor:login",
            )
        )
    template = "accounts/activate.html"
    context = {
        "profile": profile_object,
    }
    return render(
        request,
        template,
        context,
    )
