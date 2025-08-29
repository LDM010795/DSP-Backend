"""
Article Processing Service für DSP E-Learning Platform

Service für die automatische Verarbeitung von Artikeln aus Cloud Storage URLs:
- Word-Dokument aus Cloud-URL herunterladen
- WordExtraction durchführen
- Bilder aus JSON extrahieren
- Bilder aus Cloud Storage holen
- Alles in Datenbank speichern

Author: DSP Development Team
Version: 1.0.0
"""

import logging
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
from dataclasses import dataclass

# Import der anderen Services
from ..cloud_storage import CloudStorageService
from ..word_processing import WordProcessingService
from ..database import DatabaseService

logger = logging.getLogger(__name__)


@dataclass
class ProcessedArticleResult:
    """Repräsentiert das Ergebnis der Artikel-Verarbeitung."""

    success: bool
    article_title: str
    article_id: Optional[int]
    images_found: List[str]
    images_saved: int
    errors: List[str]
    warnings: List[str]


class ArticleProcessingService:
    """
    Service für die automatische Artikel-Verarbeitung.

    Verarbeitet Word-Dokumente aus Cloud Storage URLs und
    extrahiert automatisch zugehörige Bilder.
    """

    def __init__(self):
        self.cloud_service = CloudStorageService()
        self.word_service = WordProcessingService()
        self.db_service = DatabaseService()
        self.logger = logger

    def process_article_from_cloud_url(
        self, module_id: int, cloud_url: str
    ) -> ProcessedArticleResult:
        """
        Verarbeitet einen Artikel aus einer Cloud-URL.

        Args:
            module_id: ID des Moduls
            cloud_url: Cloud-URL des Word-Dokuments

        Returns:
            ProcessedArticleResult mit Verarbeitungs-Ergebnissen
        """
        print(f"🔍 [DEBUG] Starte Verarbeitung für Cloud-URL: {cloud_url}")
        self.logger.info(f"Starte Verarbeitung für Cloud-URL: {cloud_url}")

        result = ProcessedArticleResult(
            success=False,
            article_title="",
            article_id=None,
            images_found=[],
            images_saved=0,
            errors=[],
            warnings=[],
        )

        try:
            # 1. Cloud-URL parsen und validieren
            print(f"🔍 [DEBUG] Parse Cloud-URL: {cloud_url}")
            parsed_url = self._parse_cloud_url(cloud_url)
            if not parsed_url:
                print("❌ [DEBUG] Cloud-URL konnte nicht geparst werden")
                result.errors.append("Ungültige Cloud-URL")
                return result

            print(f"✅ [DEBUG] URL geparst: {parsed_url}")

            # 2. Word-Dokument herunterladen
            print(f"🔍 [DEBUG] Lade Word-Dokument herunter: {parsed_url['object_key']}")
            file_content = self.cloud_service.download_file_content(
                parsed_url["object_key"]
            )
            if not file_content:
                print("❌ [DEBUG] Word-Dokument konnte nicht heruntergeladen werden")
                result.errors.append("Konnte Word-Dokument nicht herunterladen")
                return result

            print(
                f"✅ [DEBUG] Word-Dokument erfolgreich heruntergeladen ({len(file_content)} Bytes)"
            )

            # 3. Word-Dokument verarbeiten
            print("🔍 [DEBUG] Verarbeite Word-Dokument mit WordExtraction")
            processed_article = self.word_service.process_word_document(
                file_content, parsed_url["file_name"], cloud_url
            )

            if not processed_article:
                print("❌ [DEBUG] Word-Dokument-Verarbeitung fehlgeschlagen")
                result.errors.append("Fehler bei der Word-Dokument-Verarbeitung")
                return result

            print(f"✅ [DEBUG] Word-Dokument verarbeitet: {processed_article.title}")
            result.article_title = processed_article.title

            # 4. Bilder aus JSON extrahieren
            print("🔍 [DEBUG] Extrahiere Bilder aus JSON")
            images_from_json = self._extract_images_from_json(
                processed_article.json_content
            )
            result.images_found = images_from_json
            print(f"✅ [DEBUG] Gefundene Bilder: {images_from_json}")

            # 5. Modul aus Datenbank holen
            print(f"🔍 [DEBUG] Hole Modul aus Datenbank: {module_id}")
            module = self.db_service.get_module_by_id(module_id)
            if not module:
                print(f"❌ [DEBUG] Modul nicht gefunden: {module_id}")
                result.errors.append(f"Modul mit ID {module_id} nicht gefunden")
                return result

            print(f"✅ [DEBUG] Modul gefunden: {module.title}")

            # 6. Artikel in Datenbank speichern
            print("🔍 [DEBUG] Speichere Artikel in Datenbank")
            article_data = {
                "title": processed_article.title,
                "url": cloud_url,
                "json_content": processed_article.json_content,
            }

            saved_article = self.db_service.save_processed_articles(
                module, [article_data]
            )
            if saved_article:
                result.article_id = saved_article[0].id if saved_article else None
                print(f"✅ [DEBUG] Artikel gespeichert mit ID: {result.article_id}")

            # 7. Bilder aus Cloud Storage holen und speichern
            if images_from_json:
                print("🔍 [DEBUG] Verarbeite Bilder für Artikel")
                images_saved = self._process_images_for_article(
                    module, parsed_url["module_name"], images_from_json
                )
                result.images_saved = images_saved
                print(f"✅ [DEBUG] {images_saved} Bilder gespeichert")

            result.success = True
            print(
                f"🎉 [DEBUG] Artikel '{processed_article.title}' erfolgreich verarbeitet"
            )
            self.logger.info(
                f"Artikel '{processed_article.title}' erfolgreich verarbeitet"
            )

        except Exception as e:
            error_msg = f"Unerwarteter Fehler bei der Artikel-Verarbeitung: {str(e)}"
            print(f"❌ [DEBUG] Exception: {error_msg}")
            result.errors.append(error_msg)
            self.logger.error(error_msg)

        return result

    def _parse_cloud_url(self, cloud_url: str) -> Optional[Dict[str, str]]:
        """
        Parst eine Cloud-URL und extrahiert relevante Informationen.

        Args:
            cloud_url: Die zu parsende Cloud-URL

        Returns:
            Dictionary mit geparsten Informationen oder None
        """
        print(f"🔍 [DEBUG] Parse URL: {cloud_url}")
        try:
            # Beispiel-URL: https://s3.eu-central-2.wasabisys.com/dsp-e-learning/Lerninhalte/SQL/Artikel/1.1 Installation und erste Schritte.docx

            # URL parsen
            parsed = urlparse(cloud_url)
            path_parts = parsed.path.strip("/").split("/")

            print(f"🔍 [DEBUG] Path parts: {path_parts}")

            if len(path_parts) < 4:
                print(f"❌ [DEBUG] Zu wenige Path-Parts: {len(path_parts)}")
                return None

            # Bucket-Name (erster Teil)
            bucket_name = path_parts[0]

            # Modul-Name (dritter Teil)
            module_name = path_parts[2] if len(path_parts) > 2 else None

            # Dateiname (letzter Teil)
            file_name = path_parts[-1] if path_parts else None

            # Object Key für Cloud Storage (ohne Bucket-Name)
            # Entferne den Bucket-Namen aus dem Pfad
            object_key_parts = path_parts[1:]  # Ohne Bucket-Name
            object_key = "/".join(object_key_parts)

            result = {
                "bucket_name": bucket_name,
                "module_name": module_name,
                "file_name": file_name,
                "object_key": object_key,
            }

            print(f"✅ [DEBUG] URL geparst: {result}")
            return result

        except Exception as e:
            print(f"❌ [DEBUG] Fehler beim Parsen der Cloud-URL: {e}")
            self.logger.error(f"Fehler beim Parsen der Cloud-URL: {e}")
            return None

    def _extract_images_from_json(self, json_content: Dict[str, Any]) -> List[str]:
        """
        Extrahiert Bildnamen aus dem JSON-Content.

        Args:
            json_content: Der JSON-Content des Artikels

        Returns:
            Liste der Bildnamen
        """
        images = []

        try:
            content_list = json_content.get("content", [])

            for item in content_list:
                if item.get("type") == "image":
                    src = item.get("src", "")
                    if src:
                        # Entferne Dateiendung falls vorhanden
                        image_name = src.split(".")[0] if "." in src else src
                        images.append(image_name)

            self.logger.info(f"Gefundene Bilder im JSON: {images}")
            return images

        except Exception as e:
            self.logger.error(f"Fehler beim Extrahieren der Bilder aus JSON: {e}")
            return []

    def _process_images_for_article(
        self, module, module_name: str, image_names: List[str]
    ) -> int:
        """
        Verarbeitet Bilder für einen Artikel.

        Args:
            module: Das Modul-Objekt
            module_name: Name des Moduls
            image_names: Liste der Bildnamen

        Returns:
            Anzahl der gespeicherten Bilder
        """
        try:
            # Hole alle Bilder aus dem Modul-Ordner
            module_content = self.cloud_service.get_module_content(module_name)
            if not module_content:
                self.logger.warning(f"Kein Modul-Inhalt für {module_name} gefunden")
                return 0

            # Filtere Bilder basierend auf den Namen aus dem JSON
            matching_images = []
            for image in module_content.images:
                image_name_without_ext = (
                    image.name.split(".")[0] if "." in image.name else image.name
                )

                if image_name_without_ext in image_names:
                    matching_images.append({"name": image.name, "url": image.url})

            # Speichere die gefundenen Bilder
            if matching_images:
                saved_images = self.db_service.save_article_images(
                    module, matching_images
                )
                self.logger.info(f"{len(saved_images)} Bilder für Artikel gespeichert")
                return len(saved_images)

            return 0

        except Exception as e:
            self.logger.error(f"Fehler beim Verarbeiten der Bilder: {e}")
            return 0

    def validate_cloud_url(self, cloud_url: str) -> Dict[str, Any]:
        """
        Validiert eine Cloud-URL.

        Args:
            cloud_url: Die zu validierende URL

        Returns:
            Dictionary mit Validierungs-Ergebnissen
        """
        validation_result = {"valid": False, "errors": [], "parsed_info": None}

        try:
            # Prüfe URL-Format
            if not cloud_url.startswith("https://"):
                validation_result["errors"].append("URL muss mit https:// beginnen")
                return validation_result

            # Parse URL
            parsed_info = self._parse_cloud_url(cloud_url)
            if not parsed_info:
                validation_result["errors"].append("URL konnte nicht geparst werden")
                return validation_result

            # Prüfe Dateiendung
            if not parsed_info["file_name"].lower().endswith(".docx"):
                validation_result["errors"].append(
                    "URL muss auf eine .docx Datei zeigen"
                )
                return validation_result

            validation_result["valid"] = True
            validation_result["parsed_info"] = parsed_info

        except Exception as e:
            validation_result["errors"].append(f"Validierungsfehler: {str(e)}")

        return validation_result
