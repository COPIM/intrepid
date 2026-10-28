from django.core.management.base import BaseCommand

from package.models import PreCalcMinMax
from package.utils import regenerate_pre_calc_prices


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
        regenerate_pre_calc_prices(
            convert_currencies=options["convert_currencies"],
        )

        for precalc in PreCalcMinMax.objects.all().order_by("package", "meta_package", "country"):
            print(
                f"{precalc.get_package()} {precalc}"
            )
