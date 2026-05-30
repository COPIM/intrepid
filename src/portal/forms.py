"""
Forms for the document management portal.

The site runs Django 3.2, which has no ``MultipleFileField``, so multi-file
upload uses a small ``MultipleFileInput``/``MultipleFileField`` pair (the
documented Django pattern) plus ``request.FILES.getlist`` in the view.
"""

import zipfile

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from portal.models import Document, DocumentType, ProviderContact

MONTH_INPUT_FORMATS = ["%Y-%m-%d", "%Y-%m"]


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

    def value_from_datadict(self, data, files, name):
        if hasattr(files, "getlist"):
            return files.getlist(name)
        value = files.get(name)
        return [value] if value is not None else []


class MultipleFileField(forms.FileField):
    """A FileField that cleans a list of uploaded files."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_clean = super().clean
        if not data:
            if self.required:
                raise ValidationError(
                    self.error_messages["required"], code="required"
                )
            return []
        if not isinstance(data, (list, tuple)):
            data = [data]
        return [single_clean(item, initial) for item in data]


def _reporting_month_field():
    return forms.DateField(
        required=False,
        input_formats=MONTH_INPUT_FORMATS,
        widget=forms.DateInput(attrs={"type": "month"}),
    )


class DocumentUploadForm(forms.Form):
    """OBC upload form: one document type, optional month, many files."""

    document_type = forms.ModelChoiceField(
        queryset=DocumentType.objects.all()
    )
    reporting_month = _reporting_month_field()
    file = MultipleFileField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", "Upload"))

    def clean(self):
        cleaned = super().clean()
        doc_type = cleaned.get("document_type")
        if (
            doc_type
            and doc_type.requires_reporting_month
            and not cleaned.get("reporting_month")
        ):
            self.add_error(
                "reporting_month",
                "A reporting month is required for this document type.",
            )
        return cleaned


class DocumentEditForm(forms.ModelForm):
    reporting_month = _reporting_month_field()

    class Meta:
        model = Document
        fields = ["display_name", "document_type", "reporting_month", "notes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", "Save changes"))


class BulkImportZipForm(forms.Form):
    zip_file = forms.FileField(label="ZIP archive")
    notify_on_commit = forms.BooleanField(
        required=False,
        initial=False,
        label="Send notifications for these documents",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", "Upload and preview"))

    def clean_zip_file(self):
        uploaded = self.cleaned_data["zip_file"]
        if not zipfile.is_zipfile(uploaded):
            raise ValidationError("Please upload a valid ZIP archive.")
        uploaded.seek(0)
        return uploaded


class ProviderContactForm(forms.ModelForm):
    class Meta:
        model = ProviderContact
        fields = [
            "first_name",
            "last_name",
            "job_title",
            "email",
            "position",
            "notification_frequency",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", "Save contact"))


class NotificationPreferencesForm(forms.ModelForm):
    class Meta:
        model = ProviderContact
        fields = ["notification_frequency"]
        widgets = {"notification_frequency": forms.RadioSelect}


class AcceptInviteForm(forms.Form):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    job_title = forms.CharField(max_length=255, required=False)
    password1 = forms.CharField(
        widget=forms.PasswordInput, label="Choose a password"
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput, label="Confirm password"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", "Activate my account"))

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "The two passwords do not match.")
        if password1:
            try:
                validate_password(password1)
            except ValidationError as error:
                self.add_error("password1", error)
        return cleaned
