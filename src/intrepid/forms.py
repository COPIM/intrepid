from django import forms

from intrepid import models


class SiteSetupForm(forms.ModelForm):
    """
    Form for editing the site setup.
    """

    class Meta:
        model = models.SiteSetup
        fields = (
            "site_name",
            "enable_signup",
            "enable_meta_package_signup",
            "enable_individual_package_signup",
            "enable_standards",
            "enable_your_quotes_link",
            "signup_disabled_notification",
            "twitter_url",
            "contact_email",
            "youtube_embed",
            "base_copyright_notice",
            "board_of_stewards_description",
            "management_team_description",
            "membership_committee_description",
            "secretariat_description",
            "fee_amount",
        )

        widgets = {
            "base_copyright_notice": forms.TextInput,
            "board_of_stewards_description": forms.TextInput,
            "management_team_description": forms.TextInput,
            "membership_committee_description": forms.TextInput,
            "secretariat_description": forms.TextInput,
        }

    def __init__(self, *args, **kwargs):
        super(SiteSetupForm, self).__init__(*args, **kwargs)

    def save(self, commit=True):
        site_setup_form = super(SiteSetupForm, self).save(commit=False)

        if commit:
            site_setup_form.save()

        return site_setup_form
