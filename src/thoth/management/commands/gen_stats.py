from django.core.management.base import BaseCommand
from django.db import transaction

from thoth.models import CountryStat
from thoth.models import Institution, Stats, Work


class Command(BaseCommand):
    """
    A management command that syncs Thoth entries to the local database
    """

    help = "Syncs Thoth metadata to the platform"

    def handle(self, *args, **options):
        """
        A management command that syncs Thoth entries to the local database
        :param args: command line arguments
        :param options: command line options
        """
        # delete any stats from the database and regenerate
        Stats.objects.all().delete()
        CountryStat.objects.all().delete()
        self.generate_stats()

    @staticmethod
    @transaction.atomic
    def generate_stats() -> None:
        """
        Generate stats for the database
        :return: None
        """
        # nothing in the DB so populate it and generate

        # variable initialization
        publishers = {}
        years = []
        final_publishers = {}
        books = Work.objects.all()

        # build a dict of year-by-year, publisher-by-publisher stuff
        # there MIGHT be a way to do this better by aggregating queries

        for book in books:
            # create a dictionary when we find a new publisher
            if book.publisher not in publishers:
                publishers[book.publisher] = {}

            # process the date from the string
            year = book.published_date[0:4]

            # if we don't have the year already, add it to the list of total
            # years
            if year not in years:
                years.append(year)

            if year in publishers[book.publisher]:
                # increment the year by 1 book if we've encountered this
                # publisher and year before
                publishers[book.publisher][year] = (
                    publishers[book.publisher][year] + 1
                )
            else:
                # if this is the first book for this publisher and year
                # set it to 1
                publishers[book.publisher][year] = 1

        # iterate over all years in the database to create uniform-length lists
        for year in sorted(years):
            # if the year is "n.d." we will skip it
            if not year == "n.d.":
                for publisher in publishers:
                    # if we don't have the publisher in the list, add it
                    if publisher not in final_publishers:
                        final_publishers[publisher] = []

                    # save a stat object, so we can cache this in future
                    stat_object = Stats()
                    stat_object.publisher = publisher
                    stat_object.year = year

                    if year in publishers[publisher]:
                        # if we have a value for the publisher and year
                        # then append this count to the final list
                        final_publishers[publisher].append(
                            publishers[publisher][year]
                        )
                        stat_object.book_count = publishers[publisher][year]
                    else:
                        # if we do not have a value for this publisher and year
                        # then we assume that there were no books and set it to
                        # zero
                        final_publishers[publisher].append(0)
                        stat_object.book_count = 0

                    # save the stat object for future caching
                    stat_object.save()

        # build a full database of country code counts
        affiliations = Institution.objects.all()

        for affil in affiliations:
            if affil.country_code:
                cs, created = CountryStat.objects.get_or_create(
                    country_code=affil.country_code
                )
                if not cs.country_count:
                    cs.country_count = 0

                cs.country_count += 1
                cs.save()
