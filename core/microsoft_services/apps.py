"""
Microsoft Services App Configuration - DSP (Digital Solutions Platform)

Dieses Modul enthält die Django App-Konfiguration für die Microsoft-Integrationsdienste.
Die App stellt zentrale OAuth-, GraphAPI- und rollenbasierte Authentifizierungsfunktionen
für alle DSP-Anwendungen bereit.

Features:
- Bereitstellung von OAuth- und Microsoft Graph-Integrationen
- Zentrale Verwaltung von Authentifizierungs- und Autorisierungs-Workflows
- Erweiterbar für zukünftige Microsoft-Dienste

Author: DSP Development Team
Created: 10.07.2025
Version: 1.0.0
"""

from django.apps import AppConfig


class MicrosoftServicesConfig(AppConfig):
    """
    Django AppConfig für das Microsoft Services Modul.
    
    Initialisiert die App und stellt Metadaten bereit.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.microsoft_services'
    label = 'microsoft_services'
