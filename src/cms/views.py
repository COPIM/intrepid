import csv
from io import StringIO

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from django.shortcuts import (
    render,
    get_object_or_404,
    Http404,
    redirect,
    reverse,
)
from django.views.decorators.http import require_POST
from django.conf import settings
from django.utils import translation
from django.utils import timezone

from fluid_permissions import decorators

import intrepid.views
from cms import models, forms, utils
from intrepid import diff_match_patch as dmp_module
from intrepid.security import user_is_initiative_manager
from thoth import models as thoth_models


@user_is_initiative_manager
def featured_books(request, initiative) -> HttpResponse:
    """
    View for managing featured books
    :param request: the request object
    :param initiative: the initiative object
    :return: HttpResponse object
    """
    template = "cms/featured_books.html"

    featured_books_object = models.FeaturedBook.objects.filter(
        initiative=initiative
    ).order_by("order")

    context = {
        "initiative": initiative,
        "featured_books": featured_books_object,
        "sort_url": reverse(
            "featured_books_order", kwargs={"initiative_id": initiative.pk}
        ),
    }
    return render(
        request,
        template,
        context,
    )


@user_is_initiative_manager
def page_list(request, initiative, page_or_update) -> HttpResponse:
    """
    View for managing pages
    :param request: the request object
    :param initiative: the initiative object
    :param page_or_update: either "page" or "update"
    :return: HttpResponse object
    """
    pages, updates = None, None
    if page_or_update == "page":
        pages = models.PageUpdate.objects.filter(
            is_update=False,
            initiative=initiative,
        )
    else:
        updates = models.PageUpdate.objects.filter(
            is_update=True,
            initiative=initiative,
        )
    if updates:
        objects = updates
    else:
        objects = pages
    template = "cms/page_list.html"

    featured_books_object = models.FeaturedBook.objects.filter(
        initiative=initiative
    )

    context = {
        "pages": pages,
        "updates": updates,
        "objects": objects,
        "initiative": initiative,
        "featured_books": featured_books_object,
        "page_or_update": page_or_update,
        "sort_url": reverse(
            "initiative_pages_order", kwargs={"initiative_id": initiative.pk}
        ),
    }
    return render(
        request,
        template,
        context,
    )


@user_is_initiative_manager
@require_POST
def initiative_pages_order(request, initiative_id) -> HttpResponse:
    """
    Reorders the Form Elements list, posted via AJAX.
    :param request: HttpRequest object
    :param initiative_id: the initiative ID
    :return: HttpResponse object
    """

    ids = request.POST.getlist("initiative_page[]")
    ids = [int(_id) for _id in ids]

    for fe in models.PageUpdate.objects.filter(
        initiative=initiative_id, is_update=False
    ):
        fe.sequence = ids.index(fe.pk)
        fe.save()

    return HttpResponse("Thanks")


@user_is_initiative_manager
def page_detail(request, initiative, page_or_update, page_id) -> HttpResponse:
    """
    View for managing pages
    :param request: the request object
    :param initiative: the initiative object
    :param page_or_update: either "page" or "update"
    :param page_id: the page ID
    :return: HttpResponse object
    """
    if page_or_update == "page":
        page_or_update_object = get_object_or_404(
            models.PageUpdate,
            pk=page_id,
            is_update=False,
            initiative=initiative,
        )
    else:
        page_or_update_object = get_object_or_404(
            models.PageUpdate,
            pk=page_id,
            is_update=True,
            initiative=initiative,
        )

    if request.POST and "set_current" in request.POST:
        version = get_object_or_404(
            models.Version, pk=request.POST.get("set_current")
        )
        if version and version in page_or_update_object.other_versions.all():
            page_or_update_object.current_version = version
            page_or_update_object.save()
            messages.add_message(
                request,
                messages.SUCCESS,
                "Version #{} is now the current version.".format(version.pk),
            )
            return redirect(
                reverse(
                    "page_detail",
                    kwargs={
                        "initiative": initiative.pk,
                        "page_or_update": page_or_update,
                        "page_id": page_or_update_object.pk,
                    },
                )
            )
    template = "cms/page_detail.html"
    context = {
        "object": page_or_update_object,
        "initiative": initiative,
        "page_or_update": page_or_update,
    }
    return render(
        request,
        template,
        context,
    )


