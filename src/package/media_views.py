from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import reverse, get_object_or_404, redirect, render

from intrepid.security import user_is_initiative_manager
from package import models, forms


@user_is_initiative_manager
def list_media_files(request, package_id, initiative_id) -> HttpResponse:
    """
    List all media files for a package.
    :param request: the request object
    :param package_id: the package id
    :param initiative_id: the initiative id
    :return: the response object
    """
    package = get_object_or_404(
        models.Package,
        pk=package_id,
        initiative__pk=initiative_id,
    )
    media_files = models.MediaFile.objects.filter(
        package=package,
    )
    new_file_form = forms.MediaFileForm(
        package=package,
    )
    if request.POST:
        if "upload" in request.POST:
            new_file_form = forms.MediaFileForm(
                request.POST,
                request.FILES,
                package=package,
            )
            if new_file_form.is_valid():
                new_file = new_file_form.save()
                messages.add_message(
                    request,
                    messages.SUCCESS,
                    "Media File {} loaded.".format(new_file.name),
                )

        elif "delete" in request.POST:
            id_to_delete = request.POST.get("delete")
            media_file_to_delete = get_object_or_404(
                models.MediaFile,
                pk=id_to_delete,
                package=package,
            )
            media_file_to_delete.unlink_file()
            media_file_to_delete.delete()
            messages.add_message(
                request,
                messages.ERROR,
                "Media File Deleted",
            )

        return redirect(
            reverse(
                "media_files",
                kwargs={
                    "initiative_id": initiative_id,
                    "package_id": package.pk,
                },
            )
        )

    template = "package/media/list_media_files.html"
    context = {
        "package": package,
        "media_files": media_files,
        "new_file_form": new_file_form,
    }
    return render(request, template, context)


@login_required
def download_media_file(
    request, package_id, initiative_id, file_id
) -> HttpResponse:
    """
    Download a media file.
    :param request: the request object
    :param package_id: the package id
    :param initiative_id: the initiative id
    :param file_id: the file id
    :return: the response object
    """
    package = get_object_or_404(
        models.Package,
        pk=package_id,
        initiative__pk=initiative_id,
    )

    # Find out if this user has subscribed to this package.
    packages = [
        signup.associated_package
        for signup in request.user.packagesignup_set.filter(
            associated_order__status="complete",
        )
    ]

    if package not in packages:
        raise Http404("Package not found in your subscriber list.")

    try:
        file = package.mediafile_set.get(pk=file_id)
    except Exception:
        raise Http404("File Not Found.")

    return file.serve_file()
