"""
Comparison tests for view_basket (original) vs fast_view_basket (optimized).

These tests verify that for multiple package and meta-package basket
configurations, both views produce identical template context and rendered
HTML output.

Uses fixtures/test_package.json which provides:
  - 20 Initiatives (pk 1-20)
  - 3 Countries (GBP pk=999, USD pk=998, EUR pk=997)
  - 2 BandingTypes: FTE pk=100 (8 vocabs 100-107),
    Choice pk=101 (8 vocabs 108-115)
  - 50 Packages (pk 100-149) across 20 initiatives, with 10 different
    banding-type / currency configurations
  - 10 MetaPackages (pk 300-309) with 3-18 packages each, overlapping
    membership creating 39 conflict points
  - 880 prices across 520 bandings

Additional objects (SiteSetup, SiteText, User, Profile,
AccountBandingChoices) are created programmatically in setUpTestData.
"""

import re
import time
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.contrib.sessions.backends.db import SessionStore
from django.core.management import call_command
from django.test import TestCase, RequestFactory

from accounts.models import AccountBandingChoices, Profile
from cms.models import SiteText
from intrepid.models import SiteSetup
from package import forms, models, utils, views
from vocab.models import BandingVocab


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _AnonymousUser:
    """Minimal stand-in for an anonymous user."""

    is_authenticated = False
    pk = None

    def __str__(self):
        return "AnonymousUser"


# ---------------------------------------------------------------------------
# Shared fixture mixin
# ---------------------------------------------------------------------------


class BasketFixtureMixin:
    """
    Loads ``fixtures/test_package.json`` (20 initiatives, 50 packages,
    10 metas, 1825 objects) and creates the supporting objects needed by
    views and forms.

    Package config cycle (repeats every 10 PKs starting at 100):
      0: FTE+Choice / GBP+USD+EUR   (pk 100, 110, 120, 130, 140)
      1: FTE / GBP                   (pk 101, 111, 121, 131, 141)
      2: FTE / GBP+USD               (pk 102, 112, 122, 132, 142)
      3: Choice / GBP                (pk 103, 113, 123, 133, 143)
      4: FTE+Choice / GBP+USD        (pk 104, 114, 124, 134, 144)
      5: FTE / GBP+EUR               (pk 105, 115, 125, 135, 145)
      6: Choice / USD                (pk 106, 116, 126, 136, 146)
      7: FTE+Choice / GBP            (pk 107, 117, 127, 137, 147)
      8: FTE / EUR                   (pk 108, 118, 128, 138, 148)
      9: Choice / GBP+USD            (pk 109, 119, 129, 139, 149)
    """

    @classmethod
    def setUpTestData(cls):
        # ---- Load fixture (includes 20 initiatives, 50 packages, etc.) ----
        call_command("loaddata", "test_package", verbosity=0)

        # ---- Countries ----
        cls.country_gbp = models.Country.objects.get(pk=999)
        cls.country_usd = models.Country.objects.get(pk=998)
        cls.country_eur = models.Country.objects.get(pk=997)

        # ---- BandingTypes ----
        cls.fte_banding_type = models.BandingType.objects.get(pk=100)
        cls.choice_banding_type = models.BandingType.objects.get(pk=101)

        # ---- All 50 packages (ordered by pk) ----
        cls.all_packages = list(
            models.Package.objects.filter(
                pk__gte=100, pk__lte=149,
            ).order_by("pk")
        )

        # ---- Named references for targeted tests ----
        cls.pkg_all_combos = models.Package.objects.get(pk=100)
        cls.pkg_simple_fte = models.Package.objects.get(pk=101)
        cls.pkg_fte_multi_curr = models.Package.objects.get(pk=102)
        cls.pkg_simple_choice = models.Package.objects.get(pk=103)
        cls.pkg_dual_multi = models.Package.objects.get(pk=104)
        cls.pkg_fte_gbp_eur = models.Package.objects.get(pk=105)
        cls.pkg_choice_usd = models.Package.objects.get(pk=106)
        cls.pkg_dual_gbp = models.Package.objects.get(pk=107)
        cls.pkg_fte_eur = models.Package.objects.get(pk=108)
        cls.pkg_choice_multi = models.Package.objects.get(pk=109)

        # ---- Convenience subsets ----
        # GBP-only packages (no currency conversion needed)
        cls.gbp_only_packages = [
            models.Package.objects.get(pk=pk)
            for pk in [101, 103, 107, 111, 113, 117, 121, 123, 127]
        ]

        # ---- All 10 meta packages (ordered by pk) ----
        cls.all_metas = list(
            models.MetaPackage.objects.filter(
                pk__gte=300, pk__lte=309,
            ).order_by("pk")
        )
        cls.meta_18 = models.MetaPackage.objects.get(pk=300)
        cls.meta_15 = models.MetaPackage.objects.get(pk=301)
        cls.meta_3 = models.MetaPackage.objects.get(pk=309)

        # ---- SiteSetup ----
        cls.site_setup = SiteSetup.objects.create(
            site_name="Test Site",
            enable_signup=True,
            enable_meta_package_signup=True,
            enable_individual_package_signup=True,
            fee_amount=5,
            fallback_currency="GBP",
        )

        # ---- SiteText entries required by FTEForm / FastFTEForm ----
        for key in (
            "select_currency_note",
            "fte_student_count_prompt",
            "institutions_fte",
            "your_currency",
            "after_currency_bandings_info",
            "institution_details",
            "included_within_offers",
        ):
            SiteText.objects.get_or_create(
                key=key,
                defaults={
                    "body": key.replace("_", " ").title(),
                    "help_text": "",
                    "rich_text": False,
                    "frontend": False,
                },
            )

        # ---- User + Profile ----
        cls.user = User.objects.create_user(
            username="testuser", password="testpass123",
            email="test@example.com",
        )
        profile, _ = Profile.objects.get_or_create(account=cls.user)
        profile.fte = 12000  # falls in "Large" tier (10,001-20,000)
        profile.default_currency = cls.country_gbp
        profile.save()
        cls.profile = profile

        # ---- AccountBandingChoices (for choice-based banding type) ----
        AccountBandingChoices.objects.create(
            account=cls.user,
            banding_type=cls.choice_banding_type,
            banding_type_vocab=BandingVocab.objects.get(pk=113),
        )