@user_is_initiative_manager
def featured_book_create(request, initiative) -> HttpResponse:
    """
    View for creating a featured book
    :param request: the request object
    :param initiative: the initiative object
    :return: HttpResponse object
    """
    if request.POST:
        work = get_object_or_404(
            thoth_models.Work, pk=request.POST.get("thoth_id")
        )

        book, created = models.FeaturedBook.objects.get_or_create(
            initiative=initiative, book=work
        )

        book.save()

        return redirect(
            reverse(
                "featured_books",
                kwargs={
                    "initiative": initiative.pk,
                },
            )
        )

    template = "thoth/thoth_featured.html"
    context = {}
    return render(
        request,
        template,
        context,
    )


@user_is_initiative_manager
def page_edit_or_create(
    request, initiative, page_or_update, page_id=None
) -> HttpResponse:
    """
    View for editing or creating a page
    :param request: the request object
    :param initiative: the initiative object
    :param page_or_update: either "page" or "update"
    :param page_id: the page ID
    :return: HttpResponse object
    """

    # TODO: consider breaking this function up into smaller functions

    page, current_version = None, None
    if page_id:
        page = get_object_or_404(
            models.PageUpdate,
            pk=page_id,
            initiative=initiative,
        )
        current_version = page.current_version
    page_form = forms.PageUpdateForm(
        instance=page,
        initiative=initiative,
        user=request.user,
        page_or_update=page_or_update,
        ror="",
    )
    version_form = forms.VersionForm(
        initial={
            "body": current_version.body if current_version else "",
            "first_paragraph": (
                current_version.first_paragraph if current_version else ""
            ),
            "pre_break_content": (
                current_version.pre_break_content if current_version else ""
            ),
            "pull_quote": (
                current_version.pull_quote if current_version else ""
            ),
            "show_quote_icons": (
                current_version.show_quote_icons if current_version else True
            ),
        },
        user=request.user,
    )

    if request.POST:
        if request.POST["inst_lookup"] == "":
            # the user has blanked the lookup box
            ror = ""
        elif request.POST["institution_ROR"] == "":
            # the user has left the lookup box as it was
            try:
                ror = page.target_institution.ror_id
            except AttributeError:
                ror = ""
        else:
            # a new ROR has been submitted
            ror = request.POST["institution_ROR"]

        page_form = forms.PageUpdateForm(
            request.POST,
            request.FILES,
            instance=page,
            initiative=initiative,
            user=request.user,
            page_or_update=page_or_update,
            ror=ror,
        )
        version_form = forms.VersionForm(
            request.POST,
            user=request.user,
        )

        page_form_valid = page_form.is_valid()
        version_form_valid = version_form.is_valid()

        if page_form_valid and version_form_valid:
            page = page_form.save()

            if not current_version:
                version = version_form.save()
                page.current_version = version
                page.other_versions.add(version)
                page.save()

            else:
                # now we have the structured version, we just always save a new
                # version rather than attempting to detect changes
                version = version_form.save()
                if "set_current" in request.POST:
                    page.current_version = version
                page.other_versions.add(version)
                page.save()

            messages.add_message(
                request,
                messages.SUCCESS,
                "Details of {} saved".format(page_or_update),
            )
            utils.send_cms_change_notification(
                request,
                initiative,
                page_or_update,
                page,
            )
            if (
                page_or_update == "update"
                and page.target_institution
                and page.display
                and not page.notification_sent
            ):
                # this update has just been created, send a notification to
                # users with the target_institution
                utils.send_target_institution_notification(
                    request,
                    page,
                )
            return redirect(
                reverse(
                    "page_detail",
                    kwargs={
                        "initiative": initiative.pk,
                        "page_or_update": page_or_update,
                        "page_id": page.pk,
                    },
                )
            )

    inst_name = ""
    ror = ""

    if page and page.target_institution:
        try:
            inst_name = page.target_institution.institution_name
            ror = page.target_institution.ror_id
        except AttributeError:
            pass

    template = "cms/edit_or_create.html"
    context = {
        "page": page,
        "initiative": initiative,
        "page_form": page_form,
        "version_form": version_form,
        "page_or_update": page_or_update,
        "initial_value": inst_name,
        "initial_ror": ror,
    }
    return render(
        request,
        template,
        context,
    )


