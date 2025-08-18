"""
Content Orchestration Service für DSP E-Learning Platform

Hauptservice, der alle anderen Services koordiniert:
- CloudStorageService: Verbindung zum Bucket
- WordProcessingService: Word-Dokumente verarbeiten
- DatabaseService: Daten in Models speichern

Pipeline:
1. Modul-Namen vom Frontend erhalten
2. Bilder aus Cloud Storage extrahieren
3. Word-Dokumente herunterladen und verarbeiten
4. Alle Daten in Datenbank speichern

Author: DSP Development Team
Version: 1.0.0
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

# Import der anderen Services
from ..cloud_storage import CloudStorageService, CloudFile
from ..word_processing import WordProcessingService, ProcessedArticle
from ..database import DatabaseService

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Repräsentiert das Ergebnis der Content-Verarbeitung."""
    success: bool
    module_name: str
    images_processed: int
    articles_processed: int
    images_saved: int
    articles_saved: int
    errors: List[str]
    warnings: List[str]


class ContentOrchestrationService:
    """
    Hauptservice für die Content-Verarbeitung.
    
    Koordiniert alle anderen Services und führt die komplette
    Pipeline für die automatische Extraktion und Speicherung aus.
    """
    
    def __init__(self):
        self.cloud_service = CloudStorageService()
        self.word_service = WordProcessingService()
        self.db_service = DatabaseService()
        self.logger = logger
    
    def process_module_content(self, module_name: str) -> ProcessingResult:
        """
        Verarbeitet den kompletten Inhalt eines Moduls.
        
        Args:
            module_name: Name des Moduls (z.B. "SQL", "Python Grundlagen")
            
        Returns:
            ProcessingResult mit Verarbeitungs-Ergebnissen
        """
        self.logger.info(f"Starte Verarbeitung für Modul: {module_name}")
        
        result = ProcessingResult(
            success=False,
            module_name=module_name,
            images_processed=0,
            articles_processed=0,
            images_saved=0,
            articles_saved=0,
            errors=[],
            warnings=[]
        )
        
        try:
            # 1. Cloud Storage Verbindung testen
            if not self.cloud_service.test_connection():
                result.errors.append("Cloud Storage Verbindung fehlgeschlagen")
                return result
            
            # 2. Modul-Inhalt aus Cloud Storage holen
            module_content = self.cloud_service.get_module_content(module_name)
            if not module_content:
                result.errors.append(f"Kein Inhalt für Modul {module_name} gefunden")
                return result
            
            # 3. Bilder verarbeiten
            images_data = self._process_images(module_content.images)
            result.images_processed = len(images_data)
            
            # 4. Word-Dokumente verarbeiten
            articles_data = self._process_articles(module_content.articles)
            result.articles_processed = len(articles_data)
            
            # 5. Daten validieren
            validation = self.db_service.validate_module_data(
                module_name, images_data, articles_data
            )
            
            if not validation['valid']:
                result.errors.extend(validation['errors'])
                return result
            
            if validation['warnings']:
                result.warnings.extend(validation['warnings'])
            
            # 6. Daten in Datenbank speichern
            db_result = self.db_service.process_module_content(
                module_name, images_data, articles_data
            )
            
            if db_result['success']:
                result.success = True
                result.images_saved = db_result['saved_images_count']
                result.articles_saved = db_result['saved_articles_count']
                self.logger.info(f"Modul {module_name} erfolgreich verarbeitet")
            else:
                result.errors.append(db_result.get('error', 'Unbekannter Datenbankfehler'))
            
        except Exception as e:
            error_msg = f"Unerwarteter Fehler bei der Verarbeitung von {module_name}: {str(e)}"
            result.errors.append(error_msg)
            self.logger.error(error_msg)
        
        return result
    
    def _process_images(self, images: List[CloudFile]) -> List[Dict[str, Any]]:
        """
        Verarbeitet Bilder für die Datenbank-Speicherung.
        
        Args:
            images: Liste der CloudFile Objekte
            
        Returns:
            Liste der Bild-Daten für die Datenbank
        """
        images_data = []
        
        for image in images:
            try:
                image_data = {
                    'name': image.name,
                    'url': image.url,
                    'size': image.size,
                    'content_type': image.content_type,
                    'last_modified': image.last_modified.isoformat()
                }
                images_data.append(image_data)
                
            except Exception as e:
                self.logger.error(f"Fehler beim Verarbeiten des Bildes {image.name}: {e}")
                continue
        
        self.logger.info(f"{len(images_data)} Bilder verarbeitet")
        return images_data
    
    def _process_articles(self, articles: List[CloudFile]) -> List[Dict[str, Any]]:
        """
        Verarbeitet Word-Dokumente für die Datenbank-Speicherung.
        
        Args:
            articles: Liste der CloudFile Objekte
            
        Returns:
            Liste der Artikel-Daten für die Datenbank
        """
        articles_data = []
        
        for article in articles:
            try:
                # Word-Dokument herunterladen
                file_content = self.cloud_service.download_file_content(article.path)
                if not file_content:
                    self.logger.error(f"Konnte Word-Dokument {article.name} nicht herunterladen")
                    continue
                
                # Word-Dokument verarbeiten
                processed_article = self.word_service.process_word_document(
                    file_content, article.name, article.url
                )
                
                if processed_article:
                    article_data = {
                        'title': processed_article.title,
                        'url': processed_article.url,
                        'json_content': processed_article.json_content,
                        'file_name': processed_article.file_name,
                        'word_content': processed_article.word_content
                    }
                    articles_data.append(article_data)
                else:
                    self.logger.error(f"Fehler beim Verarbeiten des Word-Dokuments {article.name}")
                    
            except Exception as e:
                self.logger.error(f"Fehler beim Verarbeiten des Artikels {article.name}: {e}")
                continue
        
        self.logger.info(f"{len(articles_data)} Artikel verarbeitet")
        return articles_data
    
    def get_available_modules(self) -> List[str]:
        """
        Holt alle verfügbaren Module aus dem Cloud Storage.
        
        Returns:
            Liste der verfügbaren Modul-Namen
        """
        return self.cloud_service.get_available_modules()
    
    def get_module_statistics(self, module_name: str) -> Dict[str, Any]:
        """
        Holt Statistiken für ein Modul.
        
        Args:
            module_name: Name des Moduls
            
        Returns:
            Dictionary mit Modul-Statistiken
        """
        return self.db_service.get_module_statistics(module_name)
    
    def test_all_services(self) -> Dict[str, bool]:
        """
        Testet alle Services auf Funktionalität.
        
        Returns:
            Dictionary mit Testergebnissen für jeden Service
        """
        results = {}
        
        # Cloud Storage Service testen
        try:
            results['cloud_storage'] = self.cloud_service.test_connection()
        except Exception as e:
            results['cloud_storage'] = False
            self.logger.error(f"Cloud Storage Service Test fehlgeschlagen: {e}")
        
        # Word Processing Service testen
        try:
            # Einfacher Test - versuche WordExtraction zu initialisieren
            test_extractor = self.word_service.word_extractor
            results['word_processing'] = test_extractor is not None
        except Exception as e:
            results['word_processing'] = False
            self.logger.error(f"Word Processing Service Test fehlgeschlagen: {e}")
        
        # Database Service testen
        try:
            # Einfacher Test - versuche eine Modul-Statistik abzurufen
            test_stats = self.db_service.get_module_statistics("Test")
            results['database'] = True  # Wenn keine Exception, dann funktioniert
        except Exception as e:
            results['database'] = False
            self.logger.error(f"Database Service Test fehlgeschlagen: {e}")
        
        return results
    
    def process_multiple_modules(self, module_names: List[str]) -> List[ProcessingResult]:
        """
        Verarbeitet mehrere Module gleichzeitig.
        
        Args:
            module_names: Liste der Modul-Namen
            
        Returns:
            Liste der ProcessingResult Objekte
        """
        results = []
        
        for module_name in module_names:
            self.logger.info(f"Verarbeite Modul: {module_name}")
            result = self.process_module_content(module_name)
            results.append(result)
            
            if result.success:
                self.logger.info(f"Modul {module_name} erfolgreich verarbeitet")
            else:
                self.logger.error(f"Modul {module_name} Verarbeitung fehlgeschlagen: {result.errors}")
        
        return results
    
    def cleanup_old_content(self, module_name: str) -> Dict[str, Any]:
        """
        Bereinigt alten Content für ein Modul.
        
        Args:
            module_name: Name des Moduls
            
        Returns:
            Dictionary mit Bereinigungs-Ergebnissen
        """
        try:
            # Hole aktuellen Cloud Storage Inhalt
            module_content = self.cloud_service.get_module_content(module_name)
            if not module_content:
                return {
                    'success': False,
                    'error': f'Kein Content für Modul {module_name} gefunden'
                }
            
            # Hole Modul aus Datenbank
            module = self.db_service.get_or_create_module(module_name)
            if not module:
                return {
                    'success': False,
                    'error': f'Modul {module_name} nicht in Datenbank gefunden'
                }
            
            # Bereinige verwaiste Bilder
            cleaned_images = self.db_service.cleanup_orphaned_images(module)
            
            return {
                'success': True,
                'module_name': module_name,
                'cleaned_images': cleaned_images,
                'current_images_count': len(module_content.images),
                'current_articles_count': len(module_content.articles)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            } 