"""
E-Learning Users Package - DSP (Digital Solutions Platform)

Dieses Paket enthält alle Module für die Benutzerverwaltung im E-Learning-System.
Ermöglicht erweiterte Benutzerprofile, Authentifizierung und Benutzerverwaltung.

Features:
- Erweiterte Benutzerprofile mit Sicherheitseinstellungen
- JWT-basierte Authentifizierung mit erweiterten Tokens
- Automatische Profilerstellung durch Django-Signale
- Sichere Passwortverwaltung mit Bestätigung
- Management-Commands für Benutzerbereinigung

Struktur:
- models.py: Benutzerprofile und Signal-Handler
- serializers.py: API-Serialisierung für Benutzerdaten
- views/: Authentifizierungs- und CRUD-Views
- management/: Django Management Commands

Author: DSP Development Team
Created: 10.07.2025
Version: 1.0.0
"""
