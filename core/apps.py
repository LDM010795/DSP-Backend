"""
Core App Configuration - DSP (Digital Solutions Platform)

This module contains the Django app configuration for the core application.
The core app serves as the foundation for shared functionality across
all DSP applications.

Features:
- Provides base models, views, and utilities
- Houses employee management functionality
- Contains Microsoft Azure AD integration services
- Serves as a central hub for cross-application features

Author: DSP Development Team
Created: 10.07.2025
Version: 1.0.0
"""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
