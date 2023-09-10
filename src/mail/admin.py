from django.contrib import admin

from mail import models


class EmailLogAdmin(admin.ModelAdmin):
    list_display = ("pk", "to", "from_email", "subject", "date_sent")


admin_list = [
    (models.EmailLog, EmailLogAdmin),
    (models.EmailTemplate,),
]

[admin.site.register(*t) for t in admin_list]
