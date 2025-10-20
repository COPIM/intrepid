import sys
from pprint import pprint

from django.core.management.base import BaseCommand

from package.models import Package, MetaPackage, PreCalcMinMax, Country, Price
from package.utils import get_price_for_package
from package.currency import convert


class Command(BaseCommand):
    """
    A management command that pregenerates package prices
    """

    help = "Pre-generates package prices"

    def add_arguments(self, parser):
        parser.add_argument(
            "--convert-currencies",
            action="store_true",
            help="Enable currency conversion using default package prices when missing",
        )

    def handle(self, *args, **options):
        convert_currencies = options["convert_currencies"]

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
            packages = list(mp.packages.all())

            all_countries = set()
            for package in packages:
                all_countries.update(package_list.get(package, {}).keys())

            for country in all_countries:
                min_total = 0
                max_total = 0
                all_found = True

                for package in packages:
                    package_data = package_list.get(package, {}).get(country)

                    if package_data:
                        min_total += package_data["min"]
                        max_total += package_data["max"]
                    elif convert_currencies:
                        fallback = self.get_converted_default_price(package, country.currency)
                        if fallback:
                            converted_min, converted_max = fallback
                            min_total += converted_min
                            max_total += converted_max
                        else:
                            all_found = False
                            break
                    else:
                        all_found = False
                        break

                if all_found:
                    meta_package_list[mp][country] = {
                        "min": min_total,
                        "max": max_total,
                    }

        for package, country_data in package_list.items():
            for country, values in country_data.items():
                PreCalcMinMax.objects.get_or_create(
                    country=country,
                    package=package,
                    min_amount=values["min"],
                    max_amount=values["max"],
                )

        for meta_package, country_data in meta_package_list.items():
            for country, values in country_data.items():
                PreCalcMinMax.objects.get_or_create(
                    meta_package=meta_package,
                    country=country,
                    min_amount=values["min"],
                    max_amount=values["max"],
                )

        for country in Country.objects.filter(catch_all=True):
            PreCalcMinMax.objects.filter(
                country__currency=country.currency,
            ).exclude(
                country=country,
            ).delete()

        for precalc in PreCalcMinMax.objects.all().order_by("package", "meta_package", "country"):
            print(
                f"{precalc.get_package()} {precalc}"
            )

    def get_converted_default_price(self, package, currency_code):
        default_country = package.default_country
        if not default_country:
            return None

        prices = Price.objects.filter(
            banding__package=package,
            country=default_country,
        )

        if not prices.exists():
            return None

        min_value = min(p.value for p in prices)
        max_value = max(p.value for p in prices)

        try:
            converted_min = round(convert(default_country.currency, currency_code, min_value))
            converted_max = round(convert(default_country.currency, currency_code, max_value))
            return converted_min, converted_max
        except Exception:
            return None
