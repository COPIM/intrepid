from django.apps import AppConfig


class InvoicingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'invoicing'

    def ready(self):
        # Implicitly connect a signal handlers decorated with @receiver.
        from invoicing import signals
