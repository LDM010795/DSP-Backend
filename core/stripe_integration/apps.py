from django.apps import AppConfig

class StripeIntegrationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core.stripe_integration"
    verbose_name = "Stripe Integration"

    def ready(self):
        # Import signals so Django registers the post_save handler for dj-stripe Event
        from . import signals  # noqa: F401