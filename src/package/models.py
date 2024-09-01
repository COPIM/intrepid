import datetime
import os
import sys
import uuid
from _decimal import Decimal

import babel.numbers
import magic
from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.db.models import QuerySet
from django.http import HttpResponse
from django.utils import timezone
from django.utils.datastructures import OrderedSet
from django_bleach.models import BleachField

from access import models as access_models
from accounts import models as account_models
from initiatives import models as im
from package import utils
from vocab import models as vm

upload_storage = FileSystemStorage(
    location=settings.FILE_ROOT, base_url="/files"
)


def package_images_upload_path(instance, filename) -> str:
    """
    Upload path for package images
    :param instance: the instance of the model
    :param filename: the filename of the file
    :return: the path to upload the file to
    """
    # TODO: consider using PathLib
    try:
        filename = str(uuid.uuid4()) + "." + str(filename.split(".")[1])
    except IndexError:
        filename = str(uuid.uuid4())

    path = "package/images/"
    return os.path.join(path, filename)


class Country(models.Model):
    """
    A country represents a country in which a package is available.
    """

    name = models.CharField(
        max_length=50,
    )
    code = models.CharField(
        max_length=4,
    )
    currency = models.CharField(
        max_length=3,
        help_text="Use the currency code eg. GBP or USD",
    )
    catch_all = models.BooleanField(
        default=False,
        help_text="Whether this currency is a grouping, such as EUR",
    )

    class Meta:
        verbose_name_plural = "Countries"
        ordering = ("name",)

    def __str__(self):
        return "{} ({})".format(self.name, self.currency)


class BandingType(models.Model):
    """
    A banding type specifies the mode of a Banding (e.g. Jisc Collections)
    """

    is_fte = models.BooleanField(
        default=False,
        help_text="If this Banding Type is FTE related. You should only select "
        "FTE Banding Vocabs if True.",
    )
    name = models.CharField(
        max_length=255, help_text="Public name of the Banding Type.#,"
    )
    description = BleachField(
        help_text="Description that will appear on the banding selection section.",
    )
    active = models.BooleanField(
        default=True,
        help_text="If active new packages can be created with this Banding "
        "Type.",
    )
    vocabs = models.ManyToManyField(
        "vocab.BandingVocab",
        blank=True,
    )

    def __str__(self) -> str:
        return self.name

    def is_fte_display(self) -> str:
        """
        Returns a string to display in the admin for the is_fte field
        :return: A string: "Yes" if is_fte, "No" if not
        """
        if self.is_fte:
            return "Yes"
        return "No"

    def set_vocabs(self, ids, request) -> list[vm.BandingVocab]:
        """
        Sets vocabs for this BandingType
        :param ids: a list of IDs to set or unset
        :param request: the request object
        :return: a list of vocabs that were set
        """
        from vocab import utils as vocab_utils

        vocabs_to_set = vm.BandingVocab.objects.filter(
            pk__in=ids,
        )
        new_vocabs = []

        for vocab in vocabs_to_set:
            if vocab not in self.vocabs.all():
                self.vocabs.add(vocab)
                new_vocabs.append(vocab)

        for vocab in self.vocabs.all():
            if vocab not in vocabs_to_set:
                self.vocabs.remove(vocab)

        if new_vocabs:
            vocab_utils.notify_initiatives_new_vocabs(self, new_vocabs, request)

        return new_vocabs


class BandingManager(models.Manager):
    """
    Custom manager for Banding
    """

    def get_queryset(self) -> QuerySet["Banding"]:
        """
        Returns a queryset of Banding objects with related objects
        :return: a queryset of Banding objects with related objects
        """
        return (
            super(BandingManager, self)
            .get_queryset()
            .select_related("banding_type", "package", "vocab")
        )


class Banding(models.Model):
    """
    A banding represents a type of banding (e.g. Jisc Band 1) for a package
    """

    package = models.ForeignKey(
        "Package", on_delete=models.CASCADE, related_name="bandings"
    )
    banding_type = models.ForeignKey(
        BandingType,
        null=True,
        on_delete=models.CASCADE,
    )
    vocab = models.ForeignKey(
        "vocab.BandingVocab",
        null=True,
        on_delete=models.SET_NULL,
    )
    active = models.BooleanField(
        default=True,
    )
    order = models.PositiveIntegerField(
        default=99,
    )
    objects = BandingManager()

    def name(self) -> str:
        """
        Returns the name of the banding
        :return: the name of the banding
        """
        if self.vocab:
            return self.vocab.__str__()
        else:
            return "Unnamed banding"

    def __str__(self):
        return self.name()

    @property
    def fte_minimum(self) -> int | None:
        """
        Returns the minimum FTE for this banding
        :return: the minimum FTE for this banding
        """
        if self.vocab:
            return self.vocab.lower_limit
        return None

    @property
    def fte_maximum(self) -> int | None:
        """
        Returns the maximum FTE for this banding
        :return: the maximum FTE for this banding
        """
        if self.vocab:
            return self.vocab.upper_limit
        return None

    @property
    def fte_comparable(self) -> bool:
        """
        Returns whether this banding is comparable by FTE
        :return: True if comparable, otherwise False
        """
        return self.banding_type.is_fte


class PriceManager(models.Manager):
    """
    Custom manager for Price
    """

    def get_queryset(self) -> QuerySet["Price"]:
        """
        Returns a queryset of Price objects with related objects
        :return: a queryset of Price objects with related objects
        """
        return (
            super(PriceManager, self)
            .get_queryset()
            .select_related("banding", "country")
        )


