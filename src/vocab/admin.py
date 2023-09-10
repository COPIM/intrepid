from django.contrib import admin

from vocab import models


admin_list = [
    (models.BandingVocab,),
    (models.AttestationHistory,),
    (models.SubjectVocab,),
]

[admin.site.register(*t) for t in admin_list]
