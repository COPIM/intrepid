import collections
import os

import pycountry
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Sum
from django.http import FileResponse, HttpResponse
from django.shortcuts import (
    render,
    get_object_or_404,
    redirect,
    reverse,
)
from fluid_permissions import decorators

from accounts import models as acc_models
from initiatives import models as init_models
from intrepid import forms as intrepid_forms
from intrepid import models as intrepid_models
from package import models as package_models
from thoth import models as thoth_models
from thoth.models import CountryStat, Institution, Funding, Contribution


def visitor_dict(stats) -> dict:
    """
    Convert the visitor stats to a dictionary
    :param stats: the stats
    :return: a dictionary of stats
    """
    ret = {}

    for stat in stats:
        # convert from ISO 3166-1 alpha-3 to ISO 3166-1 alpha-2
        if len(stat.country_code) == 3:
            country = pycountry.countries.get(alpha_3=stat.country_code)
            ret[country.alpha_2.lower()] = stat.country_count
        else:
            ret[stat.country_code.lower()] = stat.country_count

    return ret


@login_required()
def index(request) -> HttpResponse:
    """
    The dashboard index
    :param request: the request object
    :return: an HTTP response
    """
    template = "dashboard/dashboard_index.html"

    books = thoth_models.Work.objects.all()
    book_count = books.count()

    # this catches instances where a user doesn't have a profile
    try:
        profile = request.user.profile
        profile.save()

    except acc_models.Profile.DoesNotExist:
        request.user.profile = acc_models.Profile()
        request.user.profile.save()
        request.user.save()

    if request.user.profile.institution:
        institutions = Institution.objects.filter(
            ror=request.user.profile.institution.ror_id
        )

        fundings = Funding.objects.filter(institution__in=institutions)

        contributions = Contribution.objects.filter(
            institutions__in=institutions
        )

        institution_books = fundings.count() + contributions.count()
    else:
        institution_books = "Unknown"

    labels, publisher_count, publisher_templates = generate_graph(books)

    visitors_data = visitor_dict(CountryStat.objects.all())

    index_count = init_models.Initiative.objects.aggregate(Sum("indexed_books"))

    context = {
        "book_count": book_count,
        "pub_count": publisher_count,
        "graph_data": publisher_templates,
        "labels": labels,
        "visitors_data": visitors_data,
        "institution_books": institution_books,
        "index_count": index_count["indexed_books__sum"],
    }

    return render(
        request,
        template,
        context,
    )


@login_required()
def documents(request) -> HttpResponse:
    """
    The document centre dashboard
    :param request: the request object
    :return: a rendered response
    """
    template = "dashboard/document_centre.html"

    orders = package_models.Order.objects.filter(
        associated_user=request.user
    ).order_by("-order_date")

    context = {
        "orders": orders,
    }

    return render(
        request,
        template,
        context,
    )


def frozen_document(request, document_id) -> FileResponse:
    """
    View a frozen document, piping it through Django in 8KB chunks to avoid
    memory issues.
    :param request: the request object
    :param document_id: the document ID
    :return: A FileResponse
    """
    document = get_object_or_404(
        package_models.FrozenPackageDocument, pk=document_id
    )

    if (document.associated_user != request.user) and (
        document.associated_session != request.session.session_key
    ):
        raise PermissionDenied()

    response = FileResponse(open(document.final_zip.path, "rb"))
    response["Content-Disposition"] = (
        'attachment; filename="'
        + os.path.basename(document.final_zip.name)
        + '"'
    )
    response["Content-Length"] = document.final_zip.size
    return response


@decorators.user_in_authorised_group
def setup(request) -> HttpResponse:
    """
    The site setup page
    :param request: the request object
    :return: an HTTP response
    """
    try:
        instance = intrepid_models.SiteSetup.objects.all().order_by("pk")[0]
    except IndexError:
        instance = intrepid_models.SiteSetup()
        instance.save()

    form = intrepid_forms.SiteSetupForm(instance=instance)

    if request.POST:
        form = intrepid_forms.SiteSetupForm(request.POST, instance=instance)

        if form.is_valid():
            form.save()
            messages.add_message(
                request,
                messages.SUCCESS,
                "Site Setup Information Saved.",
            )
            return redirect(reverse("dashboard_index"))

    template = "dashboard/dashboard_setup.html"
    context = {
        "form": form,
    }

    return render(
        request,
        template,
        context,
    )


def generate_graph(books):
    """
    Generate the graph of books published on the homepage
    :param books: the book objects
    :return: Labels, publisher counts, and template lists
    """
    # a list of colours to loop through for the books published
    colours = [
        "rgba(210, 0, 0, 1)",
        "rgba(0, 0, 0, 1)",
        "rgba(210, 214, 222, 1)",
    ]

    # see if we have any stats in the DB
    stats = thoth_models.Stats.objects.all().order_by("year")

    # variable initialization
    publishers = {}
    years = []
    publisher_templates = []
    indexer = 0
    publisher_count = 0
    final_publishers = {}

    for stat in stats:
        # create the years list
        if stat.year not in years:
            years.append(stat.year)

        # add the publisher to the publishers list
        if stat.publisher not in publishers:
            publishers[stat.publisher] = []

        # add the data to a list
        publishers[stat.publisher].append(stat.book_count)

        # count publishers
        publisher_count = len(publishers)

        # sort the publishers
        final_publishers = collections.OrderedDict(sorted(publishers.items()))

    # produce the JS templates
    for k, v in final_publishers.items():
        # reset the colour indexer if it's too high
        if indexer > len(colours) - 1:
            indexer = 0

        # create a json template for this publisher
        pub_template = create_js_template(colours[indexer], k, v)

        # add the publisher template to the list
        publisher_templates.append(pub_template)

        indexer = indexer + 1

    # return labels and values to the dashboard
    labels = sorted(years)[:-1]
    return labels, publisher_count, publisher_templates


def create_js_template(color, publisher_name, publisher_data):
    """
    Produces a custom JS template for the graphing system in the dashboard
    :param color: the color to use (a string of type 'rgba(210, 0, 0, 1)')
    :param publisher_name: the name of the publisher
    :param publisher_data: the data list to use
    :return: a dictionary of values for json_script
    """
    pub_template = {
        "label": publisher_name.publisher_name,
        "backgroundColor": color,
        "borderColor": "rgba(210, 214, 222, 1)",
        "pointRadius": False,
        "pointColor": "rgba(210, 214, 222, 1)",
        "pointStrokeColor": "#c1c7d1",
        "pointHighlightFill": "#fff",
        "pointHighlightStroke": "rgba(220,220,220,1)",
        "data": publisher_data,
    }
    return pub_template
