"""
Shift Planner App Configuration - DSP (Digital Solutions Platform)

Dieses Modul enthält die Django App-Konfiguration für das Shift Planner Tool.
Die App stellt Schichtplanungs- und Mitarbeiterverwaltungsfunktionen bereit.

Features:
- Bereitstellung von Schichtplanungs-Views und Models
- Integration in das zentrale DSP-Backend
- Ermöglicht Erweiterungen für zukünftige Schichtplanungs-Funktionalitäten

Status: In Entwicklung - Grundkonfiguration implementiert

Author: DSP Development Team
Created: 10.07.2025
Version: 1.0.0
"""

from django.apps import AppConfig


class ShiftPlannerConfig(AppConfig):
    """
    Django AppConfig für das Shift Planner Modul.
    
    Initialisiert die App und stellt Metadaten bereit.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'shift_planner'
    verbose_name = 'Shift Planner'
