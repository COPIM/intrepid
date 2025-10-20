from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, HTML
from django import forms
from django.contrib.auth.models import User
from django.db.models import Max
from django.forms import widgets
from django_summernote.widgets import SummernoteWidget
from django.db.utils import ProgrammingError

from accounts import models as accm
from intrepid.models import PrivateImage
from package import models
from vocab import models as vm
from cms.models import SiteText


class NewBasketForm(forms.ModelForm):
    """
    Form for creating a new basket
    """

    class Meta:
        model = models.Basket
        fields = ("name",)

    def __init__(self, *args, **kwargs):
        self.identifier = kwargs.pop("identifier")
        super(NewBasketForm, self).__init__(*args, **kwargs)

    def save(self, commit=True) -> "NewBasketForm":
        """
        Save the form
        :param commit: whether to commit or not
        :return:
        """
        basket = super(NewBasketForm, self).save(commit=False)

        if isinstance(self.identifier, User):
            basket.account = self.identifier
        else:
            basket.session_id = self.identifier

        if commit:
            basket.save()

        return basket


class FTEForm(forms.Form):
    """
    Form for entering FTE and currency
    """

    # TODO: break up this form into smaller functions

    currency = forms.ModelChoiceField(
        queryset=models.Country.objects.exclude(
            name__in=["EUROZONE", "Eurozone", "eurozone"]
        ),
        help_text="",  # Will be set in __init__
        label="",
    )
    fte = forms.IntegerField(
        help_text="",  # Will be set in __init__
        label="",  # Will be set in __init__
    )

    def __init__(self, *args, **kwargs):
        self.user_session = kwargs.pop("user_session")
        self.user = kwargs.pop("user")
        self.banding_types = kwargs.pop("banding_types")

        super(FTEForm, self).__init__(*args, **kwargs)

        # Load translatable strings from database
        self.fields["currency"].help_text = SiteText.objects.get(
            key="select_currency_note"
        ).body
        self.fields["fte"].help_text = SiteText.objects.get(
            key="fte_student_count_prompt"
        ).body
        self.fields["fte"].label = SiteText.objects.get(
            key="institutions_fte"
        ).body

        if self.user:
            self.fields["fte"].initial = self.user.profile.fte
        else:
            self.fields["fte"].initial = self.user_session.get("fte", 0)

        self.helper = FormHelper()
        layout = list()
        layout.append("currency")
        self.helper.layout = Layout(
            HTML('<h4 id="currency_section">Your Currency</h4>'),
            HTML(
                "<p><small>{}</small></p>".format(
                    SiteText.objects.get(key="after_currency_bandings_info").body
                )
            ),
            "currency",
        )

        if self.user:
            self.fields["currency"].initial = (
                self.user.profile.default_currency
                if self.user.profile.default_currency
                else None
            )
        else:
            self.fields["currency"].initial = self.user_session.get(
                "currency", 0
            )

        if not self.fields["currency"].initial:
            self.fields.pop("fte")
        else:
            self.helper.layout.append(
                Layout(
                    HTML("<h4>{}</h4>".format(
                        SiteText.objects.get(key="institution_details").body
                    )),
                    "fte",
                )
            )

        if self.fields["currency"].initial:
            for banding_type in self.banding_types:

                if banding_type.active:

                    session_string = "banding_type_{}".format(banding_type.pk)
                    choices = [["", "-----"]]
                    for vocab in banding_type.vocabs.all():
                        choices.append([vocab.pk, vocab.text])
                    self.fields[session_string] = forms.ChoiceField(
                        choices=choices,
                        label=banding_type.name,
                    )
                    if self.user:
                        account_banding_choice = (
                            accm.AccountBandingChoices.objects.filter(
                                account=self.user,
                                banding_type=banding_type,
                            ).first()
                        )
                        self.fields[session_string].initial = (
                            account_banding_choice.banding_type_vocab.pk
                            if account_banding_choice
                            else None
                        )
                    else:
                        self.fields[session_string].initial = (
                            self.user_session.get(session_string, None)
                        )

                    self.fields[session_string].help_text = (
                        banding_type.description
                    )

                    self.helper.layout.append(
                        Layout(session_string),
                    )
                    if "currency" in self.changed_data:
                        self.fields[session_string].required = False

        if "currency" in self.changed_data and self.fields.get("fte"):
            self.fields["fte"].required = False

        self.helper.layout.append(
            Submit(
                "fte_form",
                "Update",
                css_class="btn btn-primary btn-obc-blue",
            ),
        )

    def save(self) -> None:
        """
        Save the form
        :return:
        """
        for key, value in self.cleaned_data.items():
            if self.user:
                if key == "fte" and value:
                    self.user.profile.fte = value
                elif key == "currency" and value:
                    self.user.profile.default_currency = value
                elif value:
                    banding_type_pk = key.replace("banding_type_", "")
                    banding_type_vocab = vm.BandingVocab.objects.get(
                        pk=value,
                    )
                    accm.AccountBandingChoices.objects.update_or_create(
                        account=self.user,
                        banding_type_id=banding_type_pk,
                        defaults={
                            "banding_type_vocab": banding_type_vocab,
                        },
                    )
                self.user.profile.save()
            else:
                if key == "fte":
                    self.user_session[key] = value
                elif key == "currency":
                    self.user_session[key] = value.pk
                else:
                    self.user_session[key] = value