@user_is_initiative_manager
def featured_book_delete(request, initiative, fb_id) -> HttpResponse:
    """
    Delete a featured book
    :param request: the request object
    :param initiative: the initiative object
    :param fb_id: the featured book ID
    :return: HttpResponse object
    """
    # put the initiative in here to constrain via security
    # (i.e. the decorator validates that the user can modify the initiative)
    fb = get_object_or_404(
        models.FeaturedBook, initiative=initiative, pk=fb_id
    )

    fb.delete()

    return redirect(
        reverse(
            "page_list",
            kwargs={
                "initiative": initiative.pk,
                "page_or_update": "update",
            },
        )
    )


@user_is_initiative_manager
def page_delete(request, initiative, page_or_update, page_id) -> HttpResponse:
    """
    Delete a page
    :param request: the request object
    :param initiative: the initiative object
    :param page_or_update: the page or update
    :param page_id: the page ID
    :return: HttpResponse object
    """
    page = get_object_or_404(
        models.PageUpdate,
        pk=page_id,
        initiative=initiative,
    )
    page.delete()
    messages.add_message(
        request,
        messages.INFO,
        "Delete successful.",
    )
    return redirect(
        reverse(
            "page_list",
            kwargs={
                "initiative": initiative.pk,
                "page_or_update": page_or_update,
            },
        )
    )


@user_is_initiative_manager
def view_version(
    request, initiative, page_or_update, page_id, version_id=None
) -> HttpResponse:
    """
    View a version of a page or update
    :param request: the request object
    :param initiative: the initiative object
    :param page_or_update: the page or update
    :param page_id: the page ID
    :param version_id: the version ID
    :return: HttpResponse object
    """
    page = get_object_or_404(
        models.PageUpdate,
        pk=page_id,
        initiative=initiative,
    )
    if version_id and page.current_version.pk == version_id:
        version = page.current_version
    else:
        version = page.other_versions.filter(pk=version_id).first()
        if not version:
            raise Http404

    if page_or_update == "page":
        template = "cms/view_page_version.html"
    else:
        template = "cms/view_update_version.html"
    context = {
        "page": page,
        "version": version,
    }
    return render(
        request,
        template,
        context,
    )


@user_is_initiative_manager
def view_current_version(
    request, initiative, page_or_update, page_id
) -> HttpResponse:
    """
    View the current version of a page or update
    :param request: the request object
    :param initiative: the initiative object
    :param page_or_update: the page or update
    :param page_id: the page ID
    :return: HttpResponse object
    """
    page = get_object_or_404(
        models.PageUpdate,
        pk=page_id,
        initiative=initiative,
    )
    version = page.current_version
    if page_or_update == "page":
        template = "cms/view_page_version.html"
    else:
        template = "cms/view_update_version.html"
    context = {
        "page": page,
        "version": version,
    }
    return render(
        request,
        template,
        context,
    )


