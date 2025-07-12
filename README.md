# DSP-Backend - Entwickler-Onboarding & Projekt-Guide

## 📋 Inhaltsverzeichnis

1. [Projekt-Übersicht](#projekt-übersicht)
2. [Architektur & Struktur](#architektur--struktur)
3. [Entwicklungsumgebung & Workflow](#entwicklungsumgebung--workflow)
4. [Django Apps im Detail](#django-apps-im-detail)
5. [API-Struktur & Endpunkte](#api-struktur--endpunkte)
6. [Code-Standards & Best Practices](#code-standards--best-practices)
7. [Debugging & Troubleshooting](#debugging--troubleshooting)
8. [Häufige Aufgaben](#häufige-aufgaben)

---

## 🎯 Projekt-Übersicht

**DSP-Backend** ist das **zentrale Backend-System** für alle DSP-Anwendungen. Es fungiert als API-Server und stellt wiederverwendbare Core-Funktionalitäten bereit, die von verschiedenen Frontend-Anwendungen genutzt werden können.

### 🏢 Unterstützte Anwendungen

- **E-Learning DSP** (Port 5173) - Digitale Lernplattform ⭐ **Hauptfokus**
- **Shift-Planner** (Port 5174) - Schichtplanung für Mitarbeiter
- **DSP-DB-Overview** (Port 5175) - Datenbankanalyse-Tool

### 🏗️ Design-Prinzipien

- **Core-Backend**: Zentrale, wiederverwendbare Logiken (Microsoft Auth, etc.)
- **Modularität**: Jede App ist ein abgekapseltes Backend für ein spezifisches Frontend
- **Enterprise-Ready**: Microsoft Azure AD Integration, umfassende Sicherheit
- **Developer Experience**: Klare Strukturen und umfassende Dokumentation

---

## 🏗️ Architektur & Struktur

### 📁 Projektstruktur

```
DSP-Backend/
├── backend/                 # Django-Projekt-Konfiguration
│   ├── settings.py         # Hauptkonfiguration (dev/prod)
│   ├── urls.py             # Root URL-Konfiguration
│   └── wsgi.py             # WSGI-Konfiguration
├── core/                   # Zentrale, wiederverwendbare Funktionalität
│   ├── employees/          # Mitarbeiterverwaltung (Core-Logik)
│   └── microsoft_services/ # Microsoft Azure AD Integration (Core-Logik)
├── elearning/              # E-Learning-Plattform Backend
├── db_overview/            # Datenbankanalyse-Tool Backend
├── shift_planner/          # Schichtplanung Backend
├── manage.py               # Django Management
├── requirements.txt        # Python-Dependencies
└── render.yml              # Production Deployment
```

### 🔄 Datenfluss-Architektur

```
Frontend Apps → Django Backend → Database
     ↓              ↓              ↓
  React/Vue    REST API      PostgreSQL/SQLite
     ↓              ↓              ↓
  Microsoft    JWT Auth      Django ORM
  OAuth 2.0    + Caching     + Migrations

Core-Logiken (Microsoft Auth, Employees) werden von allen Apps genutzt
```

---

## 🚀 Entwicklungsumgebung & Workflow

### 1. Repository Setup

```bash
# Repository klonen
git clone <repository-url>
cd DSP-Backend

# Auf develop Branch wechseln (Hauptentwicklungsbranch)
git checkout develop
git pull origin develop
```

### 2. Entwicklungsumgebung einrichten

```bash
# Virtual Environment erstellen
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Dependencies installieren
pip install -r requirements.txt
```

### 3. Environment-Konfiguration

```bash
# .env Datei wird vom Team zur Verfügung gestellt
# Diese enthält alle notwendigen Konfigurationen für die Entwicklung
```

### 4. Datenbank initialisieren

```bash
# Migrationen ausführen
python manage.py migrate

# Superuser erstellen
python manage.py createsuperuser

# Test-Daten laden (optional)
python manage.py seed_test_data
```

### 5. Entwicklungsserver starten

```bash
# Server starten
python manage.py runserver

# Admin-Interface: http://localhost:8000/admin/
# API-Browser: http://localhost:8000/api/
```

---

## 🔄 Git-Workflow

### 📋 Branch-Strategie

#### Wichtige Branches:

- **`main`**: Live-Zustand (gesperrt für direkte Pushes)
- **`develop`**: Hauptentwicklungsbranch (alle Entwickler arbeiten hierauf)
- **`feature/*`**: Feature-Branches für neue Entwicklungen

#### Workflow für Entwickler:

```bash
# 1. Feature-Branch erstellen (von develop)
git checkout develop
git pull origin develop
git checkout -b feature/neue-funktion

# 2. Entwicklung und lokales Testen
# - Code entwickeln
# - Lokal testen (visuell und funktional)
# - Commits machen

# 3. Feature-Branch pushen
git add .
git commit -m "feat: neue API-Endpoint für Benutzerverwaltung"
git push origin feature/neue-funktion

# 4. Pull Request auf GitHub erstellen
# - GitHub Repository öffnen
# - "Compare & pull request" klicken
# - Base: develop, Compare: feature/neue-funktion
# - Beschreibung schreiben, Reviewer zuweisen
# - "Create pull request" klicken

# 5. Review-Prozess
# - Lead Developer reviewed den Code
# - Nach Approval: Merge durch Lead
# - Feature-Branch wird automatisch gelöscht

# 6. Nächstes Feature (während Review läuft)
git checkout develop
git pull origin develop
git checkout -b feature/naechste-funktion
```

### 🎯 Beispiel-Arbeitsablauf

#### Szenario: Neuer API-Endpoint für E-Learning

```bash
# 1. Repository klonen (falls noch nicht geschehen)
git clone <repository-url>
cd DSP-Backend

# 2. Auf develop Branch
git checkout develop
git pull origin develop

# 3. Feature-Branch erstellen
git checkout -b feature/elearning-module-api

# 4. Entwicklungsumgebung starten
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 5. Server starten
python manage.py runserver

# 6. Entwicklung und Testen
# - API-Endpoint implementieren
# - Lokal testen mit Postman/curl
# - Frontend-Integration testen

# 7. Commits machen
git add .
git commit -m "feat: add module list API endpoint"
git commit -m "test: add unit tests for module API"

# 8. Feature-Branch pushen
git push origin feature/elearning-module-api

# 9. Pull Request auf GitHub erstellen
# - GitHub Repository öffnen: https://github.com/LDM010795/DSP-Backend
# - "Compare & pull request" für feature/elearning-module-api klicken
# - Base branch: develop, Compare branch: feature/elearning-module-api
# - Titel: "feat: add module list API endpoint"
# - Beschreibung: Details zum API-Endpoint
# - Reviewer: @LinoDeMarco zuweisen
# - "Create pull request" klicken
```

---

## 📦 Django Apps im Detail

### 🔧 Core Apps (Zentrale, wiederverwendbare Funktionalität)

#### `core.employees` - Mitarbeiterverwaltung

**Zweck**: Zentrale Mitarbeiterverwaltung für alle DSP-Anwendungen

**Wichtige Dateien:**

- `models.py` - Employee, Department Models
- `views.py` - CRUD-Operationen für Mitarbeiter
- `serializers.py` - API-Serialisierung

**Verwendung:**

```python
from core.employees.models import Employee, Department

# Mitarbeiter abrufen
employee = Employee.objects.get(user_id=user_id)

# Abteilung mit Mitarbeitern
department = Department.objects.prefetch_related('employees').get(id=dept_id)
```

#### `core.microsoft_services` - Microsoft Azure AD Integration ⭐

**Zweck**: Enterprise-Level OAuth 2.0 Authentifizierung (wiederverwendbar)

**Submodule-Struktur:**

```
microsoft_services/
├── authentications/        # OAuth Flow Management
│   ├── base.py           # Core Microsoft OAuth Client
│   ├── handlers.py       # Business Logic
│   └── views.py          # OAuth API Endpoints
├── core_integrations/     # Advanced Features
│   ├── mixins.py         # GraphAPI Base
│   ├── token_manager.py  # JWT Token Management
│   ├── role_authentication.py # Role-Based Auth
│   └── exceptions.py     # Custom Exceptions
└── graph_apis/           # Microsoft Graph API
```

**Verwendung:**

```python
from core.microsoft_services.authentications.handlers import MicrosoftAuthHandler
from core.microsoft_services.core_integrations.token_manager import TokenManager

# OAuth-Flow starten
auth_handler = MicrosoftAuthHandler()
redirect_url = auth_handler.start_login_flow(tool_slug="e-learning")

# Token validieren
token_manager = TokenManager()
is_valid = token_manager.validate_token(access_token)
```

### 🎓 Business Apps (Abgekapselte Backends)

#### `elearning` - Digitale Lernplattform ⭐

**Zweck**: Vollständige E-Learning-Plattform mit Modulen, Aufgaben und Prüfungen

**Submodule-Struktur:**

```
elearning/
├── users/                 # User Management
│   ├── models.py         # Profile, User Extensions
│   ├── views/            # User CRUD, Authentication
│   └── serializers.py    # User API Serialization
├── modules/              # Learning Content
│   ├── models.py         # Module, Task, Content Models
│   ├── views/            # Module API, Python Execution
│   └── serializers.py    # Module API Serialization
├── final_exam/           # Examination System
│   ├── models.py         # Exam, Question, Answer Models
│   ├── views/            # Exam Management, Assessment
│   └── serializers.py    # Exam API Serialization
└── management/commands/  # Django Management Commands
```

#### `db_overview` - Datenbankanalyse-Tool

**Zweck**: Database Analysis & Management Tool

**Hauptfunktionen:**

- Django Schema Analysis
- Model Relationship Mapping
- Database Statistics
- Table Data Browser

#### `shift_planner` - Schichtplanung ⚠️

**Zweck**: Schichtplanung für Mitarbeiter (in Entwicklung)

**Status**: Models noch nicht vollständig implementiert

---

## 🔌 API-Struktur & Endpunkte

### 📋 API-Übersicht

#### Microsoft OAuth Integration (Core)

```
/api/microsoft/
├── auth/login/{tool_slug}/      # OAuth Initiation
├── auth/callback/               # OAuth Callback Handler
└── employee-info/               # Employee Information Retrieval
```

#### E-Learning System

```
/api/elearning/
├── token/refresh/               # JWT Token Management
├── users/                       # User CRUD Operations
│   ├── auth/login/             # Local Authentication
│   ├── auth/register/          # User Registration
│   └── admin/users/            # Admin User Management
├── modules/                     # Learning Content Management
│   ├── {id}/                   # Module Details
│   ├── {id}/tasks/             # Module Tasks
│   └── execute-python/         # Python Code Execution
└── exams/                       # Examination System
    ├── available/               # Available Exams
    ├── {id}/start/              # Start Exam Session
    └── {id}/submit/             # Submit Exam Answers
```

#### Employee Management (Core)

```
/api/employees/
├── departments/                 # Department Management
└── {employee_id}/               # Employee Details
```

#### Database Overview

```
/api/db-overview/
├── schema/                      # Database Schema Analysis
├── tables/                      # Table Information
└── statistics/                  # Database Statistics
```

### 🔐 Authentifizierung

#### JWT Token Flow

```python
# 1. Login über Microsoft OAuth
POST /api/microsoft/auth/login/e-learning

# 2. Token erhalten
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}

# 3. API-Calls mit Token
Authorization: Bearer <access_token>
```

---

## 📏 Code-Standards & Best Practices

### 🐍 Python/Django Standards

#### 1. Namenskonventionen

```python
# ✅ Korrekt
class EmployeeManager:
    def get_employee_by_id(self, employee_id):
        pass

# ❌ Falsch
class employeemanager:
    def GetEmployeeById(self, EmployeeId):
        pass
```

#### 2. Django Model Best Practices

```python
# ✅ Korrekt
class Employee(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['last_name', 'first_name']
        verbose_name = 'Mitarbeiter'
        verbose_name_plural = 'Mitarbeiter'

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
```

#### 3. View Best Practices

```python
# ✅ Class-Based Views
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

class EmployeeListAPIView(generics.ListCreateAPIView):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Employee.objects.filter(is_active=True)
```

```

---

## 📋 Projektaufgaben & Management

### 🎯 Aufgabenverwaltung

Alle konkreten Projektaufgaben, Features und Bugs werden über **Jira** verwaltet:

- **Jira Board**: [https://dsp-software.atlassian.net/jira/software/projects/CCS/boards/1?atlOrigin=eyJpIjoiZDk5ZWUyNmIyMTcxNDMxNWExODIyNzg1ZDM5ZTc2YzAiLCJwIjoiaiJ9]
- Hier finden Sie alle aktuellen Aufgaben, Sprints und Projektplanung
- Neue Features und Bugs werden hier erstellt und zugewiesen
- Entwickler arbeiten an den ihnen zugewiesenen Jira-Tickets

**Workflow:**

1. Jira-Ticket erstellen/zuweisen
2. Feature-Branch basierend auf Ticket-Nummer/Namen erstellen
3. Entwicklung und lokales Testen
4. Pull Request mit Ticket-Referenz
5. Review und Merge durch Lead

---

## 📞 Support & Kontakt

### 🆘 Hilfe bekommen

#### 2. Team-Kontakte

- **Lead**: [Lino De Marco] - [Email]

#### 3. Nützliche Links

- **GitHub Repository**: [https://github.com/LDM010795/DSP-Backend]
- **Jira Board**: [https://dsp-software.atlassian.net/jira/software/projects/CCS/boards/1?atlOrigin=eyJpIjoiZDk5ZWUyNmIyMTcxNDMxNWExODIyNzg1ZDM5ZTc2YzAiLCJwIjoiaiJ9]

---

## 📈 Nächste Schritte

### 🎯 Onboarding-Checkliste

- [ ] Repository geklont und auf develop Branch
- [ ] Entwicklungsumgebung eingerichtet
- [ ] Erste API-Calls getestet
- [ ] Git-Workflow verstanden
- [ ] Erste Feature entwickelt
- [ ] Pull Request erstellt

### 🚀 Weiterführende Ressourcen

1. **Django Documentation**: https://docs.djangoproject.com/
2. **Django REST Framework**: https://www.django-rest-framework.org/
3. **Microsoft Graph API**: https://docs.microsoft.com/en-us/graph/
4. **JWT Authentication**: https://django-rest-framework-simplejwt.readthedocs.io/

---

**Viel Erfolg beim Entwickeln! 🚀**

_Letzte Aktualisierung: 10.07.2025_
