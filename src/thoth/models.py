import functools
from datetime import datetime
from functools import reduce
from operator import __and__ as and_operator

from django import db
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from accounts import models as accounts_models
from mail import models as email_models


@functools.total_ordering
class Publisher(models.Model):
    """
    A publisher in Thoth
    """

    publisher_name = models.TextField(blank=True, null=True)
    thoth_id = models.UUIDField()
    thoth_instance = models.URLField(default="https://api.thoth.pub")

    def __str__(self):
        return self.publisher_name

    def __lt__(self, other):
        return self.publisher_name < other.publisher_name


class Stats(models.Model):
    """
    A model to store stats about the Thoth database
    """

    publisher = models.ForeignKey(
        Publisher, on_delete=models.CASCADE, null=True
    )
    year = models.CharField(max_length=4, blank=True, null=True)
    book_count = models.IntegerField(blank=True, null=True)


class CountryStat(models.Model):
    """
    A model to store country stats
    """

    country_code = models.CharField(max_length=255, blank=True, null=True)
    country_count = models.IntegerField(blank=True, null=True)


class BIC(models.Model):
    """
    A BIC subject code
    """

    class Meta:
        verbose_name = _("BIC Code")
        verbose_name_plural = _("BIC Codes")

    code = models.CharField(max_length=20)
    heading = models.CharField(max_length=255)


class BISAC(models.Model):
    """
    A BISAC subject code
    """

    class Meta:
        verbose_name = _("BISAC Code")
        verbose_name_plural = _("BISAC Codes")

    code = models.CharField(max_length=20)
    heading = models.CharField(max_length=255)


class Thema(models.Model):
    """
    A Thema subject code
    """

    class Meta:
        verbose_name = _("Thema Code")
        verbose_name_plural = _("Thema Codes")

    code = models.CharField(max_length=20)
    heading = models.CharField(max_length=255)


class ThothWorkManager(models.Manager):
    """
    A manager for Thoth Work objects
    """

    def get_queryset(self) -> models.QuerySet:
        return (
            super(ThothWorkManager, self)
            .get_queryset()
            .exclude(
                work_type="BOOK_CHAPTER",
            )
        )


class Work(models.Model):
    """
    A work in Thoth
    """

    work_id = models.AutoField(primary_key=True)
    work_type = models.CharField(max_length=255, blank=True, null=True)
    full_title = models.TextField(blank=True, null=True)
    doi = models.CharField(max_length=255, blank=True, null=True)
    cover_url = models.URLField(blank=True, null=True, max_length=512)
    cover_caption = models.TextField(blank=True, null=True)
    thoth_id = models.UUIDField()
    thoth_instance = models.URLField(default="https://api.thoth.pub")
    landing_page = models.URLField(
        default=None, null=True, blank=True, max_length=512
    )
    long_abstract = models.TextField(default="")
    short_abstract = models.TextField(default="")
    publisher = models.ForeignKey(
        Publisher, on_delete=models.CASCADE, null=True
    )
    license = models.CharField(max_length=255, default="")
    published_date = models.CharField(max_length=255, default="n.d.")

    objects = ThothWorkManager()

    @property
    def thoth_export_url(self) -> str:
        """
        REST export URL for this Thoth instance. Replaces "api" with "export"
        :return: a string of the export url
        """
        return self.thoth_instance.replace("api", "export")

    def __str__(self) -> str:
        try:
            dt = datetime.strptime(self.published_date, "%Y-%m-%d")
            return "{0} ({1}, {2})".format(
                self.full_title, self.publisher, dt.year
            )
        except ValueError:
            return "{0} ({1}, {2})".format(
                self.full_title, self.publisher, self.published_date
            )


