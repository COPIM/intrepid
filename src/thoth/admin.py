from django.contrib import admin

from thoth import models


class WorkAdmin(admin.ModelAdmin):
    list_display = ("pk", "full_title", "doi", "publisher")
    list_filter = ("publisher",)


class ThemaAdmin(admin.ModelAdmin):
    list_display = ("pk", "code", "heading")


class InstitutionAdmin(admin.ModelAdmin):
    list_display = ("pk", "institution_name", "ror")


class BICAdmin(admin.ModelAdmin):
    list_display = ("pk", "code", "heading")


class RORAdmin(admin.ModelAdmin):
    ...


class SubjectAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "subject_display",
        "subject_code",
        "subject_type",
        "work",
    )
    list_filter = ("subject_type",)


class PublisherAdmin(admin.ModelAdmin):
    list_display = ("pk", "publisher_name")


class ContributorAdmin(admin.ModelAdmin):
    list_display = ("pk", "full_name")


class ThothSearchAdmin(admin.ModelAdmin):
    list_display = ("pk", "display_name")


class ContributionAdmin(admin.ModelAdmin):
    list_display = ("pk", "contributor_name", "contribution_type", "work_name")
    list_filter = ("work__publisher",)

    def contributor_name(self, obj):
        if obj.contributor:
            return obj.contributor.full_name
        else:
            """"""

    contributor_name.admin_order_field = "full_name"
    contributor_name.short_description = "Contributor Name"

    def work_name(self, obj):
        if obj.contributor:
            return obj.work.full_title
        else:
            return ""

    work_name.admin_order_field = "full_title"
    work_name.short_description = "Work Name"


admin_list = [
    (models.Work, WorkAdmin),
    (models.Publisher, PublisherAdmin),
    (models.Contributor, ContributorAdmin),
    (models.Contribution, ContributionAdmin),
    (models.Institution, InstitutionAdmin),
    (models.Subject, SubjectAdmin),
    (models.Thema, ThemaAdmin),
    (models.BIC, BICAdmin),
    (models.RORRecord, RORAdmin),
    (models.ThothSearch, ThothSearchAdmin),
]

[admin.site.register(*t) for t in admin_list]