@user_is_initiative_manager
def diff_versions(
    request,
    initiative,
    page_or_update,
    page_id,
    version_one_id,
    version_two_id,
) -> HttpResponse:
    """
    View the diff between two versions of a page or update
    :param request: the request object
    :param initiative: the initiative object
    :param page_or_update: the page or update
    :param page_id: the page ID
    :param version_one_id: the first version ID
    :param version_two_id: the second version ID
    :return: HttpResponse object
    """
    page = get_object_or_404(
        models.PageUpdate,
        pk=page_id,
        initiative=initiative,
    )
    version_one = get_object_or_404(
        models.Version,
        pk=version_one_id,
    )
    version_two = get_object_or_404(
        models.Version,
        pk=version_two_id,
    )
    dmp = dmp_module.diff_match_patch()
    diff = dmp.diff_main(version_one.body, version_two.body)
    dmp.diff_cleanupSemantic(diff)
    diff_out = dmp.diff_prettyHtml(diff)
    template = "cms/diff.html"
    context = {
        "version_one": version_one,
        "version_two": version_two,
        "diff_out": diff_out,
        "page": page,
        "initiative": initiative,
    }
    return render(
        request,
        template,
        context,
    )


@decorators.user_in_authorised_group
def page_update_feed(request) -> HttpResponse:
    """
    View the page update feed]
    :param request: the request object
    :return: HttpResponse object
    """
    versions = models.Version.objects.all().prefetch_related("pageupdate_set")
    template = "cms/update_feed.html"
    context = {
        "versions": versions,
    }
    return render(
        request,
        template,
        context,
    )


@staff_member_required()
def sitewide_news_config(request) -> HttpResponse:
    """
    Configure the sitewide news
    :param request: the request object
    :return: HttpResponse object
    """
    pages = models.PageUpdate.objects.filter(is_update=True)
    template = "cms/sitewide_news_config.html"

    if request.POST:
        page_to_add = request.POST.get("page_to_add")
        if page_to_add:
            linked_item = get_object_or_404(models.PageUpdate, pk=page_to_add)

            # only do this if the item doesn't already exist
            try:
                models.SiteWideNewsItem.objects.get(update_item=linked_item)

            except models.SiteWideNewsItem.DoesNotExist:
                # doesn't exist
                new_news_item = models.SiteWideNewsItem()
                new_news_item.update_item = linked_item
                new_news_item.save()

    news_items = models.SiteWideNewsItem.objects.all().order_by("order")

    context = {
        "news_items": news_items,
        "pages": pages,
        "sort_url": reverse("sitewide_news_order"),
    }
    return render(
        request,
        template,
        context,
    )


def sitewide_news(request) -> HttpResponse:
    """
    View the sitewide news
    :param request: the request object
    :return: HttpResponse object
    """
    models.PageUpdate.objects.filter(is_update=True)
    template = "base/frontend/news.html"

    news_items = models.SiteWideNewsItem.objects.all().order_by("order")

    context = {
        "news_items": news_items,
    }
    return render(
        request,
        template,
        context,
    )


def news_item(request, update_id) -> HttpResponse:
    """
    View a news item
    :param request: the request object
    :param update_id: the update ID
    :return: HttpResponse object
    """
    page_item = get_object_or_404(models.PageUpdate, pk=update_id)

    if not page_item.display:
        raise Http404

    template = "base/frontend/cms_page.html"
    context = {
        "page": page_item,
    }
    return render(
        request,
        template,
        context,
    )


def extract_ids(input_list) -> list:
    """
    Extracts the IDs from a list of strings
    :param input_list: the list of strings
    :return: list of IDs
    """
    return [int(_id) for _id in input_list]


@require_POST
@staff_member_required
def sitewide_news_order(request) -> HttpResponse:
    """
    Reorders the Form Elements list, posted via AJAX.
    :param request: HttpRequest object
    :return: HttpResponse object
    """

    news_ids = extract_ids(request.POST.getlist("news-items[]"))

    news_items = models.SiteWideNewsItem.objects.all()

    if len(news_ids) > 0:
        for news_item_object in news_items:
            try:
                news_item_object.order = news_ids.index(news_item_object.pk)
                news_item_object.save()
            except ValueError:
                pass

    return HttpResponse("Thanks")