# ---------------------------------------------------------------------------
# Model-level: price_bandings
# ---------------------------------------------------------------------------


class TestFastPriceBandings(BasketFixtureMixin, TestCase):
    """Verify fast_price_bandings produces identical output to price_bandings."""

    def _compare(self, package):
        original = package.price_bandings

        if "fast_price_bandings" in package.__dict__:
            del package.__dict__["fast_price_bandings"]
        fast = package.fast_price_bandings

        self.assertEqual(
            set(original.keys()), set(fast.keys()),
            "Banding entry keys differ",
        )
        for entry_key in original:
            orig_inner = original[entry_key]
            fast_inner = fast[entry_key]
            self.assertEqual(
                set(orig_inner.keys()), set(fast_inner.keys()),
                "Country keys differ for {}".format(entry_key),
            )
            for country_key in orig_inner:
                orig_pks = sorted(p.pk for p in orig_inner[country_key])
                fast_pks = sorted(p.pk for p in fast_inner[country_key])
                self.assertEqual(
                    orig_pks, fast_pks,
                    "Price PKs differ for {} / {}".format(
                        entry_key, country_key,
                    ),
                )

    def test_all_combos(self):
        """FTE+Choice / GBP+USD+EUR — maximum complexity."""
        self._compare(self.pkg_all_combos)

    def test_simple_fte(self):
        """FTE / GBP — simplest case."""
        self._compare(self.pkg_simple_fte)

    def test_fte_multi_currency(self):
        """FTE / GBP+USD."""
        self._compare(self.pkg_fte_multi_curr)

    def test_simple_choice(self):
        """Choice / GBP."""
        self._compare(self.pkg_simple_choice)

    def test_dual_multi_currency(self):
        """FTE+Choice / GBP+USD."""
        self._compare(self.pkg_dual_multi)

    def test_fte_gbp_eur(self):
        """FTE / GBP+EUR."""
        self._compare(self.pkg_fte_gbp_eur)

    def test_choice_usd_only(self):
        """Choice / USD — foreign currency only."""
        self._compare(self.pkg_choice_usd)

    def test_dual_gbp_only(self):
        """FTE+Choice / GBP."""
        self._compare(self.pkg_dual_gbp)

    def test_fte_eur_only(self):
        """FTE / EUR."""
        self._compare(self.pkg_fte_eur)

    def test_choice_multi_currency(self):
        """Choice / GBP+USD."""
        self._compare(self.pkg_choice_multi)


# ---------------------------------------------------------------------------
# Model-level: list_of_conflicting_packages
# ---------------------------------------------------------------------------


