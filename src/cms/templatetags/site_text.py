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
    :return: The rendered site text.
    """
    if cms_prefetched:
        return mark_safe(cms_prefetched[site_text_key].display(context))


    try:
        site_text = models.SiteText.objects.get(
            key=site_text_key,
        )
        return mark_safe(site_text.display(context))
    except models.SiteText.DoesNotExist:
        return ""


@register.simple_tag()
def get_site_text_no_edit(site_text_key, cms_prefetched=None):
    """
    Get the site text for the given key and render it with the given context
    without the edit text.
    :param site_text_key: The key of the site text to render.
    :return: The rendered site text.
    """
    if cms_prefetched:
        return mark_safe(cms_prefetched[site_text_key].body)

    try:
        site_text = models.SiteText.objects.get(
            key=site_text_key,
        )
        return mark_safe(site_text.body)
    except models.SiteText.DoesNotExist:
        return ""
