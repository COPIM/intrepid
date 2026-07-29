from django import template
from django.utils.safestring import mark_safe

from cms import models

register = template.Library()


def _prefetched_site_text(context):
    """
    Return the cached dictionary of site text objects for this render,
    fetching it once if needed. The cache lives on the request when one
    is in context; otherwise (emails, management commands) it lives on
    the template's render_context so the render still does one query.
    :param context: the template context.
    :return: a dictionary mapping site text keys to SiteText objects.
    """
    request = context.get("request")
    if request is not None:
        if not hasattr(request, "cms_prefetched"):
            request.cms_prefetched = {
                o.key: o for o in models.SiteText.objects.all()
            }
        return request.cms_prefetched

    if "cms_prefetched" not in context.render_context:
        context.render_context["cms_prefetched"] = {
            o.key: o for o in models.SiteText.objects.all()
        }
    return context.render_context["cms_prefetched"]


@register.simple_tag(takes_context=True)
def get_site_text(context, site_text_key, cms_prefetched=None):
    """
    Get the site text for the given key and render it with the given context.
    :param context: The context to render the site text with.
    :param site_text_key: The key of the site text to render.
    :param cms_prefetched: A dictionary of prefetched site text objects.
    :return: The rendered site text.
    """
    if not cms_prefetched:
        cms_prefetched = _prefetched_site_text(context)
    else:
        request = context.get("request")
        if request is not None:
            request.cms_prefetched = cms_prefetched

    if site_text_key in cms_prefetched:
        return mark_safe(cms_prefetched[site_text_key].display(context))

    return "!!{}".format(site_text_key)


@register.simple_tag(takes_context=True)
def get_site_text_no_edit(context, site_text_key, cms_prefetched=None):
    """
    Get the site text for the given key and render it with the given context
    without the edit text.
    :param context: The context to render the site text with.
    :param site_text_key: The key of the site text to render.
    :param cms_prefetched: A dictionary of prefetched site text objects.
    :return: The rendered site text.
    """

    return get_site_text(context, site_text_key, cms_prefetched)