@staff_member_required
def who_we_are_config(request) -> HttpResponse:
    """
    Configure the who we are section
    :param request: the request object
    :return: HttpResponse object
    """
    stewards = models.WhoWeAreProfileItem.objects.filter(
        section="stewards"
    ).order_by("order")
    members = models.WhoWeAreProfileItem.objects.filter(
        section="members"
    ).order_by("order")
    managers = models.WhoWeAreProfileItem.objects.filter(
        section="managers"
    ).order_by("order")
    secretariat = models.WhoWeAreProfileItem.objects.filter(
        section="secretariat"
    ).order_by("order")
    finance = models.WhoWeAreProfileItem.objects.filter(
        section="finance"
    ).order_by("order")
    previous = models.WhoWeAreProfileItem.objects.filter(
        section="previous"
    ).order_by("order")

    template = "cms/who_we_are_section_list.html"
    context = {
        "stewards": stewards,
        "members": members,
        "managers": managers,
        "secretariat": secretariat,
        "finance": finance,
        "previous": previous,
        "sort_url": reverse("who_we_are_order"),
    }
    return render(
        request,
        template,
        context,
    )


@staff_member_required
def add_who_we_are_entry(request, section, entry_id=None) -> HttpResponse:
    """
    Add or edit a who we are entry
    :param request: the request object
    :param section: the section
    :param entry_id: the entry ID
    :return: HttpResponse object
    """
    wwe = None

    if entry_id:
        wwe = get_object_or_404(
            models.WhoWeAreProfileItem,
            pk=entry_id,
        )

    wwe_form = forms.WhoWeAreEntryForm(instance=wwe, section=section)

    if request.POST:
        wwe_form = forms.WhoWeAreEntryForm(
            request.POST, request.FILES, instance=wwe, section=section
        )

        wwe_form_valid = wwe_form.is_valid()

        if wwe_form_valid:
            wwe_form.save()

            return redirect(
                reverse(
                    "who_we_are_config",
                )
            )
    template = "cms/edit_or_create_who_we_are.html"
    context = {
        "wwe": wwe,
        "wwe_form": wwe_form,
    }
    return render(
        request,
        template,
        context,
    )


@staff_member_required
@require_POST
def sitewide_news_delete(request, news_id) -> HttpResponse:
    """
    Delete a sitewide news item
    :param request: the request object
    :param news_id: the news item ID
    :return: HttpResponse object
    """
    get_object_or_404(
        models.SiteWideNewsItem,
        pk=news_id,
    ).delete()

    return redirect(reverse("sitewide_news_config"))


@staff_member_required
@require_POST
def delete_who_we_are_entry(request, entry_id) -> HttpResponse:
    """
    Delete a who we are entry
    :param request: the request object
    :param entry_id: the entry ID
    :return: HttpResponse object
    """
    get_object_or_404(
        models.WhoWeAreProfileItem,
        pk=entry_id,
    ).delete()

    return redirect(reverse("who_we_are_config"))


@require_POST
@staff_member_required
def who_we_are_order(request) -> HttpResponse:
    """
    Reorders the Form Elements list, posted via AJAX.
    :param request: HttpRequest object
    :return: HttpResponse object
    """

    steward_ids = extract_ids(request.POST.getlist("stewards[]"))
    member_ids = extract_ids(request.POST.getlist("members[]"))
    manager_ids = extract_ids(request.POST.getlist("managers[]"))
    secretariat_ids = extract_ids(request.POST.getlist("secretariat[]"))
    previous_ids = extract_ids(request.POST.getlist("previous[]"))

    wwe_items = models.WhoWeAreProfileItem.objects.all()

    item_list = [
        steward_ids,
        member_ids,
        manager_ids,
        secretariat_ids,
        previous_ids,
    ]

    for item in item_list:
        if len(item) > 0:
            for wwe_item in wwe_items:
                try:
                    wwe_item.order = item.index(wwe_item.pk)
                    wwe_item.save()
                except ValueError:
                    pass

    return HttpResponse("Thanks")


