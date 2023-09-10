from django.contrib import admin

from accounts import models


class ProfileAdmin(admin.ModelAdmin):
    list_display = ("account",)
    raw_id_fields = ("account",)


admin_list = [
    (models.Profile, ProfileAdmin),
    (models.AccountBandingChoices,),
]

[admin.site.register(*t) for t in admin_list]
