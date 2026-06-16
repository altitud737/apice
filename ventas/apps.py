from django.apps import AppConfig


class VentasConfig(AppConfig):
    name = 'ventas'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        from . import signals  # noqa: F401
