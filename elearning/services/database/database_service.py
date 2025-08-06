"""
Database Service für DSP E-Learning Platform

Service für die Speicherung von extrahierten Bildern und Artikeln
in die Django Models. Verwaltet die Datenbankoperationen für:
- ArticleImage Model (Bilder)
- Article Model (Word-Dokumente)
- Module Model (Modul-Zuordnung)

Author: DSP Development Team
Version: 1.0.0
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

# Import der Models
from ...modules.models import Module, Article, ArticleImage, ModuleCategory

logger = logging.getLogger(__name__)


class DatabaseService:
    """
    Service für Datenbankoperationen.
    
    Verwaltet die Speicherung von extrahierten Bildern und Artikeln
    in die entsprechenden Django Models.
    """
    
    def __init__(self):
        self.logger = logger
    
    def get_or_create_module(self, module_name: str) -> Optional[Module]:
        """
        Holt oder erstellt ein Modul basierend auf dem Namen.
        
        Args:
            module_name: Name des Moduls (z.B. "SQL", "Python Grundlagen")
            
        Returns:
            Module Objekt oder None
        """
        try:
            # Versuche existierendes Modul zu finden
            module = Module.objects.get(title=module_name)
            self.logger.info(f"Existierendes Modul gefunden: {module_name}")
            return module
        except ObjectDoesNotExist:
            # Erstelle neues Modul
            try:
                # Standard-Kategorie verwenden oder erstellen
                default_category, created = ModuleCategory.objects.get_or_create(
                    name="Standard",
                    defaults={'name': "Standard"}
                )
                
                module = Module.objects.create(
                    title=module_name,
                    category=default_category,
                    is_public=True
                )
                
                self.logger.info(f"Neues Modul erstellt: {module_name}")
                return module
                
            except Exception as e:
                self.logger.error(f"Fehler beim Erstellen des Moduls {module_name}: {e}")
                return None
    
    def save_article_images(self, module: Module, images: List[Dict[str, Any]]) -> List[ArticleImage]:
        """
        Speichert Bilder für ein Modul in der Datenbank.
        
        Args:
            module: Das Modul, zu dem die Bilder gehören
            images: Liste der Bild-Daten
            
        Returns:
            Liste der erstellten ArticleImage Objekte
        """
        saved_images = []
        
        with transaction.atomic():
            for image_data in images:
                try:
                    # Prüfe ob Bild bereits existiert
                    existing_image = ArticleImage.objects.filter(
                        module=module,
                        image_name=image_data['name']
                    ).first()
                    
                    if existing_image:
                        # Aktualisiere existierendes Bild
                        existing_image.cloud_url = image_data['url']
                        existing_image.save()
                        saved_images.append(existing_image)
                        self.logger.info(f"Bild aktualisiert: {image_data['name']}")
                    else:
                        # Erstelle neues Bild
                        article_image = ArticleImage.objects.create(
                            module=module,
                            image_name=image_data['name'],
                            cloud_url=image_data['url']
                        )
                        saved_images.append(article_image)
                        self.logger.info(f"Neues Bild gespeichert: {image_data['name']}")
                        
                except Exception as e:
                    self.logger.error(f"Fehler beim Speichern des Bildes {image_data['name']}: {e}")
                    continue
        
        self.logger.info(f"{len(saved_images)} Bilder für Modul {module.title} gespeichert")
        return saved_images
    
    def save_processed_articles(self, module: Module, articles: List[Dict[str, Any]]) -> List[Article]:
        """
        Speichert verarbeitete Artikel in der Datenbank.
        
        Args:
            module: Das Modul, zu dem die Artikel gehören
            articles: Liste der verarbeiteten Artikel
            
        Returns:
            Liste der erstellten Article Objekte
        """
        saved_articles = []
        
        with transaction.atomic():
            for article_data in articles:
                try:
                    # Prüfe ob Artikel bereits existiert
                    existing_article = Article.objects.filter(
                        module=module,
                        title=article_data['title']
                    ).first()
                    
                    if existing_article:
                        # Aktualisiere existierenden Artikel
                        existing_article.url = article_data['url']
                        existing_article.json_content = article_data['json_content']
                        existing_article.save()
                        saved_articles.append(existing_article)
                        self.logger.info(f"Artikel aktualisiert: {article_data['title']}")
                    else:
                        # Erstelle neuen Artikel
                        article = Article.objects.create(
                            module=module,
                            title=article_data['title'],
                            url=article_data['url'],
                            json_content=article_data['json_content']
                        )
                        saved_articles.append(article)
                        self.logger.info(f"Neuer Artikel gespeichert: {article_data['title']}")
                        
                except Exception as e:
                    self.logger.error(f"Fehler beim Speichern des Artikels {article_data['title']}: {e}")
                    continue
        
        self.logger.info(f"{len(saved_articles)} Artikel für Modul {module.title} gespeichert")
        return saved_articles
    
    def process_module_content(self, module_name: str, images: List[Dict[str, Any]], 
                             articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Verarbeitet und speichert den gesamten Inhalt eines Moduls.
        
        Args:
            module_name: Name des Moduls
            images: Liste der Bild-Daten
            articles: Liste der Artikel-Daten
            
        Returns:
            Dictionary mit Verarbeitungs-Ergebnissen
        """
        try:
            # Modul holen oder erstellen
            module = self.get_or_create_module(module_name)
            if not module:
                return {
                    'success': False,
                    'error': f'Modul {module_name} konnte nicht erstellt werden'
                }
            
            # Bilder speichern
            saved_images = self.save_article_images(module, images)
            
            # Artikel speichern
            saved_articles = self.save_processed_articles(module, articles)
            
            result = {
                'success': True,
                'module': module,
                'saved_images_count': len(saved_images),
                'saved_articles_count': len(saved_articles),
                'saved_images': saved_images,
                'saved_articles': saved_articles
            }
            
            self.logger.info(f"Modul {module_name} erfolgreich verarbeitet: "
                           f"{len(saved_images)} Bilder, {len(saved_articles)} Artikel")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Fehler beim Verarbeiten des Moduls {module_name}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_module_statistics(self, module_name: str) -> Dict[str, Any]:
        """
        Holt Statistiken für ein Modul.
        
        Args:
            module_name: Name des Moduls
            
        Returns:
            Dictionary mit Modul-Statistiken
        """
        try:
            module = Module.objects.get(title=module_name)
            
            stats = {
                'module_name': module_name,
                'module_id': module.id,
                'is_public': module.is_public,
                'category': module.category.name if module.category else None,
                'images_count': module.article_images.count(),
                'articles_count': module.articles.count(),
                'content_count': module.contents.count(),
                'tasks_count': module.tasks.count(),
                'created_at': module.created_at,
                'updated_at': module.updated_at
            }
            
            return stats
            
        except ObjectDoesNotExist:
            return {
                'module_name': module_name,
                'error': 'Modul nicht gefunden'
            }
        except Exception as e:
            return {
                'module_name': module_name,
                'error': str(e)
            }
    
    def get_module_by_id(self, module_id: int) -> Optional[Module]:
        """
        Holt ein Modul anhand der ID.
        
        Args:
            module_id: ID des Moduls
            
        Returns:
            Module Objekt oder None
        """
        try:
            module = Module.objects.get(id=module_id)
            self.logger.info(f"Modul gefunden: {module.title} (ID: {module_id})")
            return module
        except ObjectDoesNotExist:
            self.logger.error(f"Modul mit ID {module_id} nicht gefunden")
            return None
        except Exception as e:
            self.logger.error(f"Fehler beim Abrufen des Moduls {module_id}: {e}")
            return None
    
    def cleanup_orphaned_images(self, module: Module) -> int:
        """
        Entfernt verwaiste Bilder (die nicht mehr im Cloud Storage existieren).
        
        Args:
            module: Das zu bereinigende Modul
            
        Returns:
            Anzahl der entfernten Bilder
        """
        # Diese Methode könnte später implementiert werden
        # um Bilder zu entfernen, die nicht mehr im Cloud Storage existieren
        return 0
    
    def validate_module_data(self, module_name: str, images: List[Dict], articles: List[Dict]) -> Dict[str, Any]:
        """
        Validiert die Daten vor der Speicherung.
        
        Args:
            module_name: Name des Moduls
            images: Liste der Bild-Daten
            articles: Liste der Artikel-Daten
            
        Returns:
            Dictionary mit Validierungs-Ergebnissen
        """
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Validiere Modul-Name
        if not module_name or len(module_name.strip()) == 0:
            validation_result['valid'] = False
            validation_result['errors'].append("Modul-Name ist leer")
        
        # Validiere Bilder
        for i, image in enumerate(images):
            if not image.get('name'):
                validation_result['errors'].append(f"Bild {i}: Name fehlt")
            if not image.get('url'):
                validation_result['errors'].append(f"Bild {i}: URL fehlt")
        
        # Validiere Artikel
        for i, article in enumerate(articles):
            if not article.get('title'):
                validation_result['errors'].append(f"Artikel {i}: Titel fehlt")
            if not article.get('url'):
                validation_result['errors'].append(f"Artikel {i}: URL fehlt")
            if not article.get('json_content'):
                validation_result['warnings'].append(f"Artikel {i}: JSON-Content fehlt")
        
        if validation_result['errors']:
            validation_result['valid'] = False
        
        return validation_result 