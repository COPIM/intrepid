from modeltranslation.translator import translator, TranslationOptions

from cms import models


class SiteTextTranslation(TranslationOptions):
    fields = (
        'body',
    )


class VersionTranslation(TranslationOptions):
    fields = (
        'first_paragraph',
        'pre_break_content',
        'pull_quote',
        'body',
    )


class PageUpdateTranslation(TranslationOptions):
    fields = (
        'title',
        'abstract_paragraph',
    )


class WhoWeAreProfileItemTranslation(TranslationOptions):
    fields = (
        'bio',
    )


class HomePageQuoteTranslation(TranslationOptions):
    fields = (
        'pill_name',
        'quotation',
        'person_attribution',
        'organization_attribution',
    )


translator.register(models.SiteText, SiteTextTranslation)
translator.register(models.Version, VersionTranslation)
translator.register(models.PageUpdate, PageUpdateTranslation)
translator.register(models.WhoWeAreProfileItem, WhoWeAreProfileItemTranslation)
translator.register(models.HomePageQuote, HomePageQuoteTranslation)
