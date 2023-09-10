from django.core.management.base import BaseCommand
from tqdm import tqdm

from initiatives import models as initiative_models
from thoth.models import BIC, BISAC, Funding
from thoth.models import Institution, Publisher, Thema, Work
from thothlibrary import ThothClient


class DotDict(dict):
    """dot.notation access to dictionary attributes"""

    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class Command(BaseCommand):
    """
    A management command that syncs Thoth entries to the local database
    """

    help = "Tests that Thoth sync is working"

    def handle(self, *args, **options):
        """
        A management command that tests Thoth sync is working with minimal
        database interaction
        :param args: command line arguments
        :param options: command line options
        """
        self.test_thoth()

    def output(self, text, ret_text) -> None:
        """
        Outputs text to the console and to the return text
        :param text: the text to output
        :param ret_text: the return text
        :return: None
        """
        print(text)
        ret_text[0] = ret_text[0] + text + "\r\n\r\n"

    def test_thoth(self) -> str:
        """
        Tests that Thoth sync is working with minimal database interaction
        :return: None
        """
        default_thoth_endpoint = "https://api.thoth.pub"

        to_fetch = []

        id_list = []

        ret_text = [""]

        inits = initiative_models.Initiative.objects.filter(active=True)

        for init in inits:
            if init.thoth_id and init.thoth_id not in id_list:
                id_list.append(init.thoth_id)

                to_fetch.append(
                    {
                        "publisher": init.thoth_id,
                        "endpoint": init.thoth_endpoint
                        if init.thoth_endpoint
                        else default_thoth_endpoint,
                    }
                )

        for thoth_sync in to_fetch:
            # a neater way to do this would be to aggregate together all
            # requests that share an endpoint. However, that's more complex
            # so we just do standard iter here

            client = ThothClient(thoth_endpoint=thoth_sync["endpoint"])

            # lookup the publisher name for friendly display
            # this adds an extra API call
            publisher = client.publisher(publisher_id=thoth_sync["publisher"])

            # pull the full list of works for each publisher
            # as a note: technically, a work is different to a publication
            # a publication is a specific format, at a specific price point
            self.output(
                "Fetching works for "
                "publisher {0} [{1}]".format(
                    thoth_sync["publisher"], publisher.publisherName
                ),
                ret_text,
            )

            publisher_model = DotDict({})

            publisher_model.publisher_name = publisher.publisherName

            # we can handle a max of 9999 works at any one time
            # Thoth does support pagination, but currently has no way of
            # precisely querying the expected number of records
            works = client.works(
                limit=9999, publishers='["{0}"]'.format(publisher.publisherId)
            )

            self.output(
                "Syncing works for "
                "publisher {0} [{1}]".format(
                    thoth_sync["publisher"], publisher.publisherName
                ),
                ret_text,
            )

            self._sync_works(publisher_model, thoth_sync, works)

        good_institutions = []
        good_fundings = []

        for thoth_sync in to_fetch:
            # sadly we have to do this in two passes because we need a full
            # works list before we can sync fundings as funders may have
            # records for different publishers
            client = ThothClient(thoth_endpoint=thoth_sync["endpoint"])

            # lookup the publisher name for friendly display
            # this adds an extra API call
            publisher = client.publisher(publisher_id=thoth_sync["publisher"])

            # pull the full list of works for each publisher
            # as a note: technically, a work is different to a publication
            # a publication is a specific format, at a specific price point
            self.output(
                "Fetching institutions and funding for "
                "publisher {0} [{1}]".format(
                    thoth_sync["publisher"], publisher.publisherName
                ),
                ret_text,
            )

            publisher_model = Publisher.objects.get_or_create(
                thoth_id=publisher.publisherId,
                thoth_instance=thoth_sync["endpoint"],
            )[0]

            works = client.works(
                limit=9999, publishers='["{0}"]'.format(publisher.publisherId)
            )

            # now handle institutions and funding
            # as of Thoth v.0.6.0 funders are a sub-class of institution

            institutions = client.institutions(limit=9999)
            gi, gf = self._sync_institutions(thoth_sync, institutions)
            good_institutions += gi
            good_fundings += gf

            self.output(
                "Syncing contributions for "
                "publisher {0} [{1}]".format(
                    thoth_sync["publisher"], publisher.publisherName
                ),
                ret_text,
            )

            self._sync_works(
                publisher_model, thoth_sync, works, do_contribs=True
            )

        # now cleanup anything that's in the database that wasn't on the remote
        # Thoth fetch
        self._cleanup_institutions(good_institutions, good_fundings, ret_text)

        # delete any stats from the database and regenerate
        # gen_stats.Command.generate_stats()

        self.output("End of test reached successfully", ret_text)
        return ret_text[0]

    @staticmethod
    def _verify_exists_in_thoth(thoth_sync, works) -> None:
        """
        Verifies that entries in our database are in remote Thoth servers
        :param thoth_sync: the Thoth instance
        :param works: a list of works from a Thoth instance to check
        :return: None
        """

        works_in_db = Work.objects.filter(
            publisher__thoth_id=thoth_sync["publisher"],
            thoth_instance=thoth_sync["endpoint"],
        )

        for work in works_in_db:
            if any([x for x in works if str(x.workId) == str(work.thoth_id)]):
                print("[Verified] {0} exists in Thoth".format(work))
            else:
                print(
                    "[Unverified] Could not find {0} in Thoth. "
                    "Deleting.".format(work)
                )

    @staticmethod
    def _sync_institutions(
        thoth_sync, institutions
    ) -> tuple[list[DotDict], list[DotDict]]:
        """
        Synchronizes institutions and fundings from the remote Thoth instance
        :param thoth_sync: the Thoth instance
        :param institutions: a list of institutions from a Thoth instance to
        :return: a tuple of two lists, the first being institutions, the second being fundings
        """
        good_institutions = []
        good_fundings = []

        with tqdm(total=len(institutions), unit="insts") as pbar:
            for institution in institutions:
                inst = DotDict({})

                inst.institution_name = institution.institutionName
                inst.doi = institution.institutionDoi
                inst.ror = institution.ror
                inst.country_code = institution.countryCode

                good_institutions.append(inst)

                for funding in institution.fundings:
                    fund = DotDict({})

                    fund.project_name = funding.projectName
                    fund.project_shortname = funding.projectShortname
                    fund.institution = inst
                    fund.grant_number = funding.grantNumber
                    fund.jurisdiction = funding.jurisdiction

                    try:
                        fund.work = Work.objects.get(
                            thoth_id=funding.work.workId,
                            thoth_instance=fund.thoth_instance,
                        )
                        good_fundings.append(fund)
                    except Work.DoesNotExist:
                        # if this work does not exist, it's because
                        # the press for this funder was not imported
                        pass

                pbar.update(1)

        return good_institutions, good_fundings

    def _sync_works(
        self, publisher_model, thoth_sync, works, do_contribs=False
    ) -> None:
        """
        Synchronizes works from the remote Thoth instance
        :param publisher_model: the publisher to use
        :param thoth_sync: the Thoth instance
        :param works: a list of works from a Thoth instance to sync
        :param do_contribs: whether to sync contributions
        :return: None
        """
        with tqdm(total=len(works), unit="works") as pbar:
            for work in works:
                # build a work model
                work_model = DotDict({})

                work_model.thoth_id = work.workId
                work_model.doi = work.doi
                work_model.work_type = work.workType
                work_model.full_title = work.fullTitle
                work_model.cover_url = work.coverUrl
                work_model.cover_caption = work.coverCaption
                work_model.publisher = publisher_model
                work_model.landing_page = work.landingPage

                if work.license:
                    work_model.license = work.license

                if work.longAbstract:
                    work_model.long_abstract = work.longAbstract

                if work.shortAbstract:
                    work_model.short_abstract = work.shortAbstract

                if work.publicationDate:
                    work_model.published_date = work.publicationDate

                if do_contribs:
                    # this is for a second pass
                    # the reason is that we need to have created all
                    # institution objects before we can do contributions
                    self._sync_contributions(thoth_sync, work, work_model)

                    self._sync_subjects(thoth_sync, work, work_model)

                pbar.update(1)

    @staticmethod
    def _sync_subjects(thoth_sync, work, work_model) -> None:
        """
        Synchronizes Thoth subject codes to the local database
        :param thoth_sync: the Thoth sync object
        :param work: the work to sync to
        :param work_model: the database work model
        :return: None
        """

        # save the subjects
        for subject in work.subjects:
            subject_model = DotDict({})

            subject_model.subject_type = subject.subjectType
            subject_model.subject_code = subject.subjectCode
            subject_model.subject_ordinal = subject.subjectOrdinal
            subject_model.thoth_id = subject.subjectId

            # see if there's a BIC entry
            if subject.subjectType == "THEMA":
                try:
                    thema_model = Thema.objects.get(code=subject.subjectCode)

                    subject_model.thema_code = thema_model
                except Thema.DoesNotExist:
                    pass
            elif subject.subjectType == "BIC":
                try:
                    bic_model = BIC.objects.get(code=subject.subjectCode)

                    subject_model.BIC_code = bic_model
                except BIC.DoesNotExist:
                    pass
            elif subject.subjectType == "BISAC":
                try:
                    bisac_model = BISAC.objects.get(code=subject.subjectCode)

                    subject_model.BISAC_code = bisac_model
                except BISAC.DoesNotExist:
                    pass

    @staticmethod
    def _sync_contributions(thoth_sync, work, work_model) -> None:
        """
        Synchronize contributors from Thoth to the local DB
        :param thoth_sync: the Thoth instance
        :param work: the work instance
        :param work_model: the work model instance
        :return: None
        """
        # build the contributions and contributors
        for contribution in work.contributions:
            # find or build the contributor and then update it
            contributor = contribution.contributor

            contributor_model = DotDict({})

            contributor_model.first_name = contributor.firstName
            contributor_model.last_name = contributor.lastName
            contributor_model.full_name = contributor.fullName
            contributor_model.orcid = contributor.orcid
            contributor_model.thoth_id = contributor.contributorId

            # now save the contribution
            contribution_model = DotDict({})

            for affil in contribution.affiliations:
                inst = DotDict({})

            contribution_model.contribution_ordinal = (
                contribution.contributionOrdinal
            )
            contribution_model.contribution_type = contribution.contributionType
            contributor_model.thoth_id = contribution.contributionId

            contribution_model.work = work_model

            contribution_model.contributor = contributor_model

    def _cleanup_institutions(
        self, good_institutions, good_fundings, ret_text
    ) -> None:
        """
        Cleans up orphaned institutions and fundings
        :param good_institutions: the list of good institutions
        :param good_fundings: the list of good fundings
        :param ret_text: the return text
        :return: None
        """
        self.output(
            "Cleaning up orphaned institutions (not associated with "
            "our publishers",
            ret_text,
        )

        institutions = Institution.objects.all()
        dead_insts = 0
        with tqdm(total=len(institutions), unit="insts") as pbar:
            for institution in institutions:
                if not institution in good_institutions:
                    dead_insts += 1
                pbar.update(1)
        self.output(
            "Deleted {0} orphaned institutions (total: {1})".format(
                dead_insts, len(institutions)
            ),
            ret_text,
        )

        self.output(
            "Cleaning up orphaned fundings (not associated with our "
            "publishers)",
            ret_text,
        )

        fundings = Funding.objects.all()
        dead_funds = 0
        with tqdm(total=len(fundings), unit="funds") as pbar:
            for fund in fundings:
                if not fund in good_fundings:
                    dead_funds += 1
                pbar.update(1)

        self.output(
            "Deleted {0} orphaned fundings (total: {1})".format(
                dead_funds, len(fundings)
            ),
            ret_text,
        )