class Price(models.Model):
    """
    A price point for a Banding in a particular currency.
    Loosely coupled with BandingTypeCurrencyEntry
    """

    banding = models.ForeignKey(
        Banding, on_delete=models.CASCADE, related_name="prices"
    )
    country = models.ForeignKey(
        Country,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="prices",
    )
    value = models.PositiveIntegerField(
        help_text="Value in the currency of the selected country",
    )
    default_currency = models.CharField(
        max_length=3,
        help_text="If this is a default price (e.g. it has no country) add a "
        "currency here using the three digit code. "
        "For example: USD or GBP",
    )
    objects = PriceManager()

    @staticmethod
    def collect() -> None:
        """
        A garbage collector for orphaned prices
        :return: None
        """
        # TODO: investigate if this can be removed

        return

    def __str__(self):
        if self.country:
            return utils.format_price(self.value, self.country.currency)
        else:
            return utils.format_price(self.value, "")


class BandingTypeCurrencyEntry(models.Model):
    """
    Ties a currency to a BandingTypeEntry
    """

    package = models.ForeignKey(
        "Package",
        null=True,
        on_delete=models.CASCADE,
    )
    banding_type_entry = models.ForeignKey(
        "BandingTypeEntry",
        null=True,
        on_delete=models.CASCADE,
    )

    country = models.ForeignKey(
        "Country",
        null=True,
        on_delete=models.CASCADE,
    )

    payment_processor = models.ForeignKey(
        "invoicing.PaymentProcessor",
        blank=True,
        null=True,
        help_text="Optional allow a regional payment processor to "
        "handle invoicing for this banding",
        on_delete=models.SET_NULL,
    )

    def __str__(self):
        return "{} ({}) in {}".format(
            self.country, self.banding_type_entry, self.package
        )


class BandingTypeEntry(models.Model):
    """
    This model glues a package to a banding type. If this exists, then a
    package has selected to use a particular banding type. E.g. Open Book Pub
    using Jisc Collections.
    """

    package = models.ForeignKey(
        "Package",
        null=True,
        on_delete=models.CASCADE,
    )

    banding_type = models.ForeignKey(
        BandingType,
        null=True,
        on_delete=models.CASCADE,
    )

    redirect_display = models.CharField(
        blank=True,
        null=True,
        default="",
        verbose_name="Redirect display",
        max_length=255,
    )

    redirect = models.URLField(
        blank=True, null=True, default="", verbose_name="Redirect URL"
    )

    def __str__(self):
        return "{} in {}".format(self.banding_type, self.package)


class BasePackage(models.Model):
    """
    Abstract base class for Package and PackageHistory
    """

    name = models.CharField(
        max_length=255,
        help_text="Name of the package",
    )
    description = BleachField(
        blank=True,
        null=True,
    )
    active = models.BooleanField(
        default=False,
        help_text="If unchecked, this package will be unavailable for signup.",
    )
    banding_type = models.ForeignKey(
        BandingType,
        null=True,
        on_delete=models.CASCADE,
    )
    pricing_display = models.CharField(
        max_length=255,
        help_text="Display version of pricing eg. £1000-£2000",
        null=True,
    )
    display_contract_length_months = models.PositiveIntegerField(
        help_text="Display version of contract length. Positive Integer eg. 12",
        null=True,
    )
    image = models.ImageField(
        upload_to=package_images_upload_path,
        null=True,
        blank=True,
    )
    subjects = models.ManyToManyField(
        "vocab.SubjectVocab",
        blank=True,
    )
    recommended = models.BooleanField(
        default=False,
        help_text="If set, will be ordered by the Recommended "
        "option on the Packages page.",
    )

    def __str__(self):
        return self.name

    class Meta:
        ordering = ("name",)

    def highlights(self) -> im.Highlights:
        """
        Return the highlights for this package
        :return: a queryset of highlights
        """
        return im.Highlights.objects.filter(package=self)[:4]


