import shlex
import threading
from datetime import datetime
from typing import Any

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import QuerySet
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_POST

from cms import models as cms_models
from initiatives import models as init_models
from thoth import models
from thoth.management.commands import test_thoth, sync_thoth
from thoth.utils import json_response


def book(request, book_id) -> HttpResponse:
    """
    Display a single book
    :param request: the request object
    :param book_id: the book id
    :return: the response
    """
    book_model = get_object_or_404(models.Work, pk=book_id)

    # get associated packages
    try:
        initiative = init_models.Initiative.objects.get(
            thoth_id=book_model.publisher.thoth_id
        )
        packages = initiative.packages.order_by("name")
    except init_models.Initiative.DoesNotExist:
        initiative = None
        packages = None

    template = "thoth/book.html"

    context = {
        "book": book_model,
        "subjects": book_model.subject_set.all(),
        "packages": packages,
    }
    return render(
        request,
        template,
        context,
    )


@login_required
def saved_searches(request) -> HttpResponse:
    """
    Display a list of saved searches
    :param request: the request object
    :return: the response
    """
    searches = models.ThothSearch.objects.filter(user=request.user)

    book_results = []

    for search in searches:
        elements = models.ThothSearchElement.objects.filter(search=search)
        elements = list(elements)

        works = search.results(elements=elements).order_by("-published_date")

        for work in works:
            book_results.append(work)

    book_results = set(book_results)

    sort = sorted(book_results, key=lambda x: x.published_date, reverse=True)

    if request.user.profile.institution:
        int_updates = cms_models.PageUpdate.objects.filter(
            target_institution=request.user.profile.institution
        ).order_by("-created")
    else:
        int_updates = None

    template = "thoth/thoth_searches.html"
    context = {
        "searches": searches,
        "works": sort,
        "institutional_updates": int_updates,
    }

    return render(
        request,
        template,
        context,
    )


@login_required
@require_POST
def delete_search(request, search_id) -> HttpResponse:
    """
    Delete a saved search
    :param request: the request object
    :param search_id: the search id
    :return: the response
    """
    get_object_or_404(
        models.ThothSearch, pk=search_id, user=request.user
    ).delete()

    return redirect(reverse("saved_searches"))


@login_required
@require_POST
def run_search(request, search_id) -> HttpResponse:
    """
    Run a saved search
    :param request: the request object
    :param search_id: the search id
    :return: the response
    """
    search = get_object_or_404(
        models.ThothSearch, pk=search_id, user=request.user
    )

    request.session["new_search"] = search.pk

    return redirect(reverse("advanced_search"))


@login_required
@require_POST
def toggle_email(request, search_id) -> HttpResponse:
    """
    Toggle email on new result
    :param request: the request object
    :param search_id: the search id
    :return: the response
    """
    search = get_object_or_404(
        models.ThothSearch, pk=search_id, user=request.user
    )

    search.email_on_new = not search.email_on_new
    search.save()

    return redirect(reverse("saved_searches"))


@staff_member_required
def driver(request) -> HttpResponse:
    """
    Run the Thoth driver
    :param request: the request object
    :return: the response
    """
    test = not request.GET.get("test", None)

    thoth_result = None

    if request.POST:
        if "test" in request.POST:
            thoth_tester = test_thoth.Command()
            thoth_result = thoth_tester.test_thoth()

            if thoth_result:
                test = False

        elif "import" in request.POST:
            test = False
            print("Running import. Please check back here in 15 minutes or so.")
            thoth_result = "Background import process has been started..."

            thoth_driver = sync_thoth.Command()

            t = threading.Thread(target=thoth_driver.sync_thoth)
            t.daemon = True
            t.start()
        elif "notify" in request.POST:
            models.WorkNotification.notify()

    template = "thoth/thoth_sync.html"
    context = {"test": test, "result": thoth_result}

    return render(
        request,
        template,
        context,
    )


