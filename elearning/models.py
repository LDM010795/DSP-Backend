"""
Zentrale Model-Datei für die 'elearning' App.

Diese Datei dient als Haupt-Einstiegspunkt für Django, um alle Modelle
der E-Learning-Funktionalität zu erkennen.

Sie importiert die Modelle aus den jeweiligen logischen Untermodulen
(users, modules, final_exam), sodass sie alle unter dem Namespace
der 'elearning'-App registriert werden.
"""

# Importiere alle Modelle aus dem 'users'-Modul
from .users.models import *

# Importiere alle Modelle aus dem 'modules'-Modul
from .modules.models import *

# Importiere alle Modelle aus dem 'final_exam'-Modul
from .final_exam.models import *
