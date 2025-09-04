"""
Stripe Integration AppConfig
============================

This module defines the Django application configuration for the local
`core.stripe_integration`. It is responsible for:

- Registering with Django (name, verbose label, default PK field).
- Importing the signal handlers at startup so that webhook-related
  logic (listening to `djstripe.models.Event` via `post_save`) is connected.

Django only connects signal receivers once the app registry is fully loaded.
Importing `.signals` here ensures our receivers are registered exactly once
for each process (runserver, gunicorn worker, Celery worker, etc.).

Operational notes
-----------------
- Keep side effects in `ready()` minimal and idempotent (only import the
  module that wires up signal receivers).
- `apps.py` is executed on every process start; avoid DB/network calls here.
- If you ever need to temporarily disable webhook processing (e.g. during
  a migration), you can comment out the signals import below.

Author: DSP Development Team
Date: 2025-09-03
"""

from django.apps import AppConfig


class StripeIntegrationConfig(AppConfig):
    """
    App configuration for the `core.stripe_integration` package.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "core.stripe_integration"
    verbose_name = "Stripe Integration"

    def ready(self):
        # Import signals so Django registers the post_save handler for dj-stripe Event
        from . import signals  # noqa: F401
