from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from django.shortcuts import reverse, render, get_object_or_404, redirect
from django.views.decorators.http import require_POST

from package import models, forms
from vocab import models as vm


@staff_member_required
def banding_type_list(request) -> HttpResponse:
    """
    Allows a staff member to view a list of banding types.
    :param request: the request object
    :return: the response object
    """

    template = "package/banding/type_list.html"
    context = {
        "banding_types": models.BandingType.objects.all().prefetch_related(
            "vocabs",
        ),
    }
    return render(
        request,
        template,
        context,
    )


@staff_member_required
def banding_type_create(request) -> HttpResponse:
    """
    Allows a staff member to create a new banding type.
    :param request: the request object
    :return: the response object
    """

    form = forms.BandingTypeForm()

    if request.POST:
        form = forms.BandingTypeForm(
            request.POST,
        )
        if form.is_valid():
            banding_type = form.save()
            messages.add_message(
                request,
                messages.SUCCESS,
                "New Banding Type created.",
            )
            return redirect(
                reverse(
                    "package_banding_type_vocabs",
                    kwargs={
                        "banding_type_id": banding_type.pk,
                    },
                )
            )

    template = "package/banding/create.html"
    context = {
        "form": form,
    }
    return render(
        request,
        template,
        context,
    )


@staff_member_required
def banding_type_vocabs(request, banding_type_id) -> HttpResponse:
    """
    Allows a staff member to manage the vocabs for a banding type.
    :param request: the request object
    :param banding_type_id: the banding type id
    :return: the response object
    """

    banding_type = get_object_or_404(
        models.BandingType,
        pk=banding_type_id,
    )
    vocabs = vm.BandingVocab.objects.all()

    if request.POST:
        vocab_ids = request.POST.getlist("vocab")
        banding_type.set_vocabs(vocab_ids, request)

        # run garbage collection
        models.Price.collect()

        return redirect(reverse("package_banding_type_list"))

    template = "package/banding/vocabs.html"
    context = {
        "banding_type": banding_type,
        "vocabs": vocabs,
    }
    return render(
        request,
        template,
        context,
    )


@staff_member_required
def banding_type_edit(request, banding_type_id) -> HttpResponse:
    """
    Allows a staff member to edit an existing banding type. NOTE: Unimplemented.
    :param request: the request object
    :param banding_type_id: the banding type id
    :return: the response object
    """
    # TODO: implement this
    ...


@require_POST
@staff_member_required
def banding_type_delete(request, banding_type_id):
    """
    Allows a staff member to delete a banding type. NOTE: Unimplemented.
    :param request: the request object
    :param banding_type_id: the banding type id
    :return: the response object
    """
    """
    Allows a staff member to delete a banding type.
    """
    # TODO: implement this
    ...


@require_POST
@staff_member_required
def banding_type_order(request):
    """
    Allows a staff member to order banding types. NOTE: Unimplemented.
    :param request: the request object
    :return: the response object
    """
    # TODO: implement this
    ...
