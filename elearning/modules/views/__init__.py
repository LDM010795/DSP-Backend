"""
E-Learning Modules Views Package - DSP (Digital Solutions Platform)

Dieses Paket enthält alle Views für das Lernmodul-System.
Ermöglicht Modul-Verwaltung, Inhaltsdarstellung und Code-Ausführung.

Features:
- Modul-Liste und Detail-Views für Benutzer
- Öffentliche und private Modul-Zugriffe
- Interaktive Code-Ausführung für Programmieraufgaben
- Modul-Erstellung und -Verwaltung für Administratoren
- Kategorisierung und Inhaltsverwaltung
- Automatische Content-Verarbeitung aus Cloud Storage
- Automatische Artikel-Verarbeitung aus Cloud-URLs

Author: DSP Development Team
Created: 10.07.2025
Version: 1.0.0
"""

from .module_views import *
from .execute_python_code import *
from .content_processing_views import *
from .article_processing_views import *
