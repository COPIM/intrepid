from modeltranslation.translator import translator, TranslationOptions

from cms import models


class SiteTextTranslation(TranslationOptions):
    fields = (
        'body',
    )


translator.register(models.SiteText, SiteTextTranslation)
