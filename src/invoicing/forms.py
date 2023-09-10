from django import forms

from invoicing import models


class StatusForm(forms.Form):
    """
    Form for changing the status of an invoice.
    """

    status = forms.ChoiceField(
        choices=models.status_choices(),
        widget=forms.Select(attrs={"class": "form-control"}),
    )


class PaymentProcessorForm(forms.ModelForm):
    """
    Form for creating a new payment processor.
    """

    class Meta:
        model = models.PaymentProcessor
        exclude = ()
