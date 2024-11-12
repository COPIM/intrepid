from django import template
from django.utils.safestring import mark_safe

from cms import models

register = template.Library()


@register.simple_tag(takes_context=True)
def get_site_text(context, site_text_key, cms_prefetched=None):
    """
    Get the site text for the given key and render it with the given context.
    :param context: The context to render the site text with.
    :param site_text_key: The key of the site text to render.
    :param cms_prefetched: A dictionary of prefetched site text objects.
    :return: The rendered site text.
    """
    if cms_prefetched:
        context["request"].cms_prefetched = cms_prefetched
        if site_text_key in cms_prefetched:
            return mark_safe(cms_prefetched[site_text_key].display(context))
        else:
            return "!!{}".format(site_text_key)

    else:
        if hasattr(context["request"], "cms_prefetched"):
            return get_site_text(
                context,
                site_text_key,
                cms_prefetched=context["request"].cms_prefetched,
            )

        else:
            return get_site_text(
                context,
                site_text_key,
                cms_prefetched={
                    o.key: o for o in models.SiteText.objects.all()
                },
            )


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
