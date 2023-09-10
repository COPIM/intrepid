from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect, reverse
from django.views.decorators.http import require_POST
from fluid_permissions.decorators import user_in_authorised_group

from intrepid.utils import return_or_elsewhere
from vocab import models, forms, utils


@user_in_authorised_group
def vocab_list(request) -> HttpResponse:
    """
    List all the vocab items in the system
    :param request: the request object
    :return: the response object
    """
    vocabs = models.BandingVocab.objects.all()

    if request.POST:
        ids = request.POST.getlist("banding_vocabs[]")
        ids = [int(_id) for _id in ids]

        for bv in models.BandingVocab.objects.all():
            bv.order = ids.index(bv.pk)
            bv.save()

        return HttpResponse("Thanks")

    template = "vocab/list.html"

    context = {
        "vocabs": vocabs,
        "sort_url": reverse("vocab_list"),
    }
    return render(
        request,
        template,
        context,
    )


@user_in_authorised_group
@require_POST
def vocab_delete(request, vocab_id) -> HttpResponse:
    """
    Delete a vocab item
    :param request: the request object
    :param vocab_id: the id of the vocab item to delete
    :return: the response object
    """
    if request.POST and "delete" in request.POST:
        instance = get_object_or_404(models.BandingVocab, pk=vocab_id)
        instance.delete()

    return redirect(reverse("vocab_list"))


@user_in_authorised_group
def vocab_new(request, vocab_to_edit=None) -> HttpResponse:
    """
    Create a new vocab item
    :param request: the request object
    :param vocab_to_edit: the id of the vocab item to edit
    :return: the response object
    """
    if vocab_to_edit:
        vocab = get_object_or_404(models.BandingVocab, pk=vocab_to_edit)

        if request.POST:
            # Save an existing object
            vocab_form = forms.NewVocabForm(request.POST, instance=vocab)
            vocab_form.save()

            return return_or_elsewhere(request, "dashboard_index")
        else:
            # Edit an existing object
            vocab_form = forms.NewVocabForm(instance=vocab)
    else:
        if request.POST:
            # Save a new object
            vocab_form = forms.NewVocabForm(request.POST)
            vocab_form.save()

            return return_or_elsewhere(request, "dashboard_index")
        else:
            # Edit a new object
            vocab_form = forms.NewVocabForm()

    template = "vocab/new_edit.html"

    context = {
        "form": vocab_form,
    }
    return render(
        request,
        template,
        context,
    )


@staff_member_required
def standards_vocab_list(request) -> HttpResponse:
    """
    List all the standards vocab items in the system
    :param request: the request object
    :return: the response object
    """
    vocabs = models.StandardVocab.objects.all()

    template = "vocab/standards_list.html"

    context = {
        "vocabs": vocabs,
    }
    return render(
        request,
        template,
        context,
    )


@staff_member_required
def standard_new(request, vocab_to_edit=None) -> HttpResponse:
    """
    Create a new standard vocab item
    :param request: the request object
    :param vocab_to_edit: the id of the vocab item to edit
    :return: the response object
    """
    if vocab_to_edit:
        vocab = get_object_or_404(models.StandardVocab, pk=vocab_to_edit)

        if request.POST:
            # Save an existing object
            vocab_form = forms.NewStandardForm(request.POST, instance=vocab)
            if vocab_form.is_valid():
                vocab_form.save()
                return return_or_elsewhere(request, "dashboard_index")
        else:
            # Edit an existing object
            vocab_form = forms.NewStandardForm(instance=vocab)
    else:
        if request.POST:
            # Save a new object
            vocab_form = forms.NewStandardForm(request.POST)
            if vocab_form.is_valid():
                save = vocab_form.save()
                utils.notify_initiatives_new_standards(
                    standard=save,
                    request=request,
                )
                return return_or_elsewhere(request, "dashboard_index")
        else:
            # Edit a new object
            vocab_form = forms.NewStandardForm()

    template = "vocab/new_edit_standard.html"

    context = {
        "form": vocab_form,
    }
    return render(
        request,
        template,
        context,
    )


@staff_member_required
@require_POST
def standard_delete(request, vocab_id) -> HttpResponse:
    """
    Delete a standard vocab item
    :param request: the request object
    :param vocab_id: the id of the vocab item to delete
    :return: the response object
    """
    if request.POST and "delete" in request.POST:
        instance = get_object_or_404(models.StandardVocab, pk=vocab_id)
        instance.delete()

    return redirect(reverse("standards_vocab_list"))


@staff_member_required
def subjects(request) -> HttpResponse:
    """
    List all the subjects in the system
    :param request: the request object
    :return: the response object
    """
    subject_objects = models.SubjectVocab.objects.all()

    if request.POST:
        if "delete" in request.POST:
            id_to_delete = request.POST.get("delete")
            get_object_or_404(
                models.SubjectVocab,
                pk=id_to_delete,
            ).delete()
            messages.add_message(
                request,
                messages.SUCCESS,
                "Subject deleted",
            )

    template = "vocab/subjects.html"
    context = {
        "subjects": subject_objects,
    }
    return render(
        request,
        template,
        context,
    )


@staff_member_required
def new_edit_subject(request, subject_id=None) -> HttpResponse:
    """
    Create or edit a subject
    :param request: the request object
    :param subject_id: the id of the subject to edit
    :return: the response object
    """
    subject = None
    if subject_id:
        subject = get_object_or_404(
            models.SubjectVocab,
            pk=subject_id,
        )

    form = forms.SubjectForm(
        instance=subject,
    )
    if request.POST:
        form = forms.SubjectForm(
            request.POST,
            instance=subject,
        )
        if form.is_valid():
            form.save()
            return redirect(
                reverse(
                    "subjects",
                )
            )
    template = "vocab/new_edit_subjects.html"
    context = {
        "subject": subject,
        "form": form,
    }
    return render(
        request,
        template,
        context,
    )