class Package(BasePackage):
    """
    A package is a collection of content that can be purchased by a customer.
    """

    # When adding a field that only staff should edit ensure that you pop it
    # ManagePackageForm.__init__ under if not user.is_staff so that normal
    # users do not see the field.
    initiative = models.ForeignKey(
        "initiatives.Initiative",
        on_delete=models.CASCADE,
        related_name="packages",
    )
    default_country = models.ForeignKey(
        Country,
        null=True,
        on_delete=models.SET_NULL,
    )
    meta_only = models.BooleanField(
        default=False,
        help_text="If this package is only available to be added to meta "
        "packages check this box.",
    )

    # who to notify on a signup
    signup_contacts = models.ManyToManyField(
        "access.Contact", blank=True, related_name="signup_contacts"
    )

    # who to notify on an access control change
    access_contacts = models.ManyToManyField(
        "access.Contact", blank=True, related_name="access_contacts"
    )

    # a list of stored fields for this package
    @property
    def stored_fields(self) -> OrderedSet:
        """
        Returns a full list of stored field answers for this package.
        These are not guaranteed accessible for any particular signup.
        :return: A list of fields
        """
        return OrderedSet(
            PackageSignupOrderFormAnswer.objects.filter(
                package_signup__associated_package=self
            )
            .values_list("order_form_answer__form_element_name", flat=True)
            .order_by("order_form_answer__form_element__order")
        )

    class Meta:
        ordering = ("name",)

    def active_display(self) -> str:
        """
        Returns a string to display in the admin for the active field
        :return: A string: "Yes" if active, "No" if not
        """
        if self.active:
            return "Yes"
        return "No"

    def set_contacts(self, ids, contact_type) -> None:
        """
        Sets contacts for this package
        :param ids: a list of IDs to set or unset
        :param contact_type: The ManyToMany field on which to operate. Should be
        either signup_contacts or access_contacts
        :return: None
        """
        contacts_to_set = access_models.Contact.objects.filter(
            pk__in=ids,
        )

        # add the set contacts
        for contact in contacts_to_set:
            if contact not in getattr(self, contact_type).all():
                getattr(self, contact_type).add(contact)

        # remove the unset contacts
        for contact in getattr(self, contact_type).all():
            if contact not in contacts_to_set:
                getattr(self, contact_type).remove(contact)

    def save_price_data(self, form) -> None:
        """
        Saves the price data
        :param form: the form to save
        :return: None
        """
        # TODO: evaluate use of this function in light of new pricing logic
        for k, v in form.cleaned_data.items():
            if k.startswith("banding-"):
                string, v_banding_pk = k.split("-")
                v_banding = vm.BandingVocab.objects.get(pk=v_banding_pk)
                banding, c = Banding.objects.get_or_create(
                    package=self,
                    banding_type=self.banding_type,
                    fte_vocab=v_banding,
                    defaults={
                        "name": v_banding.__str__,
                    },
                )
                price, c = Price.objects.get_or_create(
                    banding=banding,
                    default_currency=self.default_country.currency,
                    defaults={"value": v},
                )

                if not c:
                    price.value = v
                    price.default_currency = self.default_country.currency
                    price.save()

    @property
    def price_bandings(self) -> dict:
        """
        This returns a dictionary of BandingTypeCurrencyEntries that contains
        a dictionary of countries that contains a list of prices
        E.g. price_bandings[BandingTypeCurrencyEntry][Country] = [Prices]
        :return: a dictionary of BandingTypeCurrencyEntries that contains
        """
        # Fetch all related objects in one go
        banding_entries = (
            self.bandingtypecurrencyentry_set.all()
            .select_related("banding_type_entry__banding_type", "country")
            .prefetch_related("banding_type_entry__banding_type__vocabs")
        )
        price_objects = Price.objects.all().select_related("banding")
        prices = {}

        bandings = Banding.objects.all().select_related("banding_type")

        for banding_entry in banding_entries:
            prices[banding_entry] = {}

            # all available vocab types
            for (
                v_banding
            ) in banding_entry.banding_type_entry.banding_type.vocabs.all():
                for banding in bandings:
                    if (
                        banding.package == self
                        and banding.vocab == v_banding
                        and banding.banding_type
                        == banding_entry.banding_type_entry.banding_type
                    ):
                        try:
                            price = None
                            for price_obj in price_objects:
                                if (
                                    price_obj.banding == banding
                                    and price_obj.country
                                    == banding_entry.country
                                ):
                                    price = price_obj

                                """
                                # see if there are prices set
                                price = price_objects.get(
                                    banding=banding,
                                    country=banding_entry.country,
                                )
                                """

                            # if so, append to the list for each country
                            if price.country not in prices[banding_entry]:
                                prices[banding_entry][price.country] = []

                            prices[banding_entry][price.country].append(price)
                        except Price.DoesNotExist:
                            pass
                        except AttributeError:
                            pass

        return prices

    def display_price(self) -> str:
        """
        Gets a display string of the pricing for this package
        :return: a string of pricing display
        """

        # if the user is not logged in or no default currency is set
        # then return a price range
        bandings = Banding.objects.filter(
            package=self,
            banding_type=self.banding_type,
        )

        if len(bandings) == 0:
            return self._no_price_display()

        # pull out prices in the default currency for this package
        prices = Price.objects.filter(
            banding__in=bandings,
            country=self.default_country,
        )

        if len(prices) == 0:
            return self._no_price_display()

        low = sys.maxsize
        high = 0

        for price in prices:
            if price.value < low:
                low = price.value
            if price.value > high:
                high = price.value

        return (
            "From {0} to {1} (in {2})".format(
                babel.numbers.format_currency(
                    low, self.default_country.currency, locale="en_US"
                ),
                babel.numbers.format_currency(
                    high, self.default_country.currency, locale="en_US"
                ),
                self.default_country.currency,
            )
            if low != high
            else "Around {0}".format(
                babel.numbers.format_currency(
                    high, self.default_country.currency, locale="en_US"
                )
            )
        )

    def meta_packages(self) -> set:
        """
        Returns a list of meta packages that this package is a part of
        :return: set of meta packages
        """
        return self.metapackage_set.filter(active=True)

    @staticmethod
    def _no_price_display() -> str:
        """
        Returns a string to display when no pricing information is available
        :return: string
        """
        # TODO: this should be internationalised
        return "No Pricing Information"

    @property
    def standards(self) -> QuerySet[vm.PackageStandardAttestation]:
        """
        Returns a QuerySet of standards that this package is certified against
        :return: QuerySet of standards
        """
        return vm.PackageStandardAttestation.objects.filter(
            package=self,
        )


