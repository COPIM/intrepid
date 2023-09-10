from django import forms
from django.contrib import admin
from django_bleach.models import BleachField

from cms import models


class PageAdmin(admin.ModelAdmin):
    """
    Admin for the Page model.
    """

    list_display = (
        "title",
        "updated_by",
    )
    raw_id_fields = (
        "updated_by",
        "current_version",
    )
    readonly_fields = ("created",)
    filter_horizontal = ("other_versions",)


class VersionAdmin(admin.ModelAdmin):
    """
    Admin for the Version model.
    """

    list_display = ("created", "created_by")
    formfield_overrides = {
        BleachField: {"widget": forms.Textarea},
    }


class SiteTextAdmin(admin.ModelAdmin):
    """
    Admin for the SiteText model.
    """

    list_display = ("key", "rich_text", "pk")
    save_as = True


admin_list = [
    (models.PageUpdate, PageAdmin),
    (models.Version, VersionAdmin),
    (models.SiteText, SiteTextAdmin),
]

[admin.site.register(*t) for t in admin_list]
