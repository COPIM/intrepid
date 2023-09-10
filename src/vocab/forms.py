from django import forms

from vocab import models


class NewVocabForm(forms.ModelForm):
    """
    Form for creating a new vocab word.
    """

    class Meta:
        model = models.BandingVocab
        exclude = ("order",)

    def __init__(self, *args, **kwargs):
        super(NewVocabForm, self).__init__(*args, **kwargs)


class NewStandardForm(forms.ModelForm):
    """
    Form for creating a new standard.
    """

    class Meta:
        fields = ("standard_name", "text")
        model = models.StandardVocab


class SubjectForm(forms.ModelForm):
    """
    Form for creating a new subject.
    """

    class Meta:
        model = models.SubjectVocab
        fields = ("name",)