class MetaPackage(BasePackage):
    """
    A Meta Package is a collection of packages that are grouped together
    """

    packages = models.ManyToManyField(
        Package,
        through="MetaPackageLink",
        help_text="Select the packages that will make up this Meta Package.",
    )
    contact = models.ForeignKey(
        User,
        null=True,
        on_delete=models.SET_NULL,
        help_text="Contact person for this Meta Package.",
    )

    def initiative_list(self) -> set:
        """
        Returns a set of initiatives that this meta package is a part of
        :return: a set of initiatives
        """
        inits = [package.initiative for package in self.packages.all()]
        return set(inits)

    def standards(self) -> dict:
        """
        Returns a dictionary of standards for which this meta package is
        certified
        :return: a dictionary of standards
        """
        standards = {}
        for package in self.packages.all():
            for standard in package.standards:
                if standards.get(standard.standard.standard_name):
                    standards[standard.standard.standard_name].append(
                        {"package": package, "standard": standard}
                    )
                else:
                    standards[standard.standard.standard_name] = [
                        {"package": package, "standard": standard}
                    ]

        return {k: standards[k] for k in sorted(standards)}


class MetaPackageLink(models.Model):
    """
    A link between a package and a meta package
    """

    package = models.ForeignKey(
        Package,
        on_delete=models.CASCADE,
    )
    meta_package = models.ForeignKey(
        MetaPackage,
        on_delete=models.CASCADE,
    )
    order = models.PositiveIntegerField(
        default=99,
    )

    class Meta:
        verbose_name = "Package"
        verbose_name_plural = "Packages"

    def __str__(self):
        return "MP: {} part of {}".format(
            self.package.name,
            self.meta_package.name,
        )


class Basket(models.Model):
    """
    A basket is a collection of packages and meta packages that a user has
    """

    name = models.CharField(
        max_length=255,
        verbose_name="Quotation name",
    )
    account = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    session_id = models.TextField(
        blank=True,
        null=True,
    )
    packages = models.ManyToManyField(
        Package,
        blank=True,
    )
    meta_packages = models.ManyToManyField(
        MetaPackage,
        blank=True,
    )
    active = models.BooleanField(
        default=True,
        help_text="If False this basket will not show in active baskets.",
    )

    def package_set(self) -> set[Package]:
        """
        Returns a set of packages that are in this basket
        :return: a set of packages
        """
        package_list = cache.get("package_list")

        if not package_list:
            package_list = list()
            for package in self.packages.all():
                package_list.append(package)
            for meta_package in self.meta_packages.all():
                for package in meta_package.packages.all():
                    package_list.append(package)

            cache.set("package_list", package_list, 5)  # 5 seconds

        return set(package_list)

    def conflicts(self) -> list[dict]:
        """
        Checks if the packages and meta_packages conflict with one another.
        """
        conflicts = list()

        for package in self.packages.all():
            for meta_package in self.meta_packages.all():
                if package in meta_package.packages.all():
                    conflicts.append(
                        {
                            "package": package,
                            "meta_package": meta_package,
                        }
                    )
        return conflicts

    def list_of_conflicting_packages(self) -> set[Package]:
        """
        Returns a set of packages that conflict with one another
        :return: a set of packages
        """
        conflicting_packages = cache.get("conflicting_packages")

        if not conflicting_packages:
            conflicting_packages = list()

            for package in self.packages.all():
                for meta_package in self.meta_packages.all():
                    if package in meta_package.packages.all():
                        conflicting_packages.append(package)

            for meta_package in self.meta_packages.all():
                other_meta_packages = self.meta_packages.exclude(
                    pk=meta_package.pk
                )
                for omp in other_meta_packages:
                    conflicts = set(meta_package.packages.all()).intersection(
                        set(omp.packages.all())
                    )
                    for conflict in conflicts:
                        conflicting_packages.append(conflict)

            cache.set(
                "conflicting_packages", conflicting_packages, 5
            )  # 5 seconds

        return set(conflicting_packages)

    def cost(self, identifier, identifier_type="user") -> tuple[list, dict]:
        """
        Returns the cost of the basket
        :param identifier: the user or country to get the cost for
        :param identifier_type: the type of identifier
        :return: tuple of the cost of the basket and currency totals
        """
        package_costs = []

        if identifier_type == "user":
            user = account_models.User.objects.get(username=identifier)
            country = user.profile.default_currency
        else:
            country_pk = identifier.get("currency", None)
            country = Country.objects.filter(pk=country_pk).first()

        for package in self.packages.all():
            price, banding = utils.get_price_for_package(
                package=package,
                identifier=identifier,
                identifier_type=identifier_type,
                country=country if country else None,
            )

            package_costs.append(
                {"package": package, "cost": price, "banding": banding}
            )

        for mp in self.meta_packages.all():
            for package in mp.packages.all():
                price, banding = utils.get_price_for_package(
                    package=package,
                    identifier=identifier,
                    identifier_type=identifier_type,
                    country=country if country else None,
                )
                package_costs.append(
                    {"package": package, "cost": price, "banding": banding}
                )

        currency_totals = dict()
        completed_packages = []
        for pc in package_costs:
            if (pc.get("cost") and pc.get("banding")) and pc.get(
                "package"
            ) not in completed_packages:
                if pc.get("cost").country:
                    currency = pc.get("cost").country.currency
                else:
                    currency = pc.get("cost").default_currency

                # TODO: investigate transient false-positive linting here

                if currency_totals.get(currency):
                    currency_totals[currency] = (
                        currency_totals[currency] + pc.get("cost").value
                    )
                else:
                    currency_totals[currency] = pc.get("cost").value

                completed_packages.append(pc.get("package"))

        return package_costs, currency_totals

    def compliance_set(self) -> dict:
        """
        Returns a dict of standards covered by the packages in this basket.
        """
        compliance = {}
        for package in self.package_set():
            for package_standard in package.standards:
                if compliance.get(package_standard.standard):
                    compliance[package_standard.standard].append(
                        package_standard
                    )
                else:
                    compliance[package_standard.standard] = [package_standard]

        return compliance

    def get_best_bandings_for_form(
        self, identifier, identifier_type="user"
    ) -> set:
        """
        Returns the best bandings for the form
        :param identifier: the user or country to get the cost for
        :param identifier_type: the type of identifier
        :return: the cost of the basket
        """
        package_bandings_return = []

        if identifier_type == "user":
            user = account_models.User.objects.get(username=identifier)
            currency = user.profile.default_currency
        else:
            currency_pk = identifier.get("currency")
            currency = Country.objects.filter(
                pk=currency_pk,
            ).first()

        if currency:
            # find catchalls
            catch_all_matching_currency = Country.objects.filter(
                currency=currency.currency, catch_all=True
            ).first()
            if catch_all_matching_currency:
                suitable_prices = Price.objects.filter(
                    country__currency=catch_all_matching_currency.currency,
                    country__catch_all=True,
                ).select_related("banding__banding_type")

                package_bandings_return = package_bandings_return + [
                    price.banding for price in suitable_prices
                ]

            bandings = Banding.objects.all().select_related("banding_type")

            for package in self.packages.all():
                package_bandings = bandings.filter(
                    package=package,
                )

                prices = Price.objects.filter(
                    banding__in=package_bandings,
                ).select_related("banding__banding_type")
                suitable_prices = prices.filter(
                    country=currency,
                ).select_related("banding__banding_type")
                if suitable_prices:
                    package_bandings_return = package_bandings_return + [
                        price.banding for price in suitable_prices
                    ]
                else:
                    suitable_prices = prices.filter(
                        country=package.default_country,
                    ).select_related("banding__banding_type")

                    if suitable_prices:
                        package_bandings_return = package_bandings_return + [
                            price.banding for price in suitable_prices
                        ]

            for mp in self.meta_packages.all():
                for package in mp.packages.all():
                    package_bandings = bandings.filter(
                        package=package,
                    )
                    prices = Price.objects.filter(
                        banding__in=package_bandings,
                    ).select_related("banding__banding_type")
                    suitable_prices = prices.filter(
                        country=currency,
                    ).select_related("banding__banding_type")
                    if suitable_prices:
                        package_bandings_return = package_bandings_return + [
                            price.banding for price in suitable_prices
                        ]
                    else:
                        if not catch_all_matching_currency:
                            suitable_prices = prices.filter(
                                country=package.default_country,
                            ).select_related("banding__banding_type")

                            if suitable_prices:
                                package_bandings_return = (
                                    package_bandings_return
                                    + [
                                        price.banding
                                        for price in suitable_prices
                                    ]
                                )

        return set(
            [
                banding.banding_type
                for banding in package_bandings_return
                if not banding.banding_type.is_fte
            ]
        )


