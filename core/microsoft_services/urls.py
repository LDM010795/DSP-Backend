"""
Microsoft Services URLs - DSP (Digital Solutions Platform)

Dieses Modul definiert die URL-Routing-Konfiguration für Microsoft OAuth und Integrationsendpunkte.
Stellt konsistente, RESTful Endpunkte für Login, Callback und Token-Exchange bereit.

Features:
- Refactored OAuth-Flow mit tool-spezifischen Logins
- Trennung von Callback- und Token-Exchange-Endpoints
- Erweiterbar für zukünftige Microsoft-Integrationsendpunkte

Author: DSP Development Team
Created: 10.07.2025
Version: 1.0.0
"""

from django.urls import path
from .authentications.views import (
    MicrosoftLoginRedirectView,
    MicrosoftCallbackView,
)

app_name = "microsoft_services"

urlpatterns = [
    # Refactored Authentication Flow
    path(
        "auth/login/<str:tool_slug>/",
        MicrosoftLoginRedirectView.as_view(),
        name="microsoft-login-redirect",
    ),
    # This is the generic callback URL that Microsoft redirects to.
    path(
        "auth/callback/",
        MicrosoftCallbackView.as_view(),
        name="microsoft-callback-passthrough",
    ),
    # This is the endpoint the frontend POSTs the code to.
    path(
        "auth/callback/<str:tool_slug>/",
        MicrosoftCallbackView.as_view(),
        name="microsoft-callback-exchange",
    ),
] 