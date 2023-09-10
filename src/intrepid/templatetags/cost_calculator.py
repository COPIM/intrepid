from django import template
from django.utils.safestring import mark_safe

from package import utils, currency as currency_convert

register = template.Library()


@register.simple_tag()
def get_banding(costs, package):
    """
    Get the banding for a package.
    :param costs: the costs
    :param package: the package to get the banding for
    :return: a string with the banding
    """
    for cost in costs:
        if cost.get("package") == package:
            banding = cost.get("banding")
            return f"{banding.banding_type.name} {banding.name()}"
    else:
        return "No banding found."


@register.simple_tag()
def meta_package_cost(costs, meta_package, converted_currency):
    """
    Get the total cost for a meta package.
    :param costs: the costs for the meta package
    :param meta_package: the meta package
    :param converted_currency: the currency to convert to
    :return: the currency totals
    """
    price_list: list = []
    currency_totals: dict = dict()
    packages_checked: list = []

    for cost in costs:
        if (
            cost.get("package") in meta_package.packages.all()
            and cost.get("package") not in packages_checked
        ):
            price_list.append(cost.get("cost"))
            packages_checked.append(cost.get("package"))

    for price in price_list:
        currency = price.country.currency
        if currency_totals.get(currency):
            currency_totals[currency] = (
                currency_totals.get(currency) + price.value
            )
        else:
            currency_totals[currency] = price.value

    currencies_to_pop = []
    if converted_currency:
        for currency, value in currency_totals.copy().items():
            if currency != converted_currency:
                convert_value = currency_convert.convert(
                    currency_from=currency,
                    currency_to=converted_currency,
                    value=value,
                )
                currencies_to_pop.append(currency)
                if currency_totals.get(converted_currency):
                    currency_totals[converted_currency] = (
                        currency_totals[converted_currency] + convert_value
                    )
                else:
                    currency_totals[converted_currency] = convert_value
    for ctp in currencies_to_pop:
        currency_totals.pop(ctp)

    return currency_totals


@register.simple_tag()
def package_cost(costs, package, converted_currency=None):
    """
    Get the cost for a package.
    :param costs: the costs
    :param package: the package to get the cost for
    :param converted_currency: the currency to convert to
    :return: the cost
    """
    for cost in costs:
        if cost.get("package") == package:
            if (
                converted_currency
                and converted_currency != cost.get("cost").country.currency
            ):
                convert_value = currency_convert.convert(
                    currency_from=cost.get("cost").country.currency,
                    currency_to=converted_currency,
                    value=cost.get("cost").value,
                )
                return mark_safe(
                    "<em>{}*</em>".format(
                        format_price(convert_value, converted_currency)
                    )
                )
            else:
                return cost.get("cost")


@register.simple_tag()
def format_price(cost, currency):
    """
    Format a price.
    :param cost: the cost
    :param currency: the currency
    :return: a formatted currency string
    """
    return utils.format_price(cost, currency)


@register.simple_tag()
def add_total_and_site_fee(currency_total, site_percentage):
    """
    Add the total and site fee together.
    :param currency_total: the currency total
    :param site_percentage: the site percentage
    :return: the final cost
    """
    subtotal, site_fee, output_currency = 0, 0, None

    for currency, value in currency_total.items():
        output_currency = currency
        subtotal = value
        break

    for currency, value in site_percentage.items():
        site_fee = value
        break

    return format_price((subtotal + site_fee), output_currency)
