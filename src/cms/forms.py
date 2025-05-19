from django import forms
from django_summernote.widgets import SummernoteWidget
from django.conf import settings

from modeltranslation.utils import get_translation_fields
from django.utils.translation import get_language

from cms import models, utils
from thoth import models as thoth_models


class PageUpdateForm(forms.ModelForm):
    """
    Form for creating and updating PageUpdate objects.
    """

    class Meta:
        model = models.PageUpdate
        fields = (
            "title",
            "url_expression",
            "abstract_paragraph",
            "display",
            "sequence",
            "thumbnail_image",
            "mid_page_image",
        )

    def __init__(self, *args, **kwargs):
        self.initiative = kwargs.pop("initiative")
        self.user = kwargs.pop("user")
        self.page_or_update = kwargs.pop("page_or_update")
        self.ror = kwargs.pop("ror")
        super(PageUpdateForm, self).__init__(*args, **kwargs)

    def clean_thumbnail_image(self):
        """
        Resize the thumbnail image to the correct dimensions.
        :return: The resized image.
        """
        img = self.cleaned_data.get("thumbnail_image")

        return utils.resize_image(510, 302, img)

    def clean_mid_page_image(self):
        """
        Resize the mid-page image to the correct dimensions.
        :return: The resized image.
        """
        img = self.cleaned_data.get("mid_page_image")

        return utils.resize_image(1250, 500, img)

    def save(self, commit=True):
        """
        Save the PageUpdate object.
        :param commit: Whether to commit the object to the database.
        :return: The saved PageUpdate object.
        """
        page_update = super(PageUpdateForm, self).save(commit=False)
        page_update.initiative = self.initiative
        page_update.updated_by = self.user

        if self.page_or_update == "update":
            page_update.is_update = True

        if self.ror is not None and self.ror != "":
            page_update.target_institution = thoth_models.RORRecord.objects.get(
                ror_id=self.ror
            )
        else:
            page_update.target_institution = None

        if commit:
            page_update.save()

        return page_update


class VersionForm(forms.ModelForm):
    """
    Form for creating and updating Version objects.
    """

    class Meta:
        model = models.Version
        fields = (
            'first_paragraph',
            'pre_break_content',
            'pull_quote',
            'show_quote_icons',
            'body',
        )

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        self.user = kwargs.pop("user")
        self.source_version = kwargs.pop("source_version", None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        version = super().save(commit=False)
        version.created_by = self.user

        if self.source_version:
            current_lang = get_language()
            for field in self.Meta.fields:
                for lang_code in [lang[0] for lang in settings.LANGUAGES]:
                    trans_field = f"{field}_{lang_code}"

                    if lang_code != current_lang:
                        value = getattr(self.source_version, trans_field, None)
                        setattr(version, trans_field, value)

        if commit:
            version.save()

        return version


class WhoWeAreEntryForm(forms.ModelForm):
    """
    Form for creating and updating WhoWeAreProfileItem objects.
    """

    class Meta:
        model = models.WhoWeAreProfileItem
        fields = (
            "display_name",
            "affiliation_line",
            "bio",
            "police_mugshot",
        )
        exclude = ("section", "order")

    def clean_police_mugshot(self):
        """
        Resize the user's profile image to the correct dimensions.
        The name of this function is a joke,
        :return: The resized image.
        """
        img = self.cleaned_data.get("police_mugshot")

        if not img:
            return img

        return utils.resize_image(300, 300, img)

    def __init__(self, *args, **kwargs):
        self.section = kwargs.pop("section")
        super(WhoWeAreEntryForm, self).__init__(*args, **kwargs)

    def save(self, commit=True):
        """
        Save the WhoWeAreProfileItem object.
        :param commit: Whether to commit the object to the database.
        :return: The saved WhoWeAreProfileItem object.
        """
        who_we_are_form = super(WhoWeAreEntryForm, self).save(commit=False)
        who_we_are_form.section = self.section

        if commit:
            who_we_are_form.save()

        return who_we_are_form


class PrimaryInitiativeForm(forms.ModelForm):
    """
    Form for creating and updating PrimaryInitiative objects.
    """

    class Meta:
        model = models.PrimaryInitiative
        exclude = ()


class HomePageQuoteForm(forms.ModelForm):
    """
    Form for creating and updating HomePageQuote objects.
    """

    class Meta:
        model = models.HomePageQuote
        fields = (
            'pill_name',
            'quotation',
            'organization_attribution',
            'organization_logo',
        )
        exclude = ("order",)

    def clean_organization_logo(self):
        """
        Resize the organization logo to the correct dimensions.
        :return: The resized image.
        """
        img = self.cleaned_data.get("organization_logo")

        return utils.resize_image(145, 145, img)


class EditSiteText(forms.ModelForm):
    """
    Form for editing the site text.
    """

    class Meta:
        model = models.SiteText
        fields = ("body",)

    def __init__(self, *args, **kwargs):
        super(EditSiteText, self).__init__(*args, **kwargs)

        if self.instance and self.instance.rich_text:
            self.fields["body"].widget = SummernoteWidget()