class WorkNotification(models.Model):
    """
    A model to store notifications about new works
    """

    """
    If a work exists in here, then it has already been notified
    """

    work = models.ForeignKey(Work, on_delete=models.CASCADE)

    @staticmethod
    def notify() -> None:
        """
        Notify users of new books
        :return: None
        """
        to_notify = WorkNotification.notifies()

        for profile, works in to_notify.items():
            for work in works:
                email_template = email_models.EmailTemplate.objects.get(
                    name="new_book_notify",
                )

                context = {
                    "work": work,
                }

                email_template.send(
                    to=profile.account.email,
                    context=context,
                )

                print("Notified {} of {}".format(profile.full_name(), work))

                # set this book to done
                notified = WorkNotification()
                notified.work = work
                notified.save()

        # now put all remaining books in pre-notified state
        works = Work.objects.all()
        for work in works:
            work_notified, created = WorkNotification.objects.get_or_create(
                work=work
            )
            work_notified.save()

    @staticmethod
    def notifies() -> dict[accounts_models.Profile, list | set]:
        """
        Returns a dictionary of profiles and works of which to notify
        :return: a dictionary of profiles and works
        """
        profiles = accounts_models.Profile.objects.all()

        user_list = {}

        notifies = WorkNotification.objects.all()
        notify_ids = notifies.values_list("work_id", flat=True)

        for profile in profiles:
            user_list[profile] = []

            if profile.notify_new_books:
                institutions = Institution.objects.filter(
                    ror=profile.institution.ror_id
                )

                contributions = Contribution.objects.filter(
                    institutions__in=institutions
                ).exclude(work__in=notify_ids)

                for contribution in contributions:
                    user_list[profile].append(contribution.work)

                print(
                    "Notifying {} of {} new "
                    "books".format(profile, len(user_list[profile]))
                )

            else:
                print("Not notifying {} as they have opted out".format(profile))

            # now see if the book matches a search that has notified by email set
            searches = ThothSearch.objects.filter(
                user=profile.account, email_on_new=True
            )

            for search in searches:
                elements = ThothSearchElement.objects.filter(search=search)
                elements = list(elements)

                works = (
                    search.results(elements=elements)
                    .exclude(pk__in=notify_ids)
                    .order_by("-published_date")
                )

                for work in works:
                    user_list[profile].append(work)

                print(
                    "Found {} works to notify {} by "
                    "search".format(works.count(), profile)
                )

            user_list[profile] = set(user_list[profile])

            return user_list


class Subject(models.Model):
    """
    A subject code for a work
    """

    thoth_id = models.UUIDField()
    thoth_instance = models.URLField(default="https://api.thoth.pub")
    subject_type = models.CharField(max_length=255)
    subject_ordinal = models.IntegerField(blank=True, null=True)
    subject_code = models.CharField(max_length=255)
    BIC_code = models.ForeignKey(BIC, null=True, on_delete=models.CASCADE)
    thema_code = models.ForeignKey(Thema, null=True, on_delete=models.CASCADE)
    BISAC_code = models.ForeignKey(BISAC, null=True, on_delete=models.CASCADE)
    work = models.ForeignKey(Work, on_delete=models.CASCADE)

    @property
    def subject_display(self) -> str:
        """
        Display a code and heading for this subject
        :return: a string of the code and heading
        """
        if self.subject_type == "BIC" and self.BIC_code:
            return self.BIC_code.heading
        elif self.subject_type == "THEMA" and self.thema_code:
            return self.thema_code.heading
        elif self.subject_type == "BISAC" and self.BISAC_code:
            return self.BISAC_code.heading
        else:
            return self.subject_code


class Contributor(models.Model):
    """
    A contributor
    """

    contributor_id = models.AutoField(primary_key=True)
    first_name = models.TextField(blank=True, null=True)
    last_name = models.TextField(blank=True, null=True)
    full_name = models.TextField(blank=True, null=True)
    orcid = models.URLField(blank=True, null=True)
    thoth_id = models.UUIDField()
    thoth_instance = models.URLField(default="https://api.thoth.pub")

    def __str__(self):
        return self.full_name


class Contribution(models.Model):
    """
    A contribution to a work
    """

    contribution_id = models.AutoField(primary_key=True)
    institutions = models.ManyToManyField("Institution", blank=True)
    contribution_ordinal = models.IntegerField(blank=True, null=True)
    thoth_id = models.UUIDField()
    contribution_type = models.CharField(max_length=255, blank=True, null=True)
    work = models.ForeignKey(Work, on_delete=models.CASCADE, null=True)
    contributor = models.ForeignKey(
        Contributor, on_delete=models.CASCADE, null=True
    )
    thoth_instance = models.URLField(default="https://api.thoth.pub")

    def __str__(self) -> str:
        if self.contributor and self.work:
            return "{0} as {1} on {2}".format(
                self.contributor.full_name, self.contribution_type, self.work
            )
        else:
            return "Contribution"