@staff_member_required
def fixed_pages(request) -> HttpResponse:
    """
    Configure the fixed pages
    :param request: the request object
    :return: HttpResponse object
    """
    try:
        instance = models.PrimaryInitiative.objects.all()[0]
    except IndexError:
        instance = None

    form = forms.PrimaryInitiativeForm(instance=instance)

    if request.POST:
        form = forms.PrimaryInitiativeForm(request.POST, instance=instance)

        if form.is_valid():
            form.save()

    template = "cms/fixed_pages.html"
    context = {
        "form": form,
    }
    return render(
        request,
        template,
        context,
    )


def fixed_page(request, page_string) -> HttpResponse:
    """
    Renders a fixed page
    :param request: the request object
    :param page_string: the page string
    :return: HttpResponse object
    """
    # append this to ensure we don't allow end users to call a getattr method
    page_string += "_page"

    try:
        instance = models.PrimaryInitiative.objects.all()[0]

        page_object = getattr(instance, page_string)

        if not page_object:
            raise Http404

        # this is a check to make sure that initiatives can't title a page
        # "Terms and Conditions" and have it accidentally selected
        if page_object.initiative != instance.initiative:
            raise Http404

        # if there's a nav entry, redirect
        if (
            page_object.url_expression is not None
            and page_object.url_expression != ""
        ):
            return redirect(
                intrepid.views.nav,
                page_name=page_object.url_expression,
            )

        template = "base/frontend/cms_page.html"
        context = {
            "page": page_object,
        }

        return render(
            request,
            template,
            context,
        )

    except IndexError:
        raise Http404


@staff_member_required
def all_pages(request) -> HttpResponse:
    """
    View all pages
    :param request: the request object
    :return: HttpResponse object
    """
    pages = models.PageUpdate.objects.all()
    template = "cms/all_pages.html"
    context = {
        "objects": pages,
    }
    return render(
        request,
        template,
        context,
    )


@staff_member_required
def page_render(request, page_id: int) -> HttpResponse:
    """
    Render a page
    """
    try:
        page_object = get_object_or_404(models.PageUpdate, pk=page_id)

        template = "base/frontend/cms_page.html"
        context = {
            "page": page_object,
        }

        return render(
            request,
            template,
            context,
        )

    except IndexError:
        raise Http404


@staff_member_required
def homepage_quotes(request) -> HttpResponse:
    """
    Configure the homepage quotes
    :param request: the request object
    :return: HttpResponse object
    """
    quotes = models.HomePageQuote.objects.all().order_by("order")

    template = "cms/homepage_quotes.html"
    context = {
        "quotes": quotes,
        "sort_url": reverse("homepage_quotes_order"),
    }
    return render(
        request,
        template,
        context,
    )


@staff_member_required
def new_quote(request, quote_id=None) -> HttpResponse:
    """
    Create or edit a homepage quote
    :param request: the request object
    :param quote_id: the quote ID
    :return: HttpResponse object
    """
    homepage_quote = None

    if quote_id:
        homepage_quote = get_object_or_404(
            models.HomePageQuote,
            pk=quote_id,
        )

    hpq_form = forms.HomePageQuoteForm(instance=homepage_quote)

    if request.POST:
        hpq_form = forms.HomePageQuoteForm(
            request.POST,
            request.FILES,
            instance=homepage_quote,
        )

        hpq_form_valid = hpq_form.is_valid()

        if hpq_form_valid:
            hpq_form.save()

            return redirect(
                reverse(
                    "homepage_quotes",
                )
            )
    template = "cms/edit_or_create_homepage_quote.html"
    context = {
        "hpq": homepage_quote,
        "form": hpq_form,
    }
    return render(
        request,
        template,
        context,
    )


@staff_member_required
@require_POST
def delete_quote(request, quote_id) -> HttpResponse:
    """
    Delete a homepage quote
    :param request: the request object
    :param quote_id: the quote ID
    :return: HttpResponse object
    """
    get_object_or_404(models.HomePageQuote, pk=quote_id).delete()

    return redirect(reverse("homepage_quotes"))