class TestFastListOfConflictingPackages(BasketFixtureMixin, TestCase):
    """
    Verify fast_list_of_conflicting_packages matches the original for
    various basket configurations.
    """

    def _compare(self, basket):
        original = basket.list_of_conflicting_packages()
        fast = basket.fast_list_of_conflicting_packages()
        self.assertEqual(original, fast)

    def test_empty_basket(self):
        basket = models.Basket.objects.create(
            name="Empty", account=self.user, active=True,
        )
        self._compare(basket)

    def test_packages_only_no_conflicts(self):
        basket = models.Basket.objects.create(
            name="Pkgs only", account=self.user, active=True,
        )
        basket.packages.add(*self.gbp_only_packages[:5])
        self._compare(basket)

    def test_two_metas_with_overlap(self):
        """meta_18 and meta_15 share packages -> conflicts."""
        basket = models.Basket.objects.create(
            name="Meta overlap", account=self.user, active=True,
        )
        basket.meta_packages.add(self.meta_18, self.meta_15)
        self._compare(basket)

    def test_direct_and_meta_overlap(self):
        """pkg 100 is both direct and inside meta_18 -> conflict."""
        basket = models.Basket.objects.create(
            name="Direct+meta", account=self.user, active=True,
        )
        basket.packages.add(self.pkg_all_combos)
        basket.meta_packages.add(self.meta_18)
        self._compare(basket)

    def test_all_metas(self):
        """All 10 meta packages — lots of overlaps."""
        basket = models.Basket.objects.create(
            name="All metas", account=self.user, active=True,
        )
        basket.meta_packages.add(*self.all_metas)
        self._compare(basket)

    def test_single_meta(self):
        basket = models.Basket.objects.create(
            name="Single meta", account=self.user, active=True,
        )
        basket.meta_packages.add(self.meta_3)
        self._compare(basket)

    def test_full_basket(self):
        """All 50 packages + all 10 metas."""
        basket = models.Basket.objects.create(
            name="Full", account=self.user, active=True,
        )
        basket.packages.add(*self.all_packages)
        basket.meta_packages.add(*self.all_metas)
        self._compare(basket)


# ---------------------------------------------------------------------------
# Model-level: cost
# ---------------------------------------------------------------------------


class TestFastCost(BasketFixtureMixin, TestCase):
    """
    Verify fast_cost returns the same package_costs and currency_totals
    as the original cost method.
    """

    def _compare(self, basket):
        identifier = self.user
        identifier_type = "user"
        country = self.user.profile.default_currency

        orig_costs, orig_totals = basket.cost(
            identifier=identifier, identifier_type=identifier_type,
        )
        fast_costs, fast_totals = basket.fast_cost(
            identifier=identifier, identifier_type=identifier_type,
            country=country,
        )

        self.assertEqual(
            len(orig_costs), len(fast_costs),
            "package_costs length differs",
        )
        for i, (orig, fast) in enumerate(zip(orig_costs, fast_costs)):
            self.assertEqual(
                orig["package"].pk, fast["package"].pk,
                "package_costs[{}].package differs".format(i),
            )
            if orig["cost"] == 0:
                self.assertEqual(
                    fast["cost"], 0,
                    "package_costs[{}].cost: expected 0".format(i),
                )
            else:
                self.assertEqual(
                    orig["cost"].pk, fast["cost"].pk,
                    "package_costs[{}].cost PK differs".format(i),
                )
                self.assertEqual(
                    orig["cost"].value, fast["cost"].value,
                    "package_costs[{}].cost value differs".format(i),
                )
            if orig["banding"] is None:
                self.assertIsNone(
                    fast["banding"],
                    "package_costs[{}].banding: expected None".format(i),
                )
            else:
                self.assertEqual(
                    orig["banding"].pk, fast["banding"].pk,
                    "package_costs[{}].banding PK differs".format(i),
                )

        self.assertEqual(orig_totals, fast_totals, "currency_totals differ")

    def test_single_package(self):
        basket = models.Basket.objects.create(
            name="Single", account=self.user, active=True,
        )
        basket.packages.add(self.pkg_all_combos)
        self._compare(basket)

    def test_five_gbp_packages(self):
        basket = models.Basket.objects.create(
            name="5 GBP", account=self.user, active=True,
        )
        basket.packages.add(*self.gbp_only_packages[:5])
        self._compare(basket)

    def test_packages_mixed_currency(self):
        basket = models.Basket.objects.create(
            name="Mixed curr", account=self.user, active=True,
        )
        basket.packages.add(
            self.pkg_all_combos, self.pkg_choice_usd, self.pkg_fte_eur,
        )
        self._compare(basket)

    def test_meta_packages(self):
        basket = models.Basket.objects.create(
            name="Meta", account=self.user, active=True,
        )
        basket.meta_packages.add(self.meta_18, self.meta_15)
        self._compare(basket)

    def test_twenty_packages(self):
        basket = models.Basket.objects.create(
            name="Twenty", account=self.user, active=True,
        )
        basket.packages.add(*self.all_packages[:20])
        self._compare(basket)

    def test_mixed_packages_and_meta(self):
        basket = models.Basket.objects.create(
            name="Mixed", account=self.user, active=True,
        )
        basket.packages.add(self.pkg_simple_choice, self.pkg_fte_eur)
        basket.meta_packages.add(self.meta_18, self.meta_15)
        self._compare(basket)

    def test_full_basket(self):
        basket = models.Basket.objects.create(
            name="Full", account=self.user, active=True,
        )
        basket.packages.add(*self.all_packages)
        basket.meta_packages.add(*self.all_metas)
        self._compare(basket)


# ---------------------------------------------------------------------------
# Model-level: get_best_bandings_for_form
# ---------------------------------------------------------------------------


