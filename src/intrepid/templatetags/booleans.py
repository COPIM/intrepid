from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag()
def boolean_font_awesome(boolean):
    """
    Returns a font awesome icon for a boolean value.
    :param boolean: a boolean value
    :return: HTML code for a font awesome icon
    """
    if boolean:
        return mark_safe('<i class="fas fa-check-circle green"></i>')
    return mark_safe('<i class="fas fa-times-circle red"></i>')
