from modeltranslation.translator import translator, TranslationOptions

from mail import models


class EmailTemplateTranslation(TranslationOptions):
    fields = (
        "subject",
        "body",
    )


translator.register(models.EmailTemplate, EmailTemplateTranslation)
