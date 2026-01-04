from django.apps import AppConfig


class IntegrationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.integrations"
    verbose_name = "Integrations"

    def ready(self):
        """Register signal receivers when app is ready."""
        # Import receivers to register signal handlers
        # Import pipeline signals for status-based task dispatch
        from apps.integrations import (
            pipeline_signals,  # noqa: F401
            receivers,  # noqa: F401
        )
