"""
E-Learning Services Package für DSP (Digital Solutions Platform)

Dieses Paket enthält alle Services für die E-Learning-Plattform:
- Cloud Storage Services
- Word Processing Services
- Database Services
- Content Processing Services

Struktur:
├── cloud_storage/          # Cloud Storage Operationen
├── word_processing/        # Word-Dokument-Verarbeitung
├── database/              # Datenbank-Operationen
└── content_processing/    # Content-Verarbeitung

Author: DSP Development Team
Version: 1.0.0
"""

# Cloud Storage Services
from .cloud_storage import CloudStorageService, CloudFile, ModuleContent

# Word Processing Services
from .word_processing import WordProcessingService, ProcessedArticle, WordExtraction

# Database Services
from .database import DatabaseService

# Content Processing Services
from .content_processing import (
    ContentOrchestrationService,
    ProcessingResult,
    ArticleProcessingService,
    ProcessedArticleResult,
)

__all__ = [
    # Cloud Storage
    "CloudStorageService",
    "CloudFile",
    "ModuleContent",
    # Word Processing
    "WordProcessingService",
    "ProcessedArticle",
    "WordExtraction",
    # Database
    "DatabaseService",
    # Content Processing
    "ContentOrchestrationService",
    "ProcessingResult",
    "ArticleProcessingService",
    "ProcessedArticleResult",
]
