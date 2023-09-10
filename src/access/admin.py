from django.contrib import admin

from access import models


class ContactAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "initiative")


class AccessLogAdmin(admin.ModelAdmin):
    list_display = (
        "signup",
        "access_type",
        "user",
        "date_stamp",
    )


admin_list = [
    (models.Contact, ContactAdmin),
    (models.AccessLog, AccessLogAdmin),
]

[admin.site.register(*t) for t in admin_list]