def books_by_ror(request, ror_id) -> HttpResponse:
    """
    Display a list of books by ROR ID
    :param request: the request object
    :param ror_id: the ROR ID
    :return: the response
    """
    ror = get_object_or_404(models.RORRecord, pk=ror_id)

    institution = models.Institution.objects.get(ror=ror.ror_id)

    fundings = models.Funding.objects.filter(institution__ror=ror.ror_id)

    contributions = models.Contribution.objects.filter(
        institutions__in=[institution]
    )

    works = []

    for fund in fundings:
        works.append(fund.work)

    for contribution in contributions:
        if contribution.work not in works:
            works.append(contribution.work)

    # paginate the response
    paginator = Paginator(works, 24)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    template = "thoth/all.html"

    context = {"works": page_obj, "heading": institution.institution_name}
    return render(
        request,
        template,
        context,
    )


@cache_page(1200)
def all_books(request) -> HttpResponse:
    """
    Display a list of all books
    :param request: the request object
    :return: the response
    """
    # determine if there's a search
    search_term = request.GET.get("search")

    sort_term = request.GET.get("sort")

    init_term = int(request.GET.get("initiative", 0))

    order_by = "-published_date"

    initiatives = init_models.Initiative.objects.exclude(thoth_id="").filter(
        active=True,
    )

    work_list = []

    if sort_term:
        if sort_term == "Date Newest":
            order_by = "-published_date"
        elif sort_term == "Date Oldest":
            order_by = "published_date"

    to_shunt = []

    if not search_term:
        if init_term and init_term > 0:
            initiative = init_models.Initiative.objects.get(pk=init_term)

            works = (
                models.Work.objects.filter(
                    publisher__thoth_id=initiative.thoth_id
                )
                .prefetch_related(
                    "contribution_set", "contribution_set__contributor"
                )
                .select_related("publisher")
                .order_by(order_by)
            )

        else:
            works = (
                models.Work.objects.all()
                .prefetch_related(
                    "contribution_set", "contribution_set__contributor"
                )
                .select_related("publisher")
                .order_by(order_by)
            )

        for work in works:
            if work.published_date == "n.d.":
                to_shunt.append(work)
            elif (
                datetime.strptime(work.published_date, "%Y-%m-%d")
                > datetime.now()
            ):
                to_shunt.append(work)
            work_list.append(work)
    else:
        # construct a temporary in-memory Thoth search object
        search_terms_split = search_term.split(" ")

        search = models.ThothSearch()
        elements = []

        for term in search_terms_split:
            search_element = models.ThothSearchElement()
            search_element.search_type = models.ThothSearchElement.FREETEXT
            search_element.text_content = term

            elements.append(search_element)

        try:
            works = search.results(elements=elements).order_by(order_by)

            for work in works:
                work_list.append(work)
        except AttributeError:
            pass

        search = models.ThothSearch()
        elements = []

        for term in search_terms_split:
            search_element = models.ThothSearchElement()
            search_element.search_type = models.ThothSearchElement.AUTHOR
            search_element.text_content = term

            elements.append(search_element)

        try:
            works = search.results(elements=elements).order_by(order_by)

            for work in works:
                work_list.append(work)
        except AttributeError:
            pass

        # remove non-initiative works
        remove_list = []

        if init_term and init_term > 0:
            initiative = init_models.Initiative.objects.get(pk=init_term)

            works = models.Work.objects.filter(
                publisher__thoth_id=initiative.thoth_id
            ).order_by(order_by)

            for work in work_list:
                if work not in works:
                    if work.published_date == "n.d.":
                        to_shunt.append(work)
                    remove_list.append(work)

        for work in remove_list:
            work_list.remove(work)

    # push all n.d. results to the back of the list
    for work_to_shunt in to_shunt:
        work_list.remove(work_to_shunt)
        # work_list.append(work_to_shunt)

    for work in work_list:
        work.year = work.published_date.split("-")[0]

    # paginate the response
    paginator = Paginator(work_list, 24)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    template = "thoth/all.html"

    context = {
        "works": page_obj,
        "initiatives": initiatives,
        "num_pages": paginator.num_pages,
        "init_term": init_term,
    }
    return render(
        request,
        template,
        context,
    )