@require_POST
@staff_member_required
def homepage_quotes_order(request) -> HttpResponse:
    """
    Reorders the Homepage Quotes list, posted via AJAX.
    :param request: HttpRequest object
    :return: HttpResponse object
    """

    quote_ids = request.POST.getlist("home-quote[]")
    quote_ids = [int(_id) for _id in quote_ids]

    quote_items = models.HomePageQuote.objects.all()

    if len(quote_ids) > 0:
        for quote_item in quote_items:
            try:
                quote_item.order = quote_ids.index(quote_item.pk)
                quote_item.save()
            except ValueError:
                pass

    return HttpResponse("Thanks")


@require_POST
@user_is_initiative_manager
def order_featured_books(request, initiative_id) -> HttpResponse:
    """
    Reorders the featured books
    :param request: HttpRequest object
    :param initiative_id: the initiative ID
    :return: HttpResponse object
    """

    fb_ids = request.POST.getlist("featured-book[]")
    ids = [int(_id) for _id in fb_ids]

    for fb in models.FeaturedBook.objects.filter(initiative=initiative_id):
        fb.order = ids.index(fb.pk)
        fb.save()

    return HttpResponse("Thanks")


@staff_member_required
def edit_site_text(request, key) -> HttpResponse:
    """
    Edit a site text
    :param request: the request object
    :param key: the site text key
    :return: HttpResponse object
    """
    site_text = get_object_or_404(
        models.SiteText,
        key=key,
    )
    form = forms.EditSiteText(
        instance=site_text,
    )
    if request.POST:
        form = forms.EditSiteText(
            request.POST,
            instance=site_text,
        )
        if form.is_valid():
            form.save()
            messages.add_message(
                request,
                messages.SUCCESS,
                "Site text updated",
            )
            return redirect(
                reverse("edit_site_text", kwargs={"key": site_text.key})
            )
    template = "cms/edit_site_text.html"
    context = {
        "site_text": site_text,
        "form": form,
    }
    return render(
        request,
        template,
        context,
    )


@staff_member_required
def list_site_text(request):
    """
    View to list all site texts with a language selection dropdown.
    """
    site_texts = models.SiteText.objects.all()
    languages = settings.LANGUAGES  # Dynamically get languages from settings

    return render(
        request,
        "cms/site_text_list.html",
        {
            "site_texts": site_texts,
            "languages": languages,
        },
    )


@staff_member_required
def site_text_csv(request):
    """
    View to download a CSV of all site texts
    """
    site_texts = models.SiteText.objects.all()
    languages = settings.LANGUAGES  # Dynamically get languages from settings

    def data(site_texts_objects):
        csvfile = StringIO()
        csvwriter = csv.writer(csvfile)

        csvwriter.writerow(["ID", "Key", "Is Frontend?", "English", "German"])

        for site_text in site_texts_objects:
            english = site_text.body_en
            german = site_text.body_de

            csvwriter.writerow([site_text.pk, site_text.key, site_test.frontend, english, german])

        yield csvfile.getvalue()

    response = HttpResponse(data(site_texts), content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=languages.csv"
    return response


@staff_member_required
def edit_site_text(request, key, lang_code):
    """
    View to handle both displaying the modal for editing site text
    and saving the updated text in the selected language.
    """
    site_text = get_object_or_404(models.SiteText, key=key)

    # Use `with override(lang_code)` to temporarily set the language
    with translation.override(lang_code):
        if request.method == "POST":
            body = request.POST.get("body")

            # Save the updated site text
            site_text.body = body
            site_text.save()

            # Get the current date and time using Django's timezone
            current_time = timezone.now().strftime("%Y-%m-%d %H:%M:%S")

            # Return an HTML success message with the timestamp
            return HttpResponse(
                f'<div class="alert alert-success">Saved successfully at {current_time}.</div>'
            )

        # If GET request, render the full modal for editing
        return render(
            request,
            "cms/htmx/site_text_modal.html",
            {
                "site_text": site_text,
                "lang_code": lang_code,
            },
        )
