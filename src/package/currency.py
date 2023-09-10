import os

from currency_converter import CurrencyConverter
from django.conf import settings

CURRENCY_FILE_PATH = os.path.join(
    settings.BASE_DIR, "currency", "eurofxref.csv"
)


def convert(currency_from, currency_to, value) -> float:
    """
    Convert a value from a currency to another
    :param currency_from: the currency to convert from
    :param currency_to: the currency to convert to
    :param value: the value to convert
    :return: the converted value
    """
    converter = CurrencyConverter(currency_file=CURRENCY_FILE_PATH)
    value = converter.convert(value, currency_from, currency_to)
    return value