class ThothSearch(models.Model):
    """
    A search in Thoth
    """

    class Meta:
        verbose_name_plural = "Thoth Searches"

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, blank=True, null=True
    )
    email_on_new = models.BooleanField(default=False)
    display_name = models.CharField(max_length=255, default="")

    def results(self, elements=None) -> models.QuerySet:
        """
        Returns results for this search
        :param elements: an optional list of elements to parse instead of those
        associated with this entry in the database
        :return: a queryset of Works or None
        """
        if not elements:
            elements = self.thothsearchelement_set.all()

        # we need to build a Q query that intersects all the search types
        works_queries = []
        contributor_queries = []
        institution_queries = []

        for element in elements:
            # the q function of a search element returns a tuple
            # the first element is a Works Q query
            # the second element is a Contributors Q query
            # the third element is an Institution Q query
            if not element.search_type:
                continue

            (
                works_queries_q,
                contributor_queries_q,
                institution_queries_q,
            ) = element.q()

            if works_queries_q and works_queries_q not in works_queries:
                works_queries.append(works_queries_q)

            if (
                contributor_queries_q
                and contributor_queries_q
                and contributor_queries not in contributor_queries
            ):
                contributor_queries.append(contributor_queries_q)

            if (
                institution_queries_q
                and institution_queries_q not in institution_queries
            ):
                institution_queries.append(institution_queries_q)

        if len(contributor_queries) > 0:
            contrib_query = None

            for contributor in contributor_queries:
                if contrib_query:
                    contrib_query = contrib_query | contributor
                else:
                    contrib_query = contributor

            contributors = Contributor.objects.filter(contrib_query)
        else:
            contributors = None

        if len(institution_queries) > 0:
            institutions = Contribution.objects.filter(
                reduce(and_operator, institution_queries)
            ).prefetch_related("work")
        else:
            institutions = None

        final_query = None

        # we need to determine whether each full-text query is a contributor
        # or book title match

        is_subject_reduce = {}
        has_subject = False

        for query in works_queries:
            if "subject_code" in query.children[0][0]:
                is_subject_reduce[query] = True
                has_subject = True
            else:
                is_subject_reduce[query] = False

        if works_queries and len(works_queries) > 0:
            # AND together the works queries (including keywords)
            for query in works_queries:
                if final_query:
                    final_query = final_query & query
                else:
                    final_query = query

        if final_query and contributors and len(contributors) > 0:
            # if we already have a final query object, OR this with contribs
            final_query = final_query & Q(
                contribution__contributor__in=contributors
            )
        elif contributors and len(contributors) > 0:
            # if final query is not set, but we have contributors
            final_query = Q(contribution__contributor__in=contributors)

        if final_query and institutions and len(institutions) > 0:
            # if we already have a final query object, OR this with institutions
            final_query = final_query & Q(contribution__in=institutions)
        elif institutions and len(institutions) > 0:
            final_query = Q(contribution__in=institutions)

        # NOW and the whole thing with keyword queries
        # This means that keyword filters reduce the whole query with an AND
        if has_subject:
            for query in works_queries:
                if is_subject_reduce[query]:
                    if final_query:
                        final_query = final_query & query
                    else:
                        final_query = query

        print(final_query)

        return (
            None
            if not final_query
            else Work.objects.filter(final_query).distinct()
        )


class RORRecord(models.Model):
    """
    A record corresponding to an ROR record
    """

    ror_id = models.URLField(blank=True, null=True)
    institution_name = models.TextField(blank=True, null=True)
    grid_id = models.CharField(max_length=255, blank=True, null=True)
    country = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        indexes = [models.Index(fields=["institution_name"])]

    def __str__(self) -> str:
        return self.institution_name


class Institution(models.Model):
    """
    An institution
    """

    thoth_id = models.UUIDField()
    thoth_instance = models.URLField(default="https://api.thoth.pub")
    institution_name = models.TextField(blank=True, null=True)
    doi = models.TextField(blank=True, null=True)
    ror = models.TextField(blank=True, null=True)
    country_code = models.CharField(max_length=255, blank=True, null=True)