class AggregateForm(models.Model):
    """
    A form that aggregates multiple forms together.
    """

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200)

    intro = models.TextField(
        help_text="Message displayed at the start of the review form."
    )
    thanks = models.TextField(
        help_text="Message displayed after the reviewer is finished."
    )

    elements = models.ManyToManyField("AggregateFormElement")
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return "{0} - {1}".format(self.id, self.name)


def element_kind_choices() -> tuple:
    """
    Returns the choices for the kind of element
    :return: the choices
    """
    return (
        ("text", "Text Field"),
        ("textarea", "Text Area"),
        ("check", "Check Box"),
        ("select", "Select"),
        ("email", "Email"),
        ("upload", "Upload"),
        ("date", "Date"),
    )


def element_width_choices() -> tuple:
    """
    Returns the choices for the width of the element
    :return: the choices
    """
    return (
        ("large-4 columns", "third"),
        ("large-6 columns", "half"),
        ("large-12 columns", "full"),
    )


class BaseAggregateFormElement(models.Model):
    """
    A form element that can be used in an aggregate form.
    """

    name = models.CharField(max_length=200)
    kind = models.CharField(max_length=50, choices=element_kind_choices())
    choices = models.CharField(
        max_length=1000,
        null=True,
        blank=True,
        help_text="Separate choices with a |.",
    )
    required = models.BooleanField(default=True)
    order = models.IntegerField()
    width = models.CharField(max_length=20, choices=element_width_choices())
    help_text = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ("order", "name")
        abstract = True

    def __str__(self):
        return "{0} ({1})".format(self.name, self.kind)

    def choices_list(self) -> None:
        # TODO: can be removed?
        if self.choices:
            return


