import package.utils as utils

from django.template.defaulttags import register


@register.filter()
def currency_display(value, currency) -> str:
    """
    Formats the price using the currency.
    :param value: the price to format
    :param currency: the currency to use
    :return: the formatted price
    """
    return utils.format_price(value, currency)
