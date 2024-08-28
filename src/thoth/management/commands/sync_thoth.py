import time

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from tqdm import tqdm

from initiatives import models as initiative_models
from intrepid import models as intrepid_models
from thoth import models as thoth_models
from thoth.management.commands import gen_stats
from thoth.models import (
    BIC,
    BISAC,
    Contribution,
    Contributor,
    Funding,
    RORRecord,
)
from thoth.models import Institution, Publisher, Subject, Thema, Work
from thothlibrary import ThothClient


class Command(BaseCommand):
    """
    A management command that syncs Thoth entries to the local database
    """

    help = "Syncs Thoth metadata to the platform"

    def output(self, text, ret_text):
        print(text)
        ret_text[0] = ret_text[0] + text + "\r\n\r\n"

    def handle(self, *args, **options):
        """
        A management command that syncs Thoth entries to the local database
        :param args: command line arguments
        :param options: command line options
        """

        self.sync_thoth()

    def sync_thoth(self) -> None:
        """
        Syncs Thoth entries to the local database
        :return: None
        """
        ret_text = [""]
        self.output("Started import at {}".format(timezone.now()), ret_text)

        try:
            with transaction.atomic():
                time.sleep(5)
                self.run_sync(ret_text)
        finally:
            # save the log
            try:
                setup = intrepid_models.SiteSetup.objects.all().order_by("pk")[
                    0
                ]
            except IndexError:
                setup = intrepid_models.SiteSetup()

            setup.last_thoth_log = ret_text[0] + "\r\n"
            setup.last_thoth_log = (
                setup.last_thoth_log + "If log does not "
                'end with "SUCCESS"'
                " then there was "
                "an error"
            )
            setup.last_thoth_log_date = timezone.now()
            setup.save()

    def run_sync(self, ret_text) -> None:
        """
        Runs the sync
        :param ret_text: the return text
        :return: None
        """
        default_thoth_endpoint = "https://api.thoth.pub"

        to_fetch = []
        new_insts = []
        id_list = []

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

        # remove any Thoth publishers that will not be processed
        for publisher in thoth_models.Publisher.objects.all():
            if str(publisher.thoth_id) not in id_list:
                publisher.delete()
                self.output("Deleted {}".format(publisher), ret_text)

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

            publisher_model = Publisher.objects.get_or_create(
                thoth_id=publisher.publisherId,
                thoth_instance=thoth_sync["endpoint"],
            )[0]

            publisher_model.publisher_name = publisher.publisherName
            publisher_model.save()

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

            new_insts = self._sync_works(publisher_model, thoth_sync, works)

            self._verify_exists_in_thoth(thoth_sync, works, ret_text)

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

        good_institutions = good_institutions + new_insts

        # now cleanup anything that's in the database that wasn't on the remote
        # Thoth fetch
        self._cleanup_institutions(good_institutions, good_fundings, ret_text)

        # delete any stats from the database and regenerate
        gen_stats.Command.generate_stats()

        self.output("SUCCESS", ret_text)

    def _verify_exists_in_thoth(self, thoth_sync, works, ret_text) -> None:
        """
        Verifies that entries in our database are in remote Thoth servers
        :param thoth_sync: the Thoth instance
        :param works: a list of works from a Thoth instance to check
        :param ret_text: the return text
        :return: None
        """

        works_in_db = Work.objects.filter(
            publisher__thoth_id=thoth_sync["publisher"],
            thoth_instance=thoth_sync["endpoint"],
        )

        for work in works_in_db:
            if any([x for x in works if str(x.workId) == str(work.thoth_id)]):
                self.output(
                    "[Verified] {0} exists in Thoth".format(work), ret_text
                )
            else:
                self.output(
                    "[Unverified] Could not find {0} in Thoth. "
                    "Deleting.".format(work),
                    ret_text,
                )
                work.delete()

    @staticmethod
    def _sync_institutions(
        thoth_sync, institutions
    ) -> tuple[list[Institution], list[Funding]]:
        """
        Synchronizes institutions from the remote Thoth instance
        :param thoth_sync: the Thoth instance
        :param institutions: a list of institutions from a Thoth instance to
        :return: a tuple of good institutions and good fundings
        """
        good_institutions = []
        good_fundings = []

        with tqdm(total=len(institutions), unit="insts") as pbar:
            for institution in institutions:
                inst, created = Institution.objects.get_or_create(
                    thoth_id=institution.institutionId,
                    thoth_instance=thoth_sync["endpoint"][0],
                )

                inst.institution_name = institution.institutionName
                inst.doi = institution.institutionDoi
                inst.ror = institution.ror
                inst.country_code = institution.countryCode
                inst.save()

                good_institutions.append(inst)

                for funding in institution.fundings:
                    fund, created = Funding.objects.get_or_create(
                        thoth_id=funding.institutionId,
                        thoth_instance=thoth_sync["endpoint"][0],
                    )

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

                    fund.save()

                pbar.update(1)

        return good_institutions, good_fundings

    def _sync_works(
        self, publisher_model, thoth_sync, works, do_contribs=False
    ) -> list:
        """
        Synchronizes works from the remote Thoth instance
        :param publisher_model: the publisher to use
        :param thoth_sync: the Thoth instance
        :param works: a list of works from a Thoth instance to sync
        :param do_contribs: whether to sync contributions
        :return: a list of new good institutions
        """
        new_insts = []

        with tqdm(total=len(works), unit="works") as pbar:
            for work in works:
                # build a work model
                work_model, created = Work.objects.get_or_create(
                    thoth_id=work.workId, thoth_instance=thoth_sync["endpoint"]
                )
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

                work_model.save()

                if do_contribs:
                    # this is for a second pass
                    # the reason is that we need to have created all
                    # institution objects before we can do contributions
                    new_insts = self._sync_contributions(
                        thoth_sync, work, work_model
                    )

                    self._sync_subjects(thoth_sync, work, work_model)

                pbar.update(1)

        return new_insts

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
            subject_model = Subject.objects.get_or_create(
                thoth_id=subject.subjectId,
                thoth_instance=thoth_sync["endpoint"],
                work=work_model,
            )[0]

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

            subject_model.save()

    @staticmethod
    def _sync_contributions(thoth_sync, work, work_model) -> list:
        """
        Synchronize contributors from Thoth to the local DB
        :param thoth_sync: the Thoth instance
        :param work: the work instance
        :param work_model: the work model instance
        :return: List of added institutions
        """

        new_good_institutions = []

        # build the contributions and contributors
        for contribution in work.contributions:
            # find or build the contributor and then update it
            contributor = contribution.contributor

            contributor_model = Contributor.objects.get_or_create(
                thoth_id=contributor.contributorId,
                thoth_instance=thoth_sync["endpoint"],
            )[0]

            contributor_model.first_name = contributor.firstName
            contributor_model.last_name = contributor.lastName
            contributor_model.full_name = contributor.fullName
            contributor_model.orcid = contributor.orcid
            contributor_model.thoth_id = contributor.contributorId

            contributor_model.save()

            # now save the contribution
            contribution_model = Contribution.objects.get_or_create(
                thoth_id=contribution.contributionId,
                thoth_instance=thoth_sync["endpoint"],
            )[0]

            for affil in contribution.affiliations:
                ror = None

                try:
                    print(f"Trying to find {affil.institution.ror}")

                    inst = Institution.objects.get(
                        ror=affil.institution.ror,
                    )
                    """
                    inst = Institution.objects.get(
                        thoth_id=affil.institution.institutionId,
                        thoth_instance=thoth_sync["endpoint"][0],
                    )
                    """

                    contribution_model.institutions.add(inst)
                    new_good_institutions.append(inst)

                    try:
                        ror = RORRecord.objects.get(ror_id=inst.ror)
                        inst.country_code = ror.country
                    except:
                        pass
                    inst.save()
                except Institution.DoesNotExist:
                    inst, created = Institution.objects.get_or_create(
                        thoth_id=affil.institution.institutionId,
                        thoth_instance=thoth_sync["endpoint"],
                    )

                    inst.institution_name = affil.institution.institutionName
                    try:
                        inst.ror = affil.institution.ror
                        ror = RORRecord.objects.get(ror_id=inst.ror)
                    except:
                        pass

                    if ror:
                        inst.country_code = ror.country
                        inst.save()

                    contribution_model.institutions.add(inst)
                    new_good_institutions.append(inst)
                except Institution.MultipleObjectsReturned:
                    insts = Institution.objects.filter(
                        ror=affil.institution.ror,
                    )

                    contribution_model.institutions.add(insts[0])
                    new_good_institutions.append(insts[0])

            contribution_model.contribution_ordinal = (
                contribution.contributionOrdinal
            )
            contribution_model.contribution_type = contribution.contributionType
            contributor_model.thoth_id = contribution.contributionId

            contribution_model.work = work_model

            contribution_model.contributor = contributor_model

            contribution_model.save()

            return new_good_institutions

    def _cleanup_institutions(
        self, good_institutions, good_fundings, ret_text
    ) -> None:
        """
        Cleans up orphaned institutions and fundings
        :param good_institutions: a list of good institutions
        :param good_fundings: a list of good fundings
        :param ret_text: the return text
        :return: None
        """

        # without main Thoth sync allowing more than 9999 records we can't
        # return the correct institutions for orphaning. This fix restores
        # working institution search.
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
                    institution.delete()
                    dead_insts += 1
                pbar.update(1)
        self.output(
            "Deleted {0} orphaned institutions (total: {1})".format(
                dead_insts, len(institutions)
            ),
            ret_text,
        )
        """

        self.output(
            "Cleaning up orphaned fundings (not associated with "
            "our publishers)",
            ret_text,
        )

        fundings = Funding.objects.all()
        dead_funds = 0
        with tqdm(total=len(fundings), unit="funds") as pbar:
            for fund in fundings:
                if not fund in good_fundings:
                    fund.delete()
                    dead_funds += 1
                pbar.update(1)
        self.output(
            "Deleted {0} orphaned fundings (total: {1})".format(
                dead_funds, len(fundings)
            ),
            ret_text,
        )