class ManagePackageForm(forms.ModelForm):
    """
    Form for managing packages
    """

    def __init__(self, *args, **kwargs):
        self.current_initiative = kwargs.pop("current_initiative")
        self.banding_type = kwargs.pop("banding_type")
        self.user = kwargs.pop("user")
        super(ManagePackageForm, self).__init__(*args, **kwargs)

        self.fields["default_country"].label = "Default currency"

        if not self.user.is_staff:
            self.fields.pop("active")
            self.fields.pop("recommended")
            self.fields.pop("signup_contacts")
            self.fields.pop("access_contacts")

    def save(self, commit=True) -> tuple[
        models.Package,
        models.BandingTypeEntry,
        models.BandingTypeCurrencyEntry,
    ]:
        """
        Save the form
        :param commit: whether to commit or not
        :return: tuple
        """
        package = super(ManagePackageForm, self).save(commit=False)
        bte, btce = None, None

        package.initiative = self.current_initiative
        package.banding_type = self.banding_type

        if commit:
            package.save()
            bte, c = models.BandingTypeEntry.objects.get_or_create(
                package=package,
                banding_type=self.banding_type,
            )
            btce, c = models.BandingTypeCurrencyEntry.objects.get_or_create(
                package=package,
                banding_type_entry=bte,
                country=package.default_country,
            )

        return package, bte, btce

    class Meta:
        model = models.Package
        exclude = (
            "initiative",
            "banding_type",
        )
        widgets = {
            "description": SummernoteWidget(),
        }


