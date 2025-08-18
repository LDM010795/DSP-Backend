"""
E-Learning Users Views Package - DSP (Digital Solutions Platform)

Dieses Paket enthält alle Views für die Benutzerverwaltung im E-Learning-System.
Ermöglicht Authentifizierung, Benutzer-CRUD-Operationen und Passwortverwaltung.

Features:
- JWT-basierte Authentifizierung mit erweiterten Tokens
- Benutzer-CRUD-Operationen mit Admin-Rechten
- Sichere Passwortverwaltung und -änderung
- Logout-Funktionalität mit Token-Invalidierung

Author: DSP Development Team
Created: 10.07.2025
Version: 1.0.0
"""

from .auth_views import (
    CustomTokenObtainPairView,
    LogoutView,
    SetInitialPasswordView,
    ExternalUserRegistrationView,
)
from .user_crud_view import UserCrudViewSet
