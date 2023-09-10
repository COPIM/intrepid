import os
from wsgiref.util import FileWrapper

from django.http import (
    HttpResponseRedirect,
    HttpResponsePermanentRedirect,
    HttpResponse,
)
from django.shortcuts import (
    redirect,
    reverse,
)
from django.utils.cache import patch_cache_control


def return_or_elsewhere(
    request, return_page
) -> HttpResponseRedirect | HttpResponsePermanentRedirect:
    """
    Determine whether to return to a page or go to a default page.
    :param request: a request object
    :param return_page: the default page to return to
    :return: an HttpResponseRedirect object
    """
    if "return" in request.GET:
        return redirect(request.GET["return"])
    else:
        return redirect(reverse(return_page))


def serve_file(path, filename, mime) -> HttpResponse:
    """
    Serve a file
    :param path: the path
    :param filename: the filename
    :param mime: the mime type
    :return: HttpResponse
    """

    response = HttpResponse(
        FileWrapper(open(path, "rb"), 8192),
        content_type=mime,
    )

    response["Content-Length"] = os.path.getsize(path)

    response["Content-Disposition"] = 'attachment; filename="{0}"'.format(
        filename
    )

    patch_cache_control(response, max_age=600)

    return response