class AggregateFormElement(BaseAggregateFormElement):
    """
    A form element that can be used in an aggregate form.
    """

    class Meta(BaseAggregateFormElement.Meta):
        pass

    def snapshot(self, answer) -> "FrozenAggregateFormElement":
        """
        Creates a snapshot of the element
        :param answer: the answer to snapshot
        :return: the snapshot
        """
        frozen, _ = FrozenAggregateFormElement.objects.update_or_create(
            answer=answer,
            defaults=dict(
                form_element=self,
                name=self.name,
                kind=self.kind,
                choices=self.choices,
                required=self.required,
                order=self.order,
                width=self.width,
                help_text=self.help_text,
            ),
        )
        return frozen


class AggregateAssignmentAnswer(models.Model):
    """
    An answer to an aggregate assignment.
    """

    original_element = models.ForeignKey(
        AggregateFormElement, null=True, on_delete=models.SET_NULL
    )
    answer = models.TextField(blank=True, null=True)
    edited_answer = models.TextField(null=True, blank=True)
    author_can_see = models.BooleanField(default=True)

    def __str__(self):
        return "{0}".format(self.element)

    @property
    def element(self) -> BaseAggregateFormElement:
        """
        Returns the frozen element
        :return: the element
        """
        return self.frozen_element


class FrozenAggregateFormElement(BaseAggregateFormElement):
    """A snapshot of a form element at the time an answer is created"""

    form_element = models.ForeignKey(
        AggregateFormElement, null=True, on_delete=models.SET_NULL
    )
    answer = models.OneToOneField(
        AggregateAssignmentAnswer,
        related_name="frozen_element",
        on_delete=models.CASCADE,
    )

    class Meta(BaseAggregateFormElement.Meta):
        pass


class AggregateFormAnswer(models.Model):
    """
    An answer to an aggregate form.
    """

    form_element = models.ForeignKey(
        AggregateFormElement, on_delete=models.CASCADE
    )
    answer = models.TextField()


class PackageFormElement(models.Model):
    """
    A form element that can be used in a package form.
    """

    form_element = models.ForeignKey(
        AggregateFormElement, null=True, on_delete=models.CASCADE
    )
    package = models.ForeignKey(Package, null=True, on_delete=models.CASCADE)


class PackageDocument(models.Model):
    """
    A document associated with a package (e.g. a contract)
    """

    package = models.ForeignKey(Package, on_delete=models.CASCADE)
    pdf_file = models.FileField(blank=True, upload_to="documents")
    name = models.CharField(max_length=255, blank=True, null=True)

    def create_historical_record(self) -> "PackageDocumentHistorical":
        """
        Duplicating this object including copying the file
        :return: the historical record
        """
        historical_record = PackageDocumentHistorical()
        new_file = ContentFile(self.pdf_file.read(), name=self.pdf_file.name)
        historical_record.pdf_file = new_file
        historical_record.name = self.name
        historical_record.package_document = self
        historical_record.save()
        return historical_record

    def __str__(self):
        return self.name


class FrozenPackageDocument(models.Model):
    """
    A frozen document associated when a package is bought (e.g. a set of
    merged PDF contracts)
    """

    final_zip = models.FileField(
        blank=True, upload_to="private_documents", storage=upload_storage
    )
    associated_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    associated_session = models.TextField(
        blank=True,
        null=True,
    )
    subject_line = models.TextField(blank=True, null=True)
    date_of_freeze = models.DateField(
        blank=True, null=True, default=datetime.date.today
    )


class CustomPackageDocument(models.Model):
    """
    A document associated with a package (e.g. a contract)
    """

    package_signup = models.OneToOneField(
        "PackageSignup", on_delete=models.CASCADE
    )
    pdf_file = models.FileField(blank=True, upload_to="documents")
    name = models.CharField(max_length=255, blank=True, null=True)


class PackageDocumentHistorical(models.Model):
    """
    An old version of an existing PackageDocument.
    """

    package_document = models.ForeignKey(
        "PackageDocument",
        on_delete=models.CASCADE,
    )
    pdf_file = models.FileField(blank=True, upload_to="documents")
    name = models.CharField(max_length=255, blank=True, null=True)

    def revert(self) -> None:
        """
        Reverts the package document to this historical version
        :return: None
        """
        historical_record = PackageDocumentHistorical()
        new_file = ContentFile(
            self.package_document.pdf_file.read(),
            name=self.package_document.pdf_file.name,
        )
        historical_record.pdf_file = new_file
        historical_record.name = self.package_document.name
        historical_record.package_document = self.package_document
        historical_record.save()

        self.package_document.name = self.name
        self.package_document.pdf_file = ContentFile(
            self.pdf_file.read(),
            name=self.pdf_file.name,
        )
        self.package_document.save()


class OrderFormAnswer(models.Model):
    """
    An answer to an order form.
    """

    order = models.ForeignKey(
        "Order",
        on_delete=models.CASCADE,
    )
    form_element = models.ForeignKey(
        AggregateFormElement,
        null=True,
        on_delete=models.SET_NULL,
    )
    form_element_name = models.CharField(
        max_length=300,
        help_text="Copied from PackageFormElement as a backup in the event "
        "it is deleted.",
    )
    answer = models.TextField()


class PackageSignupOrderFormAnswer(models.Model):
    """
    This model links a form answer to a signup
    """

    package_signup = models.ForeignKey(
        "PackageSignup", on_delete=models.CASCADE
    )

    order_form_answer = models.ForeignKey(
        "OrderFormAnswer", on_delete=models.CASCADE
    )

    def __str__(self) -> str:
        return "{} for {} on signup {}".format(
            self.order_form_answer.form_element_name,
            self.package_signup.associated_package,
            self.package_signup.pk,
        )


