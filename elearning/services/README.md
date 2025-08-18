# E-Learning Services Package

Dieses Paket enthält alle Services für die DSP E-Learning-Plattform.

## 📁 Struktur

```
services/
├── __init__.py                    # Haupt-Paket-Initialisierung
├── cloud_storage/                 # Cloud Storage Services
│   ├── __init__.py
│   └── cloud_storage_service.py
├── word_processing/               # Word-Dokument-Verarbeitung
│   ├── __init__.py
│   ├── word_processing_service.py
│   └── word_extraction.py
├── database/                      # Datenbank-Operationen
│   ├── __init__.py
│   └── database_service.py
└── content_processing/            # Content-Verarbeitung
    ├── __init__.py
    ├── content_orchestration_service.py
    └── article_processing_service.py
```

## 🔧 Services-Übersicht

### Cloud Storage Services

- **CloudStorageService**: Verbindung zu Wasabi Cloud Storage
- **CloudFile**: Repräsentiert eine Datei im Cloud Storage
- **ModuleContent**: Repräsentiert den Inhalt eines Moduls

### Word Processing Services

- **WordProcessingService**: Verarbeitet Word-Dokumente
- **ProcessedArticle**: Repräsentiert ein verarbeitetes Word-Dokument
- **WordExtraction**: Extrahiert strukturierte Daten aus Word-Dokumenten

### Database Services

- **DatabaseService**: Verwaltet alle Datenbank-Operationen

### Content Processing Services

- **ContentOrchestrationService**: Koordiniert alle Services für Batch-Verarbeitung
- **ArticleProcessingService**: Verarbeitet einzelne Artikel aus Cloud-URLs
- **ProcessingResult**: Repräsentiert das Ergebnis der Content-Verarbeitung
- **ProcessedArticleResult**: Repräsentiert das Ergebnis der Artikel-Verarbeitung

## 🚀 Verwendung

```python
# Import aller Services
from elearning.services import (
    CloudStorageService,
    WordProcessingService,
    DatabaseService,
    ContentOrchestrationService,
    ArticleProcessingService
)

# Oder spezifische Imports
from elearning.services.cloud_storage import CloudStorageService
from elearning.services.content_processing import ArticleProcessingService
```

## 📋 Features

- **Modulare Architektur**: Jeder Service hat eine klare Verantwortlichkeit
- **Wiederverwendbarkeit**: Services können unabhängig verwendet werden
- **Erweiterbarkeit**: Neue Services können einfach hinzugefügt werden
- **Dokumentation**: Umfassende Docstrings und Kommentare

## 🔒 Sicherheit

- **Cloud Storage**: Sichere Verbindung zu Wasabi
- **Datenbank**: Transaktionale Operationen
- **Validierung**: Umfassende Eingabe-Validierung
- **Fehlerbehandlung**: Robuste Exception-Behandlung

## 📝 Author

DSP Development Team
Version: 1.0.0
