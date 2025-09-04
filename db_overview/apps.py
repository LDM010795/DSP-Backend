"""
Database Overview App Configuration - DSP (Digital Solutions Platform)

Dieses Modul enthält die Django App-Konfiguration für das Database Overview Tool.
Die App stellt umfassende Datenbankanalyse- und Visualisierungsfunktionen bereit.

Features:
- Bereitstellung von Schema-Analyse-Views und Models
- Integration in das zentrale DSP-Backend
- Ermöglicht Erweiterungen für zukünftige Datenbankanalyse-Funktionalitäten

Author: DSP Development Team
Created: 10.07.2025
Version: 1.0.0
"""

from django.apps import AppConfig


class DbOverviewConfig(AppConfig):
    """
    Django AppConfig für das Database Overview Modul.

    Initialisiert die App und stellt Metadaten bereit.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "db_overview"
    verbose_name = "Database Overview"
