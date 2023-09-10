from django.apps import AppConfig


class ApplicationConfig(AppConfig):
    name = "package"

    def ready(self):
        pass
