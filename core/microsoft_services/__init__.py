"""
Microsoft Services Package - DSP (Digital Solutions Platform)

Dieses Paket enthält alle Integrationen und Hilfsmodule für Microsoft Azure AD,
OAuth 2.0, Microsoft Graph API und rollenbasierte Authentifizierung.

Struktur:
- authentications: OAuth-Flow-Management
- core_integrations: Token-Management, Rollen, Mixins
- graph_apis: Erweiterte GraphAPI-Integrationen
- models: Persistente OAuth-State- und User-Mappings
- admin: Admin-Interfaces für OAuth States

Author: DSP Development Team
Created: 10.07.2025
Version: 1.0.0
"""

default_app_config = "core.microsoft_services.apps.MicrosoftServicesConfig"
