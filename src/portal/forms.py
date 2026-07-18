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
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from portal.models import Document, DocumentType, ProviderContact

MONTH_INPUT_FORMATS = ["%Y-%m-%d", "%Y-%m"]


def site_text(key, default):
    """Return the translated SiteText for ``key``, falling back to ``default``.

    Lets portal form labels and buttons be translated through the site's
    existing ``cms.SiteText`` system without 500ing if a key is missing.
    """
    from cms.models import SiteText

    try:
        return SiteText.objects.get(key=key).body or default
    except SiteText.DoesNotExist:
        return default


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
    send_notification = forms.BooleanField(required=False, initial=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["send_notification"].label = site_text(
            "portal_form_send_notification", "Send notification"
        )
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
        self.fields["display_name"].label = site_text(
            "portal_form_display_name", "Display name"
        )
        self.fields["document_type"].label = site_text(
            "portal_form_document_type", "Document type"
        )
        self.fields["reporting_month"].label = site_text(
            "portal_form_reporting_month", "Reporting month"
        )
        self.fields["notes"].label = site_text("portal_form_notes", "Notes")
        self.helper = FormHelper()
        self.helper.add_input(
            Submit("submit", site_text("portal_form_save_changes", "Save changes"))
        )


class BulkImportZipForm(forms.Form):
    zip_file = forms.FileField(label="ZIP archive")
    notify_on_commit = forms.BooleanField(
        required=False,
        initial=True,
        label="Send notifications for these documents",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["zip_file"].label = site_text(
            "portal_form_zip_archive", "ZIP archive"
        )
        self.fields["notify_on_commit"].label = site_text(
            "portal_form_notify_commit",
            "Send notifications for these documents",
        )
        self.helper = FormHelper()
        self.helper.add_input(
            Submit(
                "submit",
                site_text("portal_form_upload_preview", "Upload and preview"),
            )
        )

    def clean_zip_file(self):
        uploaded = self.cleaned_data["zip_file"]
        if not zipfile.is_zipfile(uploaded):
            raise ValidationError("Please upload a valid ZIP archive.")
        uploaded.seek(0)
        return uploaded


class ProviderContactForm(forms.ModelForm):
    class Meta:
        model = ProviderContact
        # ``position`` is intentionally omitted — it is auto-numbered when a
        # contact is added (see provider_manage_contacts).
        fields = [
            "first_name",
            "last_name",
            "job_title",
            "email",
            "notification_frequency",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        labels = {
            "first_name": ("portal_form_first_name", "First name"),
            "last_name": ("portal_form_last_name", "Surname"),
            "job_title": ("portal_form_job_title", "Job title"),
            "email": ("portal_form_email", "Email address"),
            "notification_frequency": (
                "portal_form_notification_frequency",
                "Notification frequency",
            ),
        }
        for field, (key, default) in labels.items():
            self.fields[field].label = site_text(key, default)
        self.helper = FormHelper()
        self.helper.add_input(
            Submit("submit", site_text("portal_form_save_contact", "Save contact"))
        )


class NotificationPreferencesForm(forms.ModelForm):
    class Meta:
        model = ProviderContact
        fields = ["notification_frequency"]
        widgets = {"notification_frequency": forms.RadioSelect}


class InitiativeUserForm(forms.Form):
    """Add an existing user account to a Provider by email address."""

    email = forms.EmailField(label="User's email address")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.fields["email"].label = site_text(
            "portal_form_user_email", "User's email address"
        )
        self.helper = FormHelper()
        self.helper.add_input(
            Submit("submit", site_text("portal_form_add_user", "Add user"))
        )

    def clean_email(self):
        email = self.cleaned_data["email"]
        self.user = User.objects.filter(email__iexact=email).first()
        if self.user is None:
            raise ValidationError(
                "No user account exists with that email address. Invite them "
                "from the Provider's contacts instead."
            )
        return email


class InitiativeAliasForm(forms.Form):
    """Add an alternative name (alias) for a Provider."""

    alias = forms.CharField(max_length=255)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["alias"].label = site_text(
            "portal_form_alias", "Alias (alternative name)"
        )
        self.helper = FormHelper()
        self.helper.add_input(
            Submit("submit", site_text("portal_form_add_alias", "Add alias"))
        )


class InviteByEmailForm(forms.Form):
    """Invite a new person by email address alone."""

    email = forms.EmailField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].label = site_text(
            "portal_form_invite_email", "Email address"
        )
        self.helper = FormHelper()
        self.helper.add_input(
            Submit(
                "submit",
                site_text("portal_form_invite_btn", "Invite by email"),
            )
        )


class StaffUserForm(forms.Form):
    """Grant an existing user account OBC staff (backend) access by email."""

    email = forms.EmailField(label="User's email address")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.fields["email"].label = site_text(
            "portal_form_staff_email", "User's email address"
        )
        self.helper = FormHelper()
        self.helper.add_input(
            Submit("submit", site_text("portal_form_add_staff", "Make staff"))
        )

    def clean_email(self):
        email = self.cleaned_data["email"]
        self.user = User.objects.filter(email__iexact=email).first()
        if self.user is None:
            raise ValidationError(
                "No user account exists with that email address. They need an "
                "account first — invite them from a Provider's contacts."
            )
        return email


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
        self.fields["first_name"].label = site_text(
            "portal_form_first_name", "First name"
        )
        self.fields["last_name"].label = site_text(
            "portal_form_last_name", "Surname"
        )
        self.fields["job_title"].label = site_text(
            "portal_form_job_title", "Job title"
        )
        self.fields["password1"].label = site_text(
            "portal_form_choose_password", "Choose a password"
        )
        self.fields["password2"].label = site_text(
            "portal_form_confirm_password", "Confirm password"
        )
        self.helper = FormHelper()
        self.helper.add_input(
            Submit("submit", site_text("portal_form_activate", "Activate my account"))
        )

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