class TestFastGetBestBandingsForForm(BasketFixtureMixin, TestCase):
    """
    Verify fast_get_best_bandings_for_form returns the same set of
    BandingType objects as the original.
    """

    def _compare(self, basket):
        identifier = self.user
        identifier_type = "user"
        country = self.user.profile.default_currency

        original = basket.get_best_bandings_for_form(
            identifier, identifier_type,
        )
        fast = basket.fast_get_best_bandings_for_form(
            identifier, identifier_type, country=country,
        )
        self.assertEqual(original, fast)

    def test_single_package(self):
        basket = models.Basket.objects.create(
            name="Single", account=self.user, active=True,
        )
        basket.packages.add(self.pkg_simple_choice)
        self._compare(basket)

    def test_multiple_packages(self):
        basket = models.Basket.objects.create(
            name="Multi", account=self.user, active=True,
        )
        basket.packages.add(
            self.pkg_all_combos, self.pkg_simple_fte, self.pkg_simple_choice,
        )
        self._compare(basket)

    def test_meta_packages(self):
        basket = models.Basket.objects.create(
            name="Meta", account=self.user, active=True,
        )
        basket.meta_packages.add(self.meta_18, self.meta_15)
        self._compare(basket)

    def test_full_basket(self):
        basket = models.Basket.objects.create(
            name="Full", account=self.user, active=True,
        )
        basket.packages.add(*self.all_packages)
        basket.meta_packages.add(*self.all_metas)
        self._compare(basket)

    def test_cross_currency_package(self):
        """pkg_choice_usd is USD-priced; user prefers GBP -> fallback."""
        basket = models.Basket.objects.create(
            name="Cross", account=self.user, active=True,
        )
        basket.packages.add(self.pkg_choice_usd)
        self._compare(basket)

    def test_multi_banding_basket(self):
        basket = models.Basket.objects.create(
            name="Multi-band", account=self.user, active=True,
        )
        basket.packages.add(
            self.pkg_all_combos, self.pkg_dual_multi, self.pkg_dual_gbp,
        )
        self._compare(basket)


# ---------------------------------------------------------------------------
# Util-level: get_price_for_package
# ---------------------------------------------------------------------------


class TestFastGetPriceForPackage(BasketFixtureMixin, TestCase):
    """
    Verify fast_get_price_for_package returns the same price/banding
    as the original for each package.
    """

    def _compare(self, package, country=None):
        identifier = self.user
        identifier_type = "user"
        if country is None:
            country = self.user.profile.default_currency

        orig_price, orig_banding = utils.get_price_for_package(
            package=package, identifier=identifier,
            identifier_type=identifier_type, country=country,
        )

        if "fast_price_bandings" in package.__dict__:
            del package.__dict__["fast_price_bandings"]

        account_banding_choices = {
            abc.banding_type_id: abc
            for abc in AccountBandingChoices.objects.filter(
                account=identifier,
            ).select_related("banding_type_vocab")
        }

        fast_price, fast_banding = utils.fast_get_price_for_package(
            package=package, identifier=identifier,
            identifier_type=identifier_type, country=country,
            account_banding_choices=account_banding_choices,
        )

        if orig_price == 0:
            self.assertEqual(fast_price, 0)
        else:
            self.assertEqual(orig_price.pk, fast_price.pk)
            self.assertEqual(orig_price.value, fast_price.value)

        if orig_banding is None:
            self.assertIsNone(fast_banding)
        else:
            self.assertEqual(orig_banding.pk, fast_banding.pk)

    def test_fte_matching_currency(self):
        """FTE/GBP, user currency is GBP."""
        self._compare(self.pkg_simple_fte)

    def test_fte_different_currency(self):
        """FTE/EUR, user currency is GBP -> fallback."""
        self._compare(self.pkg_fte_eur)

    def test_choice_package(self):
        """Choice/GBP."""
        self._compare(self.pkg_simple_choice)

    def test_all_combos_package(self):
        """FTE+Choice / GBP+USD+EUR — most complex."""
        self._compare(self.pkg_all_combos)

    def test_dual_multi_currency(self):
        """FTE+Choice / GBP+USD."""
        self._compare(self.pkg_dual_multi)

    def test_choice_usd_with_gbp_user(self):
        """Choice/USD, user is GBP -> fallback."""
        self._compare(self.pkg_choice_usd)

    def test_eur_country_override(self):
        """Force EUR country for a GBP+EUR package."""
        self._compare(self.pkg_fte_gbp_eur, country=self.country_eur)

    def test_usd_country_override(self):
        """Force USD country for an all-currency package."""
        self._compare(self.pkg_all_combos, country=self.country_usd)


# ---------------------------------------------------------------------------
# Util-level: get_user_currency
# ---------------------------------------------------------------------------