class MetaPackageForm(forms.ModelForm):
    """
    Form for managing meta packages
    """

    def __init__(self, *args, **kwargs):
        super(MetaPackageForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.add_input(Submit("submit", "Save"))

        self.fields["contact"].label_from_instance = (
            lambda obj: "%s %s (%s)"
            % (
                obj.first_name,
                obj.last_name,
                obj.email,
            )
        )

    def save(self, commit=True) -> models.MetaPackage:
        """
        Save the form
        :param commit: whether to commit or not
        :return: the meta package
        """
        meta_package = super(MetaPackageForm, self).save(commit=False)

        if commit:
            meta_package.save()

        return meta_package

    class Meta:
        model = models.MetaPackage
        exclude = ("banding_type",)
        widgets = {
            "packages": widgets.CheckboxSelectMultiple(),
        }


class FormElementForm(forms.ModelForm):
    """
    Form for managing form elements
    """

    class Meta:
        model = models.AggregateFormElement
        fields = ("name", "kind", "choices", "required")

    def __init__(self, *args, **kwargs):
        super(FormElementForm, self).__init__(*args, **kwargs)

    def save(self, commit=True) -> models.AggregateFormElement:
        """
        Save the form
        :param commit: whether to commit or not
        :return: the form element
        """
        form_element_form = super(FormElementForm, self).save(commit=False)

        # insert at the next highest order value
        new_order = models.AggregateFormElement.objects.aggregate(Max("order"))
        new_order = (
            new_order["order__max"] + 1 if new_order["order__max"] else 0
        )

        form_element_form.order = new_order

        if commit:
            form_element_form.save()

        return form_element_form


class CustomVocabM2M(forms.ModelMultipleChoiceField):
    """
    Custom M2M field for vocabularies
    """

    def label_from_instance(self, vocab):
        """
        Display the label for a vocabulary
        :param vocab: the vocabulary
        :return: the label
        """
        return "{}".format(vocab.m2m_display())

    widget = widgets.CheckboxSelectMultiple()


class BandingTypeForm(forms.ModelForm):
    """
    Form for managing banding types
    """

    class Meta:
        model = models.BandingType
        fields = ("name", "active", "is_fte")


class BandingTypeEntryRedirectForm(forms.ModelForm):
    """
    Form for managing banding type entries
    """

    class Meta:
        model = models.BandingTypeEntry
        fields = ("redirect_display", "redirect")


class DocumentUploadForm(forms.ModelForm):
    """
    Form for uploading documents
    """

    class Meta:
        model = models.PackageDocument
        fields = ("name", "pdf_file")

    def __init__(self, *args, **kwargs):
        self.package = kwargs.pop("package")
        super(DocumentUploadForm, self).__init__(*args, **kwargs)

    def save(self, commit=True) -> models.PackageDocument:
        """
        Save the form
        :param commit: whether to commit or not
        :return: the document
        """
        document_form = super(DocumentUploadForm, self).save(commit=False)
        document_form.package = self.package

        if commit:
            document_form.save()

        return document_form


class BandingTypeField(forms.Form):
    """
    Form for selecting banding types
    """

    bandings = forms.ModelChoiceField(
        queryset=models.BandingType.objects.all().distinct(), empty_label=None
    )


class StandardsTypeField(forms.Form):
    """
    Form for selecting standards
    """

    standards = forms.ModelChoiceField(
        queryset=vm.StandardVocab.objects.all().distinct(), empty_label=None
    )


class StandardsAttestForm(forms.ModelForm):
    """
    Form for managing standards attestations
    """

    class Meta:
        model = vm.PackageStandardAttestation
        fields = ("details_url",)

    def __init__(self, *args, **kwargs):
        self.package = kwargs.pop("package")
        self.standard = kwargs.pop("standard")
        super(StandardsAttestForm, self).__init__(*args, **kwargs)

    def save(self, commit=True) -> vm.PackageStandardAttestation:
        """
        Save the form
        :param commit: whether to commit or not
        :return: the standards attestation
        """
        attest = super(StandardsAttestForm, self).save(commit=False)

        attest.standard = self.standard
        attest.package = self.package

        if commit:
            attest.save()

        return attest


class CurrencyField(forms.Form):
    """
    Form for selecting currencies
    """

    currencies = forms.ModelChoiceField(
        queryset=models.Country.objects.all(),
        empty_label=None,
        label="Country",
    )


class FormListField(forms.Form):
    """
    Form for selecting form fields
    """

    form_fields = forms.ModelChoiceField(
        queryset=models.AggregateFormElement.objects.all(),
        empty_label=None,
        label="Form fields",
    )


class ManagePackageCurrencyForm(forms.Form):
    """
    Form for managing package currencies
    """

    def __init__(self, *args, **kwargs):
        self.current_initiative = kwargs.pop("initiative_id")
        self.banding_type = kwargs.pop("banding_type")
        self.package_id = kwargs.pop("package_id")
        self.currency = kwargs.pop("currency")
        super(ManagePackageCurrencyForm, self).__init__(*args, **kwargs)

        # dynamically add pricing fields to the form
        for v_banding in self.banding_type.vocabs.all():
            field_name = "banding-{}".format(str(v_banding.pk))
            self.fields[field_name] = forms.CharField(
                widget=forms.NumberInput(
                    attrs={"placeholder": "Enter price for banding."}
                ),
                required=True,
            )
            self.fields[field_name].label = v_banding.__str__()

            # see if we can populate the fields
            banding_vocab = v_banding

            package = models.Package.objects.get(pk=self.package_id)
            banding, c = models.Banding.objects.get_or_create(
                package=package,
                vocab=banding_vocab,
                banding_type=self.banding_type,
            )

            try:
                price = models.Price.objects.get(
                    banding=banding,
                    country=self.currency.country,
                )
                self.fields[field_name].initial = price.value
            except models.Price.DoesNotExist:
                self.fields[field_name].initial = 0

    def save(self, commit=True) -> None:
        """
        Save the form
        :param commit: whether to commit or not
        :return: None
        """
        # TODO: should this check the commit flag?
        for field in self._get_banding_fields():
            # get the object ID (sliced to remove 'banding-')
            object_id = int(field.name[8:])

            banding_vocab = vm.BandingVocab.objects.get(pk=object_id)
            package = models.Package.objects.get(pk=self.package_id)
            banding, c = models.Banding.objects.get_or_create(
                package=package,
                vocab=banding_vocab,
                banding_type=self.banding_type,
            )

            # delete existing prices
            prices = models.Price.objects.filter(
                banding=banding, country=self.currency.country
            )
            prices.delete()

            # enter new prices
            price, created = models.Price.objects.get_or_create(
                banding=banding,
                country=self.currency.country,
                value=field.value(),
            )
            price.save()

    def _get_banding_fields(self):
        """
        Get the banding fields
        :return: the banding fields
        """
        for field_name in self.fields:
            if field_name.startswith("banding-"):
                yield self[field_name]


def render_choices(choices) -> list:
    """
    Helper function to render choices
    :param choices: the choices to render
    :return: the rendered choices
    """
    c_split = choices.split("|")
    return [(choice.capitalize(), choice) for choice in c_split]


class GeneratedForm(forms.Form):
    """
    Form for generating forms
    """

    email_address = forms.EmailField(required=True)
    term_length = forms.ChoiceField(choices=[])  # Will be set in __init__

    def __init__(self, *args, **kwargs):
        order = kwargs.pop("order", None)
        fields_required = kwargs.pop("fields_required", True)
        email = kwargs.pop("email_address", None)
        term_length = kwargs.pop("term_length", 3)
        super(GeneratedForm, self).__init__(*args, **kwargs)

        # Load translatable strings from database
        try:
            months_text = SiteText.objects.get(key="months").body
        except SiteText.DoesNotExist:
            months_text = "months"

        # Set term length choices with translated text
        TERM_CHOICES = {
            "1": f"12 {months_text}",
            "3": f"36 {months_text}",
        }
        self.fields["term_length"].choices = TERM_CHOICES.items()

        # Set labels from SiteText
        try:
            self.fields["email_address"].label = SiteText.objects.get(
                key="email_address"
            ).body
        except SiteText.DoesNotExist:
            self.fields["email_address"].label = "Email address*"

        try:
            self.fields["term_length"].label = SiteText.objects.get(
                key="term_length"
            ).body
        except SiteText.DoesNotExist:
            self.fields["term_length"].label = "Term length*"

        self.helper = FormHelper()
        self.helper.form_method = "post"

        # Load Save button text from SiteText
        try:
            save_text = SiteText.objects.get(key="save_button").body
        except SiteText.DoesNotExist:
            save_text = "Save"

        self.helper.add_input(
            Submit("save", save_text, css_class="btn btn-primary btn-obc-blue")
        )

        elements = order.data_to_collect

        for element in elements:
            if element.kind == "text":
                self.fields[str(element.pk)] = forms.CharField(
                    widget=forms.TextInput(attrs={"div_class": element.width}),
                    required=element.required if fields_required else False,
                )
            elif element.kind == "textarea":
                self.fields[str(element.pk)] = forms.CharField(
                    widget=forms.Textarea,
                    required=element.required if fields_required else False,
                )
            elif element.kind == "date":
                self.fields[str(element.pk)] = forms.CharField(
                    widget=forms.DateInput(
                        attrs={
                            "class": "datepicker",
                            "div_class": element.width,
                        }
                    ),
                    required=element.required if fields_required else False,
                )
            elif element.kind == "upload":
                self.fields[str(element.pk)] = forms.FileField(
                    required=element.required if fields_required else False
                )
            elif element.kind == "select":
                choices = render_choices(element.choices)
                self.fields[str(element.pk)] = forms.ChoiceField(
                    widget=forms.Select(attrs={"div_class": element.width}),
                    choices=choices,
                    required=element.required if fields_required else False,
                )
            elif element.kind == "email":
                self.fields[str(element.pk)] = forms.EmailField(
                    widget=forms.TextInput(attrs={"div_class": element.width}),
                    required=element.required if fields_required else False,
                )
            elif element.kind == "check":
                self.fields[str(element.pk)] = forms.BooleanField(
                    widget=forms.CheckboxInput(attrs={"is_checkbox": True}),
                    required=element.required if fields_required else False,
                )

            self.fields[str(element.pk)].help_text = element.help_text
            self.fields[str(element.pk)].label = element.name

        answers = models.OrderFormAnswer.objects.filter(
            order=order,
        )
        for answer in answers:
            if self.fields[str(answer.form_element.pk)]:
                self.fields[str(answer.form_element.pk)].initial = (
                    answer.answer
                )

        self.fields["email_address"].initial = email
        self.fields["term_length"].initial = term_length


class CustomDocumentForm(forms.ModelForm):
    """
    Form for custom documents
    """

    class Meta:
        model = models.CustomPackageDocument
        fields = ("name", "pdf_file")

    def __init__(self, *args, **kwargs):
        self.package_signup = kwargs.pop("package_signup")
        super(CustomDocumentForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.add_input(Submit("submit", "Save"))

    def save(self, commit=True) -> models.CustomPackageDocument:
        """
        Save the form
        :param commit: whether to commit or not
        :return: the document
        """
        document_form = super(CustomDocumentForm, self).save(commit=False)
        document_form.package_signup = self.package_signup

        if commit:
            document_form.save()

        return document_form


class OrderForm(forms.ModelForm):
    """
    Form for orders
    """

    def __init__(self, *args, **kwargs):
        self.initiative = kwargs.pop("initiative", None)
        super(OrderForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.add_input(Submit("submit", "Save"))
        self.fields["associated_user"].label_from_instance = (
            lambda obj: "%s" % obj.get_full_name()
        )

        if self.initiative:
            self.fields["status"].widget = forms.HiddenInput()
            self.fields["status"].initial = "complete"
            self.fields["initiative"].widget = forms.HiddenInput()
            self.fields["initiative"].initial = self.initiative

    class Meta:
        model = models.Order
        fields = (
            "order_number",
            "associated_user",
            "initiative",
            "order_date",
            "valid_period",
            "status",
            "proxy_signup_information",
        )
        widgets = {
            "proxy_signup_information": SummernoteWidget(),
        }


class PrivateImageForm(forms.ModelForm):
    """
    Form for private images
    """

    class Meta:
        model = PrivateImage
        fields = ("image",)

    def __init__(self, *args, **kwargs):
        self.order = kwargs.pop("order")
        super(PrivateImageForm, self).__init__(*args, **kwargs)

    def save(self, commit=True) -> PrivateImage:
        """
        Save the form
        :param commit: whether to commit or not
        :return: the image
        """
        image = super(PrivateImageForm, self).save()
        self.order.private_images.add(image)

        return image


class MediaFileForm(forms.ModelForm):
    """
    Form for media files
    """

    class Meta:
        model = models.MediaFile
        fields = ("name", "file")

    def __init__(self, *args, **kwargs):
        self.package = kwargs.pop("package")
        super(MediaFileForm, self).__init__(*args, **kwargs)

    def save(self, commit=True) -> models.MediaFile:
        """
        Save the form
        :param commit: whether to commit or not
        :return: the media file
        """
        file = super(MediaFileForm, self).save(commit=False)
        file.package = self.package

        if commit:
            file.save()

        return file


class CountryForm(forms.Form):
    country = forms.ModelChoiceField(
        queryset=models.Country.objects.exclude(
            name__in=["EUROZONE", "Eurozone", "eurozone"]
        ),
        help_text="Select your preferred country.",
        label="Countries",
    )

    def __init__(self, *args, **kwargs):
        session_country_code = kwargs.pop("session_country_code")
        super(CountryForm, self).__init__(*args, **kwargs)
        if session_country_code:
            country = models.Country.objects.filter(
                code=session_country_code,
            ).first()
            if country:
                self.fields["country"].initial = country.pk