class Order(models.Model):
    """
    An order for a package.
    """

    # UUID order number
    order_number = models.UUIDField(
        default=uuid.uuid4,
        help_text="Order numbers are automatically generated.",
    )

    # the user who signed up (stored for convenience)
    associated_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        help_text="The account to whom the order belongs.",
        blank=True,
        null=True,
    )
    session_id = models.TextField(
        blank=True,
        null=True,
    )
    email_address = models.EmailField(
        blank=True,
        null=True,
    )

    # the term period of this signup (e.g. 2020-2021)
    valid_period = models.CharField(max_length=255, blank=True, null=True)

    # the associated frozen document zip file
    document = models.ForeignKey(
        FrozenPackageDocument, null=True, on_delete=models.CASCADE
    )

    # the order date
    order_date = models.DateField(
        blank=True, null=True, default=datetime.date.today
    )

    # the associated basket for this order
    basket = models.ForeignKey(
        Basket,
        null=True,
        on_delete=models.SET_NULL,
        help_text="The associated basket record for this order.",
    )

    status = models.CharField(
        max_length=20,
        default="new",
        choices=(
            ("new", "New"),
            ("provisional", "Provisional"),
            ("complete", "Complete"),
            ("lapsed", "Lapsed"),
        ),
    )

    proxy_signup_information = models.TextField(
        blank=True,
        null=True,
        help_text="Storage area for proxy signup information.",
    )

    private_images = models.ManyToManyField(
        "intrepid.PrivateImage",
        blank=True,
    )

    initiative = models.ForeignKey(
        "initiatives.Initiative",
        blank=True,
        null=True,
        help_text="If signup inserted by initiative store here.",
        on_delete=models.CASCADE,
    )
    converted_currency = models.CharField(
        max_length=3,
        blank=True,
        null=True,
    )
    converted_value = models.DecimalField(
        blank=True, null=True, decimal_places=2, max_digits=100
    )
    platform_fee = models.DecimalField(
        blank=True,
        null=True,
        decimal_places=2,
        max_digits=100,
    )

    class Meta:
        ordering = ("-order_date",)

    def get_currency_totals_completed_order(self) -> dict[str, Decimal]:
        """
        Returns the currency totals for a completed order
        :return: dict
        """
        if self.converted_value:
            return {
                self.converted_currency: self.converted_value,
            }
        else:
            identifier = (
                self.associated_user
                if self.associated_user
                else self.session_id
            )
            identifier_type = (
                "user" if self.associated_user else self.session_id
            )
            package_costs, currency_totals = self.basket.cost(
                identifier=identifier,
                identifier_type=identifier_type,
            )
            return currency_totals

    def parcel_data(self, signups) -> None:
        """
        This function takes a list of signups and saves a list of dicts
        :param signups: list of signups
        :return: None
        """
        # this function doles the data out to individual signups
        for signup in signups:
            form_elements = PackageFormElement.objects.filter(
                package=signup.associated_package
            )

            for fe in form_elements:
                signup_answer = PackageSignupOrderFormAnswer()
                signup_answer.order_form_answer = OrderFormAnswer.objects.get(
                    form_element_name=fe.form_element.name, order=self
                )
                signup_answer.package_signup = signup
                signup_answer.save()

    def get_order_form_details(self) -> list[dict[str, str]]:
        """
        Returns a list of dicts containing the order form details
        :return: list of dicts
        """
        details = []
        for answer in self.orderformanswer_set.all():
            details.append(
                {
                    "question": answer.form_element_name,
                    "answer": answer.answer,
                }
            )
        return details

    def __str__(self):
        return "Order #{0}".format(self.order_number)

    def has_processor(self, user) -> bool:
        """
        Returns true if the user has a payment processor for this order
        :param user: the user to check
        :return: bool
        """
        packages = self.packagesignup_set.all()

        for package in packages:
            if (
                package.payment_processor
                and package.payment_processor.is_member(user)
            ):
                return True

        return False

    @property
    def package_set(self) -> set[Package]:
        """
        Returns a set of packages associated with this order
        :return: set
        """
        packages = list(
            package.associated_package
            for package in self.packagesignup_set.all()
        )
        return set(packages)

    @property
    def data_to_collect(self) -> OrderedSet:
        """
        Returns an OrderedSet of the field names that will be collected for
        this basket
        :return: OrderedSet
        """
        package_set = self.package_set
        data_to_collect = OrderedSet(
            fe.form_element
            for fe in PackageFormElement.objects.filter(
                package__in=package_set
            ).order_by("form_element__order")
        )
        return data_to_collect

    def save_order_form(self, form) -> None:
        """
        Saves the order form
        :param form: the form to save
        :return: None
        """
        self.email_address = form.cleaned_data.get("email_address")
        for k, v in form.cleaned_data.items():
            if not k == "email_address":
                form_element = AggregateFormElement.objects.get(pk=k)
                answer, _ = OrderFormAnswer.objects.update_or_create(
                    order=self,
                    form_element=form_element,
                    defaults={
                        "answer": v,
                        "form_element_name": form_element.name,
                    },
                )

    def rebuild_docs(self, request) -> None:
        """
        Rebuilds the docs for this order
        :param request: the request
        :return: None
        """
        document = utils.generate_package_docs_zip(self, request)
        utils.unlink_frozen_doc(self)
        self.document = document
        self.save()