class TestFastGetUserCurrency(BasketFixtureMixin, TestCase):
    """Verify fast_get_user_currency matches get_user_currency."""

    def test_authenticated_user(self):
        orig = utils.get_user_currency(self.user, "user")
        fast = utils.fast_get_user_currency(
            self.user, "user", country=self.user.profile.default_currency,
        )
        self.assertEqual(orig, fast)

    def test_session_user(self):
        session = {"currency": self.country_usd.pk}
        orig = utils.get_user_currency(session, "session")
        fast = utils.fast_get_user_currency(session, "session")
        self.assertEqual(orig, fast)

    def test_pre_resolved_bypasses_lookup(self):
        """When country is passed, it should be returned as-is."""
        result = utils.fast_get_user_currency(
            None, "user", country=self.country_gbp,
        )
        self.assertEqual(result, self.country_gbp)


# ---------------------------------------------------------------------------
# View-level: compare full template contexts
# ---------------------------------------------------------------------------


class _ViewComparisonMixin:
    """
    Shared logic for comparing view_basket vs fast_view_basket contexts.
    Patches ``render`` to capture the template context dict.
    """

    def _extract_context(self, view_func, request, basket_id):
        captured = {}

        import package.views as pv
        original_render = pv.render

        def mock_render(req, template, context):
            captured.update(context)
            return original_render(req, template, context)

        pv.render = mock_render
        try:
            view_func(request, basket_id=basket_id)
        finally:
            pv.render = original_render

        return captured

    def _compare_contexts(self, orig_ctx, fast_ctx):
        # ---- package_costs ----
        orig_costs = orig_ctx["package_costs"]
        fast_costs = fast_ctx["package_costs"]
        self.assertEqual(
            len(orig_costs), len(fast_costs),
            "package_costs length differs",
        )
        for i, (o, f) in enumerate(zip(orig_costs, fast_costs)):
            self.assertEqual(
                o["package"].pk, f["package"].pk,
                "package_costs[{}].package differs".format(i),
            )
            if o["cost"] == 0:
                self.assertEqual(f["cost"], 0)
            else:
                self.assertEqual(
                    o["cost"].pk, f["cost"].pk,
                    "package_costs[{}].cost PK differs".format(i),
                )
            if o["banding"] is None:
                self.assertIsNone(f["banding"])
            else:
                self.assertEqual(
                    o["banding"].pk, f["banding"].pk,
                    "package_costs[{}].banding PK differs".format(i),
                )

        # ---- currency_totals ----
        self.assertEqual(
            orig_ctx["currency_totals"], fast_ctx["currency_totals"],
        )

        # ---- conflicting_packages ----
        orig_pks = {p.pk for p in orig_ctx["conflicting_packages"]}
        fast_pks = {p.pk for p in fast_ctx["conflicting_packages"]}
        self.assertEqual(orig_pks, fast_pks)

        # ---- scalar context values ----
        for key in (
            "has_all_prices",
            "message",
            "site_percentage",
            "currency_converted",
            "converted_total",
            "converted_currency",
        ):
            self.assertEqual(
                orig_ctx.get(key), fast_ctx.get(key),
                "Context key '{}' differs".format(key),
            )

        # ---- user_currency ----
        self.assertEqual(
            orig_ctx["user_currency"], fast_ctx["user_currency"],
        )

        # ---- bandings list ----
        orig_banding_pks = [b.pk for b in orig_ctx["bandings"]]
        fast_banding_pks = [b.pk for b in fast_ctx["bandings"]]
        self.assertEqual(orig_banding_pks, fast_banding_pks)


