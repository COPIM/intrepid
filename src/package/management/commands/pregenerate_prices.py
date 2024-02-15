import sys
from pprint import pprint

from django.core.management.base import BaseCommand

from package.models import Package, MetaPackage, PreCalcMinMax
from package.utils import get_price_for_package


class Command(BaseCommand):
    """
    A management command that pregenerates package prices
    """

    help = "Pre-generates package prices"

    def handle(self, *args, **options):
        # get a full list of countries that have currencies

        package_list = {}
        meta_package_list = {}

        PreCalcMinMax.objects.all().delete()

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

        for mp in MetaPackage.objects.all():
            meta_package_list[mp] = {}
            for package in mp.packages.all():
                package_dict = package_list[package]
                for country, values in package_dict.items():
                    if meta_package_list[mp].get(country):
                        meta_package_list[mp][country]['min'] = meta_package_list[mp][country]['min'] + values['min']
                        meta_package_list[mp][country]['max'] = meta_package_list[mp][country]['max'] + values['max']
                    else:
                        meta_package_list[mp][country] = {
                            'min': values['min'],
                            'max': values['max'],
                        }
        for package, country in package_list.items():
            for c, values in country.items():
                PreCalcMinMax.objects.create(
                    country=c,
                    package=package,
                    min_amount=values['min'],
                    max_amount=values['max'],
                )
        pprint(meta_package_list)
        for package, country in meta_package_list.items():
            for c, values in country.items():
                PreCalcMinMax.objects.create(
                    meta_package=package,
                    country=c,
                    min_amount=values['min'],
                    max_amount=values['max'],
                )