def advanced_search(request) -> HttpResponse:
    """
    Display the advanced search page
    :param request: the request object
    :return: the response
    """
    # retrieve the current search from the session
    current_search, elements = _fetch_search_from_session(request)
    elements = list(elements)

    save_text = ""

    # see if there's a POST asking us to add an element
    if request.method == "POST":
        print(request.POST)

        if request.POST.get("save"):
            save_text = "Saved search successfully."
            current_search.user = request.user
            current_search.display_name = request.POST.get("search_name", "")
            current_search.save()

        elif request.POST.get("delete_all"):
            for search_item in elements:
                models.ThothSearchElement.objects.get(
                    pk=search_item.pk
                ).delete()

            current_search, elements = _fetch_search_from_session(request)

        elif request.POST.get("reset"):
            _new_session(request)
            current_search, elements = _fetch_search_from_session(request)

        elif request.POST.get("Delete"):
            models.ThothSearchElement.objects.get(
                pk=request.POST.get("to_del")
            ).delete()

            element_to_remove = None

            for element in elements:
                if element.pk == int(request.POST.get("to_del")):
                    element_to_remove = element

            if element_to_remove:
                elements.remove(element_to_remove)

            elements = list(elements)

        else:
            # determine if we have actionable content
            search_string = request.POST.get("search", "")
            type_of_search = request.POST.get("type_of_search", "")

            search_terms_split = search_string.split(" ")

            add_search_term(
                current_search, elements, search_terms_split, type_of_search
            )

    # we pass elements as it saves a database trip in results
    works = current_search.results(elements)

    # paginate the response
    paginator = Paginator(works, 24)  # Show 25 contacts per page.
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number) if works else None

    template = "thoth/advanced_search.html"

    context = {
        "works": page_obj,
        "search": current_search,
        "search_elements": elements,
        "save_text": save_text,
    }
    return render(
        request,
        template,
        context,
    )


def add_search_term(
    current_search, elements, search_terms_split, search_type
) -> None:
    """
    Add a search term to the current search
    :param current_search: the current search
    :param elements: the elements
    :param search_terms_split: the search terms, split
    :param search_type: the type of search
    :return: None
    """
    for term in search_terms_split:
        search_element = models.ThothSearchElement()
        search_element.search_type = search_type
        search_element.text_content = term
        search_element.search = current_search

        search_element.save()
        elements.append(search_element)


def _new_session(request) -> None:
    """
    Create a new session
    :param request: the request object
    :return: None
    """
    current_search = models.ThothSearch()
    current_search.save()
    request.session["new_search"] = current_search.pk


def _fetch_search_from_session(request) -> tuple[Any, QuerySet]:
    """
    Fetch the search from the session
    :param request: the request object
    :return: the search and elements
    """
    # see if there's a search in the session
    current_search = request.session.get("new_search", None)

    # if nothing in the session, create a new Thoth search object
    if not current_search:
        current_search = models.ThothSearch()
        current_search.save()
        request.session["new_search"] = current_search.pk
    else:
        try:
            current_search = models.ThothSearch.objects.get(pk=current_search)
        except models.ThothSearch.DoesNotExist:
            current_search = models.ThothSearch()
            current_search.save()
            request.session["new_search"] = current_search.pk

    elements = models.ThothSearchElement.objects.filter(search=current_search)

    return current_search, elements


@json_response
def ror_ajax(request) -> list[dict[str, Any]]:
    """
    Return a list of ROR institutions
    :param request: the request object
    :return: the response
    """
    # extract terms from the database
    term = request.GET.get("term")

    if term:
        results = models.RORRecord.objects.filter(
            institution_name__icontains=term
        )[0:10]

        return_dict = []

        for result in results:
            return_dict.append(
                {"label": result.institution_name, "id": result.ror_id}
            )
    else:
        return []

    return return_dict
