from django import forms
from django.contrib.auth.models import User

from accounts import models
from cms import utils as cms_utils
from thoth import models as thoth_models


class ProfileForm(forms.ModelForm):
    class Meta:
        model = models.Profile
        fields = (
            "fte",
            "institution",
            "default_currency",
            "notify_new_books",
            "notify_targeted_updates",
            "image",
        )

    def __init__(self, *args, **kwargs):
        self.ror = kwargs.pop("ror")
        super(ProfileForm, self).__init__(*args, **kwargs)

    def clean_image(self):
        img = self.cleaned_data.get("image")

        return cms_utils.resize_image(400, 400, img)

    def save(self, commit=True):
        site_setup_form = super(ProfileForm, self).save(commit=False)

        if self.ror is not None and self.ror != "":
            site_setup_form.institution = thoth_models.RORRecord.objects.get(
                ror_id=self.ror
            )

        if commit:
            site_setup_form.save()

        return site_setup_form


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "email",
            "password",
        )
        widgets = {
            "password": forms.PasswordInput(),
        }

    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        self.password = None

    def save(self, commit=True):
        user = super(UserForm, self).save(commit=False)
        user.username = user.email.lower()
        user.is_active = False

        self.password = self.cleaned_data.get("password")

        if self.password and self.password != "":
            user.set_password(user.password)

        if commit:
            user.save()

        return user


class UserFormNoPassword(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")
        widgets = {
            "password": forms.PasswordInput(),
        }

    def __init__(self, *args, **kwargs):
        super(UserFormNoPassword, self).__init__(*args, **kwargs)

    def save(self, commit=True):
        user = super(UserFormNoPassword, self).save(commit=False)
        user.username = user.email.lower()
        user.is_active = True

        if commit:
            user.save()

        return user
