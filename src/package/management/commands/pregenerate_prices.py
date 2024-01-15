import sys

from django.core.management.base import BaseCommand

from package.models import Package
from package.utils import get_price_for_package


class Command(BaseCommand):
    """
    A management command that pregenerates package prices
    """

    help = "Pre-generates package prices"

    def handle(self, *args, **options):
        # get a full list of countries that have currencies

        package_list = {}

        for package in Package.objects.all():
            package_list[package] = {}

            for key, val in package.price_bandings.items():
                for country, prices in val.items():
                    found_min = sys.maxsize
                    found_max = 0

                    min_price = min(prices, key=lambda x: x.value)
                    max_price = max(prices, key=lambda x: x.value)

                    found_min = (
                        min_price.value
                        if min_price.value < found_min
                        else found_min
                    )
                    found_max = (
                        max_price.value
                        if max_price.value > found_max
                        else found_max
                    )

                    package_list[package][country] = {
                        "min": found_min,
                        "max": found_max,
                    }

        print(package_list)