class TestViewBasketComparison(
    BasketFixtureMixin, _ViewComparisonMixin, TestCase
):
    """
    End-to-end comparison for an authenticated user: call both
    view_basket and fast_view_basket and verify contexts match.
    """

    def setUp(self):
        self.factory = RequestFactory()

    def _make_request(self):
        request = self.factory.get("/fake/")
        request.user = self.user
        request.session = {"country": self.country_gbp.code}
        request.site = self.site_setup
        request.signups = []
        return request

    def _run_comparison(self, basket):
        orig_ctx = self._extract_context(
            views.view_basket, self._make_request(), basket.pk,
        )
        fast_ctx = self._extract_context(
            views.fast_view_basket, self._make_request(), basket.pk,
        )
        self._compare_contexts(orig_ctx, fast_ctx)

    def test_single_package(self):
        basket = models.Basket.objects.create(
            name="Single", account=self.user, active=True,
        )
        basket.packages.add(self.pkg_all_combos)
        self._run_comparison(basket)

    def test_five_packages(self):
        basket = models.Basket.objects.create(
            name="Five", account=self.user, active=True,
        )
        basket.packages.add(*self.gbp_only_packages[:5])
        self._run_comparison(basket)

    @patch("package.currency.convert", return_value=1.25)
    def test_meta_packages(self, mock_convert):
        basket = models.Basket.objects.create(
            name="Meta", account=self.user, active=True,
        )
        basket.meta_packages.add(self.meta_18, self.meta_15)
        self._run_comparison(basket)

    @patch("package.currency.convert", return_value=1.25)
    def test_mixed_packages_and_meta(self, mock_convert):
        basket = models.Basket.objects.create(
            name="Mixed", account=self.user, active=True,
        )
        basket.packages.add(self.pkg_simple_choice)
        basket.meta_packages.add(self.meta_18, self.meta_15)
        self._run_comparison(basket)

    @patch("package.currency.convert", return_value=1.25)
    def test_twenty_packages(self, mock_convert):
        basket = models.Basket.objects.create(
            name="Twenty", account=self.user, active=True,
        )
        basket.packages.add(*self.all_packages[:20])
        basket.meta_packages.add(*self.all_metas[:5])
        self._run_comparison(basket)

    @patch("package.currency.convert", return_value=1.25)
    def test_full_basket(self, mock_convert):
        """All 50 packages + all 10 metas."""
        basket = models.Basket.objects.create(
            name="Full", account=self.user, active=True,
        )
        basket.packages.add(*self.all_packages)
        basket.meta_packages.add(*self.all_metas)
        self._run_comparison(basket)

    @patch("package.currency.convert", return_value=1.25)
    def test_cross_currency(self, mock_convert):
        basket = models.Basket.objects.create(
            name="Cross", account=self.user, active=True,
        )
        basket.packages.add(
            self.pkg_all_combos, self.pkg_choice_usd, self.pkg_fte_eur,
        )
        self._run_comparison(basket)


# ---------------------------------------------------------------------------
# Session-based (anonymous) view comparison tests
# ---------------------------------------------------------------------------


class TestViewBasketSessionComparison(
    BasketFixtureMixin, _ViewComparisonMixin, TestCase
):
    """Same comparisons but for anonymous/session-based users."""

    def setUp(self):
        self.factory = RequestFactory()
        self.session = SessionStore()
        self.session["currency"] = self.country_gbp.pk
        self.session["fte"] = 12000
        self.session.create()

    def _make_request(self):
        request = self.factory.get("/fake/")
        request.user = _AnonymousUser()
        request.session = self.session
        request.site = self.site_setup
        request.signups = []
        return request

    def _run_comparison(self, basket):
        orig_ctx = self._extract_context(
            views.view_basket, self._make_request(), basket.pk,
        )
        fast_ctx = self._extract_context(
            views.fast_view_basket, self._make_request(), basket.pk,
        )
        self._compare_contexts(orig_ctx, fast_ctx)

    def test_session_single(self):
        basket = models.Basket.objects.create(
            name="Sess single", session_id=self.session.session_key,
            active=True,
        )
        basket.packages.add(self.pkg_all_combos)
        self._run_comparison(basket)

    def test_session_five(self):
        basket = models.Basket.objects.create(
            name="Sess five", session_id=self.session.session_key,
            active=True,
        )
        basket.packages.add(*self.gbp_only_packages[:5])
        self._run_comparison(basket)

    def test_session_meta(self):
        basket = models.Basket.objects.create(
            name="Sess meta", session_id=self.session.session_key,
            active=True,
        )
        basket.meta_packages.add(self.meta_18, self.meta_15)
        self._run_comparison(basket)

    @patch("package.currency.convert", return_value=1.25)
    def test_session_twenty(self, mock_convert):
        basket = models.Basket.objects.create(
            name="Sess twenty", session_id=self.session.session_key,
            active=True,
        )
        basket.packages.add(*self.all_packages[:20])
        basket.meta_packages.add(*self.all_metas[:5])
        self._run_comparison(basket)

    @patch("package.currency.convert", return_value=1.25)
    def test_session_full(self, mock_convert):
        basket = models.Basket.objects.create(
            name="Sess full", session_id=self.session.session_key,
            active=True,
        )
        basket.packages.add(*self.all_packages)
        basket.meta_packages.add(*self.all_metas)
        self._run_comparison(basket)


# ---------------------------------------------------------------------------
# Rendered output comparison: actual HTTP responses from both views
# ---------------------------------------------------------------------------


