from django.contrib import admin

from invoicing import models

admin_list = [
    (models.PaymentProcessor,),
    (models.SignupInvoice,),
    (models.InvoiceLog,),
]

[admin.site.register(*t) for t in admin_list]
