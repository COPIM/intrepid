from django import forms

from cms import utils
from initiatives import models


class InitiativeForm(forms.ModelForm):
    """
    A form that represents an initiative
    """

    class Meta:
        model = models.Initiative
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")

        super(InitiativeForm, self).__init__(*args, **kwargs)

        if self.request.user.is_staff or self.request.user.is_superuser:
            # if platform manager
            pass
        else:
            if "users" in self.fields:
                del self.fields["users"]

    def clean_image(self):
        """
        Resize the image to 335x100
        :return: a resized image
        """
        img = self.cleaned_data.get("image")

        return utils.resize_image(335, 100, img)
