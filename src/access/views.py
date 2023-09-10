from django.contrib.auth.decorators import login_required
from django.shortcuts import (
    render,
    get_object_or_404,
    redirect,
    reverse,
)
from django.contrib import messages
from django.views.decorators.http import require_POST


from access import models, forms


def contact_list(request):
    # the middleware gives us request.initiatives for initiatives owned
    # by the logged-in user
    contacts = models.Contact.objects.filter(initiative__in=request.initiatives)

    template = "contacts/contact_list.html"
    context = {
        "contacts": contacts,
    }
    return render(
        request,
        template,
        context,
    )


@login_required
def create_contact(request, contact_id=None):
    if contact_id:
        contact = get_object_or_404(
            models.Contact, pk=contact_id, initiative__in=request.initiatives
        )

        form = forms.ContactForm(
            request=request,
            instance=contact,
        )
    else:
        form = forms.ContactForm(request=request)
        contact = None

    if request.POST:
        form = (
            forms.ContactForm(
                request.POST,
                request=request,
                instance=contact,
            )
            if contact_id
            else forms.ContactForm(
                request.POST,
                request=request,
            )
        )

        if form.is_valid():
            form.save()
            messages.add_message(
                request,
                messages.SUCCESS,
                "Contact Information Saved.",
            )
            return redirect(reverse("contact_list"))
    template = "contacts/create_contact.html"
    context = {
        "form": form,
    }
    return render(request, template, context)


@login_required
@require_POST
def delete_contact(request, contact_id):
    get_object_or_404(
        models.Contact, pk=contact_id, initiative__in=request.initiatives
    ).delete()

    return redirect(reverse("contact_list"))