class Funding(models.Model):
    """
    A funding record
    """

    thoth_id = models.UUIDField()
    thoth_instance = models.URLField(default="https://api.thoth.pub")
    project_name = models.TextField(blank=True, null=True)
    project_shortname = models.TextField(blank=True, null=True)
    institution = models.ForeignKey(
        Institution, blank=True, null=True, on_delete=models.CASCADE
    )
    grant_number = models.TextField(blank=True, null=True)
    jurisdiction = models.TextField(blank=True, null=True)
    work = models.ForeignKey(
        Work, blank=True, null=True, on_delete=models.CASCADE
    )


class ThothSearchElement(models.Model):
    """
    A search element in Thoth
    """

    BIC = "BI"
    THEMA = "TH"
    KEYWORD = "KW"
    BISAC = "BS"
    FREETEXT = "FT"
    INSTITUTION = "IT"
    AUTHOR = "AU"
    SEARCH_TYPE_CHOICES = [
        (BIC, "BIC Subject Code"),
        (THEMA, "THEMA Subject Code"),
        (BISAC, "BISAC Subject Code"),
        (KEYWORD, "Keyword"),
        (AUTHOR, "Author"),
        (FREETEXT, "Free Text"),
        (INSTITUTION, "Institution Name"),
    ]

    def __str__(self) -> str:
        return self.text_content

    search_type = models.CharField(
        max_length=2, choices=SEARCH_TYPE_CHOICES, default=FREETEXT
    )

    # establish a generic foreign key to store a remote object
    # this might be a BIC subject code etc
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, default=None, null=True
    )
    object_id = models.PositiveIntegerField(null=True)
    content_object = GenericForeignKey("content_type", "object_id")

    # a text content field for direct searches
    text_content = models.CharField(max_length=255, null=True, blank=True)

    search = models.ForeignKey(ThothSearch, on_delete=models.CASCADE)

    @property
    def type_of_search(self) -> str | None:
        """
        Returns a string of the type of search
        :return: a string of the type of search
        """
        if self.search_type in self.SEARCH_TYPE_CHOICES:
            return dict(self.SEARCH_TYPE_CHOICES)[self.search_type]
        else:
            return None

    @property
    def _word_regex(self) -> str:
        """
        Gives a database-specific whole-word regex for finding whole words only
        :return: a regular expression version of the text_content field
        """

        # if we are using postgres we have to use \Y. Otherwise \b.
        if (
            db.connections.databases["default"]["ENGINE"]
            == "django.db.backends.postgresql"
        ):
            return r"\y{0}\y".format(self.text_content)
        else:
            return r"\b{0}\b".format(self.text_content)

    def q(self) -> tuple[Q | None, Q | None, Q | None]:
        """
        Generate a Q query for this search method
        :return: a tuple of Q queries for Works, Contributor, and Contribution
        """

        # this method returns a Q query for this particular search element
        # specifically, it returns a tuple, the first entry of which is a Q
        # against Works while the second is a Q against Contributor
        # the third is a Q against Institution (via Contribution)

        if self.search_type == self.FREETEXT:
            # freetext searches look for whole words, using database-specific
            # regular expressions in works and contributions
            return Q(full_title__iregex=self._word_regex), None, None

        elif self.search_type == self.BIC:
            # BIC subject search. Returns works, and nothing for contrib and
            # institution
            return Q(subject__BIC_Code=self.content_object), None, None

        elif self.search_type == self.THEMA:
            # THEMA subject search. Returns works, and nothing for contrib and
            # institution
            return Q(subject__thema_Code=self.content_object), None, None

        elif self.search_type == self.BISAC:
            # BISAC subject search. Returns works, and nothing for contrib and
            # institution
            return Q(subject__BISAC_Code=self.content_object), None, None

        elif self.search_type == self.KEYWORD:
            # this is a free-text keywords search
            # it returns a Works Q that looks up raw keywords and None for
            # contribution and institution Qs
            return (
                Q(subject__subject_code__icontains=self.text_content),
                None,
                None,
            )

        elif self.search_type == self.INSTITUTION:
            # no works search, no contributors search, institution regex search
            return (
                None,
                None,
                Q(institutions__institution_name__iregex=self._word_regex),
            )

        elif self.search_type == self.AUTHOR:
            # no works, a contributors search, no institution
            return None, Q(full_name__iregex=self._word_regex), None

        # That was a lot of Q.
        # Goodbye, Jean-Luc. I'm gonna miss you. You had such potential.
        # But then again, all good things must come to an end.
