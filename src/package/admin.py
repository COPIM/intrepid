from django.contrib import admin
from django_bleach.models import BleachField
from django_summernote.widgets import SummernoteWidget

from package import models


class CountryAdmin(admin.ModelAdmin):
    """
    Admin for Country model
    """

    list_display = ("pk", "name", "code", "currency")


class BandingAdmin(admin.ModelAdmin):
    """
    Admin for Banding model
    """

    list_display = ("pk", "name", "package", "active")
    list_filter = ("package", "active")
    raw_id_fields = ("package",)


class PriceAdmin(admin.ModelAdmin):
    """
    Admin for Price model
    """

    list_display = ("pk", "banding", "country", "value")
    list_filter = ("banding", "country")
    raw_id_fields = ("banding", "country")


class PackageAdmin(admin.ModelAdmin):
    """
    Admin for Package model
    """

    list_display = ("pk", "name", "initiative")
    list_filter = ("initiative",)
    raw_id_fields = ("initiative",)
    formfield_overrides = {
        BleachField: {"widget": SummernoteWidget},
    }


class MetaPackageLinkInline(admin.TabularInline):
    """
    Inline for MetaPackageLink model
    """

    model = models.MetaPackageLink
    extra = 1


class MetaPackage(admin.ModelAdmin):
    """
    Admin for MetaPackage model
    """

    list_display = ("pk", "name")
    inlines = (MetaPackageLinkInline,)
    formfield_overrides = {
        BleachField: {"widget": SummernoteWidget},
    }


class BasketAdmin(admin.ModelAdmin):
    """
    Admin for Basket model
    """

    list_display = ("pk", "name", "account", "session_id")
    list_filter = ("account",)


class FormElementAdmin(admin.ModelAdmin):
    """
    Admin for AggregateFormElement model
    """

    list_display = ("pk", "name", "kind", "choices", "required")


class DocumentAdmin(admin.ModelAdmin):
    """
    Admin for PackageDocument model
    """

    list_display = ("pk", "name", "pdf_file", "package")


class BandingTypeAdmin(admin.ModelAdmin):
    """
    Admin for BandingType model
    """

    list_display = (
        "name",
        "is_fte",
        "active",
    )
    filter_horizontal = ("vocabs",)
    list_filter = (
        "is_fte",
        "active",
    )
    formfield_overrides = {
        BleachField: {"widget": SummernoteWidget},
    }


class BandingTypeEntryAdmin(admin.ModelAdmin):
    """
    Admin for BandingTypeEntry model
    """

    list_display = ("package", "banding_type")


class BandingTypeCurrencyEntryAdmin(admin.ModelAdmin):
    """
    Admin for BandingTypeCurrencyEntry model
    """

    list_display = ("package", "banding_type_entry")


class OrderAdmin(admin.ModelAdmin):
    """
    Admin for Order model
    """

    list_display = ("pk", "order_number", "associated_user", "email_address")


class PackageDocumentHistoricalAdmin(admin.ModelAdmin):
    """
    Admin for PackageDocumentHistorical model
    """

    list_display = ("name", "pk")


class SignupInvoiceInline(admin.TabularInline):
    """
    Inline for SignupInvoice model
    """

    from invoicing.models import SignupInvoice

    model = SignupInvoice


class PackageSignupAdmin(admin.ModelAdmin):
    """
    Admin for PackageSignup model
    """

    list_display = (
        "pk",
        "associated_order",
        "associated_package",
        "associated_user",
        "banding",
        "signup_date",
        "price",
        "currency",
        "status",
        "initiative_approved",
        "organisation_approved",
    )
    inlines = [SignupInvoiceInline]


class PreCalcMinMaxAdmin(admin.ModelAdmin):
    list_display = ('pk', 'package', 'meta_package', 'country', 'min_amount', 'max_amount')


admin_list = [
    (models.BandingType, BandingTypeAdmin),
    (models.Country, CountryAdmin),
    (models.Banding, BandingAdmin),
    (models.Price, PriceAdmin),
    (models.Package, PackageAdmin),
    (models.MetaPackage, MetaPackage),
    (models.Basket, BasketAdmin),
    (models.AggregateFormElement, FormElementAdmin),
    (models.PackageDocument, DocumentAdmin),
    (models.BandingTypeEntry, BandingTypeEntryAdmin),
    (models.Order, OrderAdmin),
    (models.PackageSignup, PackageSignupAdmin),
    (models.PackageSignupOrderFormAnswer,),
    (models.CustomPackageDocument,),
    (models.PackageDocumentHistorical, PackageDocumentHistoricalAdmin),
    (models.BandingTypeCurrencyEntry, BandingTypeCurrencyEntryAdmin),
    (models.PreCalcMinMax, PreCalcMinMaxAdmin),
]

[admin.site.register(*t) for t in admin_list]
