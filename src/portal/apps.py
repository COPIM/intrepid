from django.apps import AppConfig


class PortalConfig(AppConfig):
    name = "portal"
    verbose_name = "Document Portal"

    def ready(self):
        # Connect the notification-enqueue signal.
        from portal import signals  # noqa: F401
