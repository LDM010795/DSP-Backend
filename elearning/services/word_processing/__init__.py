"""
Word Processing Services Package für DSP E-Learning Platform

Dieses Paket enthält alle Services für Word-Dokument-Verarbeitung:
- Word-Dokument-Extraktion
- JSON-Strukturierung
- Text-Verarbeitung
- WordExtraction-Integration

Author: DSP Development Team
Version: 1.0.0
"""

from .word_processing_service import WordProcessingService, ProcessedArticle
from .word_extraction import WordExtraction

__all__ = ["WordProcessingService", "ProcessedArticle", "WordExtraction"]
