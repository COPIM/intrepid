from modeltranslation.translator import translator, TranslationOptions

from package import models


class BandingTypeTranslation(TranslationOptions):
    fields = (
        'name',
        'description',
    )

translator.register(models.BandingType, BandingTypeTranslation)


class BasePackageTranslation(TranslationOptions):
    fields = (
        'name',
        'description',
    )

translator.register(models.BasePackage, BasePackageTranslation)
