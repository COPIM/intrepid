from django import forms

from access import models


class ContactForm(forms.ModelForm):
    class Meta:
        model = models.Contact
        fields = (
            "name",
            "email",
            "initiative",
        )

    def __init__(self, *args, **kwargs):
        # pop requests and call super constructor
        self.request = kwargs.pop("request")
        super(ContactForm, self).__init__(*args, **kwargs)

        # Restrict the initiatives queryset to the middleware-set
        self.fields["initiative"].queryset = self.request.initiatives


class AccessLogForm(forms.ModelForm):
    class Meta:
        model = models.AccessLog
        fields = (
            "access_type",
            "date_stamp",
            "ip_range",
            "payment_handler",
        )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        self.signup = kwargs.pop("signup")
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        access_log = super(AccessLogForm, self).save(commit=False)
        access_log.user = self.request.user
        access_log.signup = self.signup

        if commit:
            access_log.save()

        return access_log
