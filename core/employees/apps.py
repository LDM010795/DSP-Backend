"""
Employee Management App Configuration - DSP (Digital Solutions Platform)

Dieses Modul enthält die Django App-Konfiguration für das Mitarbeiter-Management.
Die App employees verwaltet alle Kernfunktionen rund um Mitarbeiter, Abteilungen,
Positionen, Anwesenheiten und Tool-Zugriffsrechte.

Features:
- Bereitstellung von Models, Views, Serializers und Admin für Employee Management
- Integration in das zentrale DSP-Backend
- Ermöglicht Erweiterungen für zukünftige HR-Funktionalitäten

Author: DSP Development Team
Created: 10.07.2025
Version: 1.0.0
"""

from django.apps import AppConfig


class EmployeesConfig(AppConfig):
    """
    Django AppConfig für das Employee Management Modul.
    
    Initialisiert die App und stellt Metadaten bereit.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.employees'
    label = 'employees'