class _TimingTableMixin:
    """
    Collects per-test timing results and prints a summary table in
    ``tearDownClass``.
    """

    _timing_results = None
    _timing_title = "Timing Results"

    @classmethod
    def _init_timing(cls):
        cls._timing_results = []

    @classmethod
    def _print_timing_table(cls):
        if not cls._timing_results:
            return

        label_w = max(len(r[0]) for r in cls._timing_results)
        label_w = max(label_w, len("Scenario"))

        rows = []
        for label, orig, fast in cls._timing_results:
            speedup = orig / fast if fast > 0 else float("inf")
            saved = orig - fast
            rows.append((label, orig, fast, speedup, saved))

        print("\n")
        print("  {}".format(cls._timing_title))
        print("  {}".format("=" * (label_w + 52)))
        print("  {:<{w}}  {:>10}  {:>10}  {:>9}  {:>9}".format(
            "Scenario", "Original", "Fast", "Speedup", "Saved",
            w=label_w,
        ))
        print("  {:<{w}}  {:>10}  {:>10}  {:>9}  {:>9}".format(
            "-" * label_w, "-" * 10, "-" * 10, "-" * 9, "-" * 9,
            w=label_w,
        ))
        for label, orig, fast, speedup, saved in rows:
            print("  {:<{w}}  {:>9.3f}s  {:>9.3f}s  {:>8.1f}x  {:>8.3f}s".format(
                label, orig, fast, speedup, saved,
                w=label_w,
            ))
        print("  {:<{w}}  {:>10}  {:>10}  {:>9}  {:>9}".format(
            "-" * label_w, "-" * 10, "-" * 10, "-" * 9, "-" * 9,
            w=label_w,
        ))

        total_orig = sum(r[1] for r in rows)
        total_fast = sum(r[2] for r in rows)
        total_speedup = total_orig / total_fast if total_fast > 0 else float("inf")
        total_saved = total_orig - total_fast
        print("  {:<{w}}  {:>9.3f}s  {:>9.3f}s  {:>8.1f}x  {:>8.3f}s".format(
            "TOTAL", total_orig, total_fast, total_speedup, total_saved,
            w=label_w,
        ))
        print()

    _csrf_re = re.compile(
        r'(name="csrfmiddlewaretoken"\s+value=")[^"]*(")'
    )

    @classmethod
    def _normalise(cls, html):
        return cls._csrf_re.sub(r'\1CSRF_TOKEN\2', html)

    def _get_responses(self, basket):
        orig_url = "/packages/baskets/{}/".format(basket.pk)
        fast_url = "/packages/baskets/{}/fast/".format(basket.pk)

        t0 = time.perf_counter()
        orig_resp = self.client.get(orig_url)
        orig_time = time.perf_counter() - t0

        t0 = time.perf_counter()
        fast_resp = self.client.get(fast_url)
        fast_time = time.perf_counter() - t0

        self.assertEqual(
            orig_resp.status_code, 200,
            "Original view returned {}".format(orig_resp.status_code),
        )
        self.assertEqual(
            fast_resp.status_code, 200,
            "Fast view returned {}".format(fast_resp.status_code),
        )
        return orig_resp, fast_resp, orig_time, fast_time

    def _compare_html(self, basket, label=""):
        orig_resp, fast_resp, orig_time, fast_time = self._get_responses(
            basket,
        )
        orig_html = self._normalise(orig_resp.content.decode("utf-8"))
        fast_html = self._normalise(fast_resp.content.decode("utf-8"))

        display_label = label or basket.name
        self.__class__._timing_results.append(
            (display_label, orig_time, fast_time),
        )

        self.assertEqual(
            orig_html, fast_html,
            "Rendered HTML differs between view_basket and fast_view_basket",
        )


