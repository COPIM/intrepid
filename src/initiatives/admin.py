from django.contrib import admin

from django_bleach.models import BleachField
from django_summernote.widgets import SummernoteWidget

from initiatives import models


class InitiativeAdmin(admin.ModelAdmin):
    list_display = ('name',)
    filter_horizontal = ('users',)
    formfield_overrides = {
        BleachField: {'widget': SummernoteWidget},
    }


class HighlightsAdmin(admin.ModelAdmin):
    list_display = ('pk', 'package', 'title')
    formfield_overrides = {
        BleachField: {'widget': SummernoteWidget},
    }


admin_list = [
    (models.Initiative, InitiativeAdmin),
    (models.Highlights, HighlightsAdmin),
]

[admin.site.register(*t) for t in admin_list]
