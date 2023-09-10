from django.contrib import admin

from intrepid import models

admin_list = [
    (models.SiteSetup,),
]

[admin.site.register(*t) for t in admin_list]
