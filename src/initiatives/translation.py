from modeltranslation.translator import translator, TranslationOptions

from initiatives import models


class InitiativeTranslation(TranslationOptions):
    fields = (
        'description',
        'more_info',
    )


translator.register(models.Initiative, InitiativeTranslation)


class HighlightsTranslation(TranslationOptions):
    fields = (
        'title',
        'body',
    )


translator.register(models.Highlights, HighlightsTranslation)
