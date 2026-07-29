"""
modeltranslation registrations for the portal.

Only ``DocumentType`` carries translatable content — the type names and
descriptions that Provider Members see in the filters. This mirrors the
module-level ``translator.register`` convention used in ``vocab/translation.py``.
"""

from modeltranslation.translator import TranslationOptions, translator

from portal import models


class DocumentTypeTranslation(TranslationOptions):
    fields = ("name", "description")


translator.register(models.DocumentType, DocumentTypeTranslation)