class TestRenderedOutputComparison(
    BasketFixtureMixin, _TimingTableMixin, TestCase,
):
    """
    End-to-end test that hits both /packages/baskets/<id>/ and
    /packages/baskets/<id>/fast/ via Django's test Client and compares
    the rendered HTML output byte-for-byte (after normalising CSRF tokens).
    """

    _timing_title = "Authenticated User Timing"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._init_timing()

    @classmethod
    def tearDownClass(cls):
        cls._print_timing_table()
        super().tearDownClass()

    def setUp(self):
        self.client.login(username="testuser", password="testpass123")
        session = self.client.session
        session["country"] = self.country_gbp.code
        session.save()

    def test_single_package(self):
        basket = models.Basket.objects.create(
            name="1 pkg", account=self.user, active=True,
        )
        basket.packages.add(self.pkg_all_combos)
        self._compare_html(basket, label="1 pkg (auth)")

    def test_five_packages(self):
        basket = models.Basket.objects.create(
            name="5 pkg", account=self.user, active=True,
        )
        basket.packages.add(*self.gbp_only_packages[:5])
        self._compare_html(basket, label="5 pkgs GBP-only (auth)")

    @patch("package.currency.convert", return_value=1.25)
    def test_ten_packages(self, mock_convert):
        basket = models.Basket.objects.create(
            name="10 pkg", account=self.user, active=True,
        )
        basket.packages.add(*self.all_packages[:10])
        self._compare_html(basket, label="10 pkgs (auth)")

    @patch("package.currency.convert", return_value=1.25)
    def test_twenty_packages(self, mock_convert):
        basket = models.Basket.objects.create(
            name="20 pkg", account=self.user, active=True,
        )
        basket.packages.add(*self.all_packages[:20])
        basket.meta_packages.add(*self.all_metas[:5])
        self._compare_html(basket, label="20 pkgs + 5 metas (auth)")

    @patch("package.currency.convert", return_value=1.25)
    def test_thirty_packages_with_metas(self, mock_convert):
        basket = models.Basket.objects.create(
            name="30 pkg", account=self.user, active=True,
        )
        basket.packages.add(*self.all_packages[:30])
        basket.meta_packages.add(*self.all_metas[:7])
        self._compare_html(basket, label="30 pkgs + 7 metas (auth)")

    @patch("package.currency.convert", return_value=1.25)
    def test_full_basket(self, mock_convert):
        """All 50 packages + all 10 metas."""
        basket = models.Basket.objects.create(
            name="Full", account=self.user, active=True,
        )
        basket.packages.add(*self.all_packages)
        basket.meta_packages.add(*self.all_metas)
        self._compare_html(basket, label="50 pkgs + 10 metas (auth)")

    @patch("package.currency.convert", return_value=1.25)
    def test_meta_only(self, mock_convert):
        basket = models.Basket.objects.create(
            name="Meta only", account=self.user, active=True,
        )
        basket.meta_packages.add(self.meta_18, self.meta_15)
        self._compare_html(basket, label="2 metas / 33 pkgs (auth)")

    @patch("package.currency.convert", return_value=1.25)
    def test_cross_currency(self, mock_convert):
        basket = models.Basket.objects.create(
            name="Cross", account=self.user, active=True,
        )
        basket.packages.add(
            self.pkg_all_combos, self.pkg_choice_usd, self.pkg_fte_eur,
        )
        self._compare_html(basket, label="3 pkgs cross-currency (auth)")

    def test_choice_only(self):
        basket = models.Basket.objects.create(
            name="Choice", account=self.user, active=True,
        )
        basket.packages.add(self.pkg_simple_choice)
        self._compare_html(basket, label="1 choice pkg (auth)")

    @patch("package.currency.convert", return_value=1.25)
    def test_all_metas_no_direct(self, mock_convert):
        """All 10 meta packages, no direct packages."""
        basket = models.Basket.objects.create(
            name="All metas", account=self.user, active=True,
        )
        basket.meta_packages.add(*self.all_metas)
        self._compare_html(basket, label="10 metas / no direct (auth)")


class TestRenderedOutputSessionComparison(
    BasketFixtureMixin, _TimingTableMixin, TestCase,
):
    """Same rendered-output comparison for anonymous/session-based users."""

    _timing_title = "Anonymous/Session User Timing"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._init_timing()

    @classmethod
    def tearDownClass(cls):
        cls._print_timing_table()
        super().tearDownClass()

    def setUp(self):
        session = self.client.session
        session["country"] = self.country_gbp.code
        session["currency"] = self.country_gbp.pk
        session["fte"] = 12000
        session.save()

    def _get_session_key(self):
        return self.client.session.session_key

    def test_session_single(self):
        basket = models.Basket.objects.create(
            name="Sess 1", session_id=self._get_session_key(), active=True,
        )
        basket.packages.add(self.pkg_all_combos)
        self._compare_html(basket, label="1 pkg (anon)")

    def test_session_five(self):
        basket = models.Basket.objects.create(
            name="Sess 5", session_id=self._get_session_key(), active=True,
        )
        basket.packages.add(*self.gbp_only_packages[:5])
        self._compare_html(basket, label="5 pkgs (anon)")

    @patch("package.currency.convert", return_value=1.25)
    def test_session_twenty(self, mock_convert):
        basket = models.Basket.objects.create(
            name="Sess 20", session_id=self._get_session_key(), active=True,
        )
        basket.packages.add(*self.all_packages[:20])
        basket.meta_packages.add(*self.all_metas[:5])
        self._compare_html(basket, label="20 pkgs + 5 metas (anon)")

    @patch("package.currency.convert", return_value=1.25)
    def test_session_thirty(self, mock_convert):
        basket = models.Basket.objects.create(
            name="Sess 30", session_id=self._get_session_key(), active=True,
        )
        basket.packages.add(*self.all_packages[:30])
        basket.meta_packages.add(*self.all_metas[:7])
        self._compare_html(basket, label="30 pkgs + 7 metas (anon)")

    @patch("package.currency.convert", return_value=1.25)
    def test_session_full(self, mock_convert):
        basket = models.Basket.objects.create(
            name="Sess full", session_id=self._get_session_key(), active=True,
        )
        basket.packages.add(*self.all_packages)
        basket.meta_packages.add(*self.all_metas)
        self._compare_html(basket, label="50 pkgs + 10 metas (anon)")

    @patch("package.currency.convert", return_value=1.25)
    def test_session_all_metas(self, mock_convert):
        basket = models.Basket.objects.create(
            name="Sess metas", session_id=self._get_session_key(), active=True,
        )
        basket.meta_packages.add(*self.all_metas)
        self._compare_html(basket, label="10 metas / no direct (anon)")