class PackageSignup(models.Model):
    """
    A signup to a package
    """

    # the user who signed up
    associated_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )

    # if no user, session key
    associated_session = models.TextField(blank=True, null=True)

    # the order this signup was part of
    associated_order = models.ForeignKey(Order, on_delete=models.CASCADE)

    # the package that was signed up to
    associated_package = models.ForeignKey(Package, on_delete=models.CASCADE)

    banding = models.ForeignKey(
        Banding,
        on_delete=models.CASCADE,
        null=True,
    )

    # the signup date
    signup_date = models.DateTimeField(
        blank=True, null=True, default=timezone.now
    )

    # price and currency for the signup
    price = models.IntegerField(blank=True, null=True)

    currency = models.ForeignKey(
        Country,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )

    status = models.CharField(
        max_length=20,
        default="new",
        choices=(
            ("new", "New"),
            ("provisional", "Provisional"),
            ("complete", "Complete"),
            ("lapsed", "Lapsed"),
        ),
    )

    initiative_approved = models.DateTimeField(
        blank=True,
        null=True,
    )
    initiative_approved_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="initiative_approved_by",
        blank=True,
        null=True,
    )
    organisation_approved = models.DateTimeField(
        blank=True,
        null=True,
    )

    def external(self) -> str:
        """
        Returns a redirect field if one exists
        :return: str
        """
        try:
            return BandingTypeEntry.objects.get(
                banding_type=self.banding.banding_type,
                package=self.associated_package,
            ).redirect
        except BandingTypeEntry.DoesNotExist:
            return ""

    def external_display(self) -> str:
        """
        Returns a redirect field if one exists
        :return: str
        """
        try:
            return BandingTypeEntry.objects.get(
                banding_type=self.banding.banding_type,
                package=self.associated_package,
            ).redirect_display
        except BandingTypeEntry.DoesNotExist:
            return ""

    @property
    def stored_fields(self) -> list:
        """
        Returns a full list of stored field answers for this signup.
        These should be guaranteed accessible for this signup.
        :return: A list of fields
        """
        return PackageSignupOrderFormAnswer.objects.filter(
            package_signup=self
        ).values_list("order_form_answer__form_element_name", flat=True)

    def stored_answer(self, field) -> str:
        """
        Returns a stored answer or empty string if it does not exist
        :param field: The field name
        :return: str
        """
        try:
            return PackageSignupOrderFormAnswer.objects.get(
                package_signup=self, order_form_answer__form_element_name=field
            ).order_form_answer.answer
        except PackageSignupOrderFormAnswer.DoesNotExist:
            return ""

    def stored_answers(self) -> QuerySet[PackageSignupOrderFormAnswer]:
        """
        Returns a dict of stored answers
        :return: QuerySet of PackageSignupOrderFormAnswer
        """
        return PackageSignupOrderFormAnswer.objects.filter(package_signup=self)

    def __str__(self) -> str:
        return "{} to {} for {} {}".format(
            self.associated_user,
            self.associated_package,
            self.price,
            self.currency,
        )

    @property
    def payment_processor(self) -> str:
        """
        Returns the payment processor for this signup
        :return: str
        """
        # see if we can find a currency entry for this banding
        return BandingTypeCurrencyEntry.objects.get(
            banding_type_entry__in=(
                self.banding.banding_type.bandingtypeentry_set.all()
            ),
            country=self.currency,
            package=self.associated_package,
        ).payment_processor

    @property
    def formatted_price(self) -> str:
        """
        Returns a formatted price
        :return: str
        """
        return utils.format_price(self.price, self.currency.currency)


class MediaFile(models.Model):
    """
    A media file for a package
    """

    name = models.CharField(
        max_length=255,
        help_text="Descriptive name of the file.",
    )
    file = models.FileField(
        blank=True,
        upload_to="private_documents",
        storage=upload_storage,
    )
    package = models.ForeignKey(
        "Package",
        on_delete=models.CASCADE,
    )
    date_uploaded = models.DateTimeField(
        default=timezone.now,
    )

    class Meta:
        ordering = ("name", "date_uploaded")

    def mime(self) -> str:
        """
        Returns the mime type of the file
        :return: str
        """
        return magic.from_file(self.file.path, mime=True)

    def unlink_file(self) -> None:
        """
        Unlinks the file from the filesystem
        :return: None
        """
        if self.file and os.path.isfile(self.file.path):
            os.unlink(self.file.path)

    def serve_file(self) -> HttpResponse:
        """
        Serve a file
        :return: HttpResponse
        """

        from intrepid.utils import serve_file

        return serve_file(
            path=self.file.path, filename=self.file.name, mime=self.mime
        )


class PreCalcMinMax(models.Model):
    package = models.ForeignKey(
        "Package",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    meta_package = models.ForeignKey(
        "MetaPackage",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    country = models.ForeignKey(
        "Country",
        on_delete=models.CASCADE,
    )
    min_amount = models.IntegerField()
    max_amount = models.IntegerField()

    def __str__(self):
        return "{0} to {1}".format(
            babel.numbers.format_currency(
                self.min_amount, self.country.currency, locale="en_US"
            ),
            babel.numbers.format_currency(
                self.max_amount, self.country.currency, locale="en_US"
            ),
        )

    def get_package(self):
        if self.package:
            return self.package.name
        if self.meta_package:
            return self.meta_package
        return "No package associated with pre calc price"
