"""
E-Learning Application Configuration

This module contains the Django application configuration for the E-Learning system.
It defines the application's metadata, default field configurations, and any
application-specific initialization logic.

The E-Learning application provides comprehensive digital learning functionality
including user management, module systems, interactive content, and examination
capabilities with certification paths.

Author: DSP Development Team
Version: 1.0.0
"""

from django.apps import AppConfig


class ElearningConfig(AppConfig):
    """
    Configuration class for the E-Learning Django application.

    This class defines the application's configuration including default field types,
    application name, and any initialization logic required for the E-Learning system.

    Attributes:
        default_auto_field: Default primary key field type for models
        name: Application name for Django registration
        verbose_name: Human-readable application name for admin interface
    """

    default_auto_field: str = "django.db.models.BigAutoField"
    name: str = "elearning"
    verbose_name: str = "E-Learning System"

    def ready(self) -> None:
        """
        Initialize the application when Django starts.

        This method is called when the application is ready and can be used
        to perform any initialization logic such as signal registration,
        custom model validation, or other startup tasks.

        Note: This method should be idempotent and safe to call multiple times
        during testing or application reloads.
        """
        super().ready()
        return
