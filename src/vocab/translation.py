from modeltranslation.translator import translator, TranslationOptions

from vocab import models


class BandingVocabTranslation(TranslationOptions):
    fields = ('text',)

translator.register(models.BandingVocab, BandingVocabTranslation)
