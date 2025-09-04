"""
Cloud Storage Service für DSP E-Learning Platform

Service für die Verbindung zum dsp-e-learning Bucket und die Navigation
durch die Ordnerstruktur: Lerninhalte -> Modul-Name -> Bilder/Artikel

Features:
- Verbindung zum dsp-e-learning Bucket
- Navigation durch Ordnerstruktur
- Bild-Extraktion aus Modul-Ordnern
- Word-Dokument-Extraktion aus Artikel-Ordnern
- Automatische URL-Generierung

Author: DSP Development Team
Version: 1.0.0
"""

import os
import logging
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime

# Cloud Storage Imports (AWS S3 oder ähnlich)
try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError

    CLOUD_STORAGE_AVAILABLE = True
except ImportError:
    CLOUD_STORAGE_AVAILABLE = False
    logging.warning("boto3 nicht verfügbar - Cloud Storage Service deaktiviert")

logger = logging.getLogger(__name__)


@dataclass
class CloudFile:
    """Repräsentiert eine Datei im Cloud Storage."""

    name: str
    path: str
    size: int
    last_modified: datetime
    url: str
    content_type: str


@dataclass
class ModuleContent:
    """Repräsentiert den Inhalt eines Moduls."""

    module_name: str
    images: List[CloudFile]
    articles: List[CloudFile]
    videos: List[CloudFile]


class CloudStorageService:
    """
    Service für Cloud Storage Operationen.

    Verwaltet die Verbindung zum dsp-e-learning Bucket und
    extrahiert Bilder und Artikel aus der Ordnerstruktur.
    """

    def __init__(self):
        self.bucket_name = "dsp-e-learning"
        self.base_path = "Lerninhalte"
        self.images_folder = "Bilder"
        self.articles_folder = "Artikel"
        self.videos_folder = "Videos"

        # Cloud Storage Client initialisieren
        self.client = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialisiert den Cloud Storage Client."""
        if not CLOUD_STORAGE_AVAILABLE:
            logger.error("Cloud Storage nicht verfügbar - boto3 fehlt")
            return

        try:
            # Wasabi S3 Client initialisieren
            self.client = boto3.client(
                "s3",
                aws_access_key_id=os.getenv("WASABI_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("WASABI_SECRET_ACCESS_KEY"),
                region_name=os.getenv("WASABI_REGION", "eu-central-2"),
                endpoint_url=os.getenv(
                    "WASABI_ENDPOINT_URL", "https://s3.eu-central-2.wasabisys.com"
                ),
            )
            logger.info("Wasabi Cloud Storage Client initialisiert")
        except NoCredentialsError:
            logger.error("Wasabi Credentials nicht gefunden")
        except Exception as e:
            logger.error(
                f"Fehler beim Initialisieren des Wasabi Cloud Storage Clients: {e}"
            )

    def get_available_modules(self) -> List[str]:
        """
        Holt alle verfügbaren Module aus dem Cloud Storage.

        Returns:
            Liste der Modul-Namen
        """
        if not self.client:
            logger.error("Cloud Storage Client nicht verfügbar")
            return []

        try:
            # Liste alle Ordner unter Lerninhalte/
            response = self.client.list_objects_v2(
                Bucket=self.bucket_name, Prefix=f"{self.base_path}/", Delimiter="/"
            )

            modules = []
            if "CommonPrefixes" in response:
                for prefix in response["CommonPrefixes"]:
                    # Extrahiere Modul-Namen aus Pfad
                    module_path = prefix["Prefix"]
                    module_name = module_path.replace(f"{self.base_path}/", "").rstrip(
                        "/"
                    )
                    if module_name:
                        modules.append(module_name)

            logger.info(f"Gefundene Module: {modules}")
            return modules

        except ClientError as e:
            logger.error(f"Fehler beim Abrufen der Module: {e}")
            return []

    def get_module_content(self, module_name: str) -> Optional[ModuleContent]:
        """
        Holt alle Bilder, Artikel und Videos für ein spezifisches Modul.

        Args:
            module_name: Name des Moduls (z.B. "SQL", "Python Grundlagen")

        Returns:
            ModuleContent mit Bildern, Artikeln und Videos oder None
        """
        if not self.client:
            logger.error("Cloud Storage Client nicht verfügbar")
            return None

        try:
            # Bilder aus Modul/Bilder/ Ordner holen
            images = self._get_images_for_module(module_name)

            # Artikel aus Modul/Artikel/ Ordner holen
            articles = self._get_articles_for_module(module_name)

            # Videos aus Modul/Videos/ Ordner holen
            videos = self._get_videos_for_module(module_name)

            content = ModuleContent(
                module_name=module_name, images=images, articles=articles, videos=videos
            )

            logger.info(
                f"Modul {module_name}: {len(images)} Bilder, {len(articles)} Artikel, {len(videos)} Videos gefunden"
            )
            return content

        except ClientError as e:
            logger.error(
                f"Fehler beim Abrufen des Modul-Inhalts für {module_name}: {e}"
            )
            return None

    def _get_images_for_module(self, module_name: str) -> List[CloudFile]:
        """
        Holt alle Bilder für ein spezifisches Modul.

        Args:
            module_name: Name des Moduls

        Returns:
            Liste der CloudFile Objekte für Bilder
        """
        try:
            # Pfad zum Bilder-Ordner des Moduls
            images_prefix = f"{self.base_path}/{module_name}/{self.images_folder}/"

            response = self.client.list_objects_v2(
                Bucket=self.bucket_name, Prefix=images_prefix
            )

            images = []
            if "Contents" in response:
                for obj in response["Contents"]:
                    # Überspringe Ordner selbst
                    if obj["Key"].endswith("/"):
                        continue

                    # Extrahiere Dateiname
                    file_name = os.path.basename(obj["Key"])

                    # Generiere Cloud-URL
                    cloud_url = self._generate_cloud_url(obj["Key"])

                    cloud_file = CloudFile(
                        name=file_name,
                        path=obj["Key"],
                        size=obj["Size"],
                        last_modified=obj["LastModified"],
                        url=cloud_url,
                        content_type=obj.get("ContentType", "image/png"),
                    )
                    images.append(cloud_file)

            logger.info(
                f"Gefundene Bilder für {module_name}: {[img.name for img in images]}"
            )
            return images

        except ClientError as e:
            logger.error(f"Fehler beim Abrufen der Bilder für {module_name}: {e}")
            return []

    def _get_articles_for_module(self, module_name: str) -> List[CloudFile]:
        """
        Holt alle Word-Dokumente für ein spezifisches Modul.

        Args:
            module_name: Name des Moduls

        Returns:
            Liste der CloudFile Objekte für Word-Dokumente
        """
        try:
            # Pfad zum Artikel-Ordner des Moduls
            articles_prefix = f"{self.base_path}/{module_name}/{self.articles_folder}/"

            response = self.client.list_objects_v2(
                Bucket=self.bucket_name, Prefix=articles_prefix
            )

            articles = []
            if "Contents" in response:
                for obj in response["Contents"]:
                    # Überspringe Ordner selbst
                    if obj["Key"].endswith("/"):
                        continue

                    # Nur Word-Dokumente (.docx)
                    file_name = os.path.basename(obj["Key"])
                    if not file_name.lower().endswith(".docx"):
                        continue

                    # Generiere Cloud-URL
                    cloud_url = self._generate_cloud_url(obj["Key"])

                    cloud_file = CloudFile(
                        name=file_name,
                        path=obj["Key"],
                        size=obj["Size"],
                        last_modified=obj["LastModified"],
                        url=cloud_url,
                        content_type=obj.get(
                            "ContentType",
                            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        ),
                    )
                    articles.append(cloud_file)

            logger.info(
                f"Gefundene Artikel für {module_name}: {[art.name for art in articles]}"
            )
            return articles

        except ClientError as e:
            logger.error(f"Fehler beim Abrufen der Artikel für {module_name}: {e}")
            return []

    def _get_videos_for_module(self, module_name: str) -> List[CloudFile]:
        """
        Holt alle Videos für ein spezifisches Modul.

        Args:
            module_name: Name des Moduls

        Returns:
            Liste der CloudFile Objekte für Videos
        """
        try:
            # Pfad zum Videos-Ordner des Moduls
            videos_prefix = f"{self.base_path}/{module_name}/{self.videos_folder}/"

            response = self.client.list_objects_v2(
                Bucket=self.bucket_name, Prefix=videos_prefix
            )

            videos = []
            if "Contents" in response:
                for obj in response["Contents"]:
                    # Überspringe Ordner selbst
                    if obj["Key"].endswith("/"):
                        continue

                    # Nur Video-Dateien (.mp4, .avi, .mov, .mkv, etc.)
                    file_name = os.path.basename(obj["Key"])
                    video_extensions = [
                        ".mp4",
                        ".avi",
                        ".mov",
                        ".mkv",
                        ".wmv",
                        ".flv",
                        ".webm",
                    ]
                    if not any(
                        file_name.lower().endswith(ext) for ext in video_extensions
                    ):
                        continue

                    # Generiere Cloud-URL
                    cloud_url = self._generate_cloud_url(obj["Key"])

                    cloud_file = CloudFile(
                        name=file_name,
                        path=obj["Key"],
                        size=obj["Size"],
                        last_modified=obj["LastModified"],
                        url=cloud_url,
                        content_type=obj.get("ContentType", "video/mp4"),
                    )
                    videos.append(cloud_file)

            logger.info(
                f"Gefundene Videos für {module_name}: {[vid.name for vid in videos]}"
            )
            return videos

        except ClientError as e:
            logger.error(f"Fehler beim Abrufen der Videos für {module_name}: {e}")
            return []

    def _generate_cloud_url(self, object_key: str) -> str:
        """
        Generiert eine Cloud-URL für ein Objekt.

        Args:
            object_key: Der Objekt-Schlüssel im Bucket

        Returns:
            Vollständige Cloud-URL
        """
        # Wasabi URL-Generierung
        endpoint_url = os.getenv(
            "WASABI_ENDPOINT_URL", "https://s3.eu-central-2.wasabisys.com"
        )
        # Entferne das 's3.' aus dem Endpoint für die öffentliche URL
        public_endpoint = endpoint_url.replace("s3.", "")
        return f"{public_endpoint}/{self.bucket_name}/{object_key}"

    def download_file_content(self, object_key: str) -> Optional[bytes]:
        """
        Lädt den Inhalt einer Datei herunter.

        Args:
            object_key: Der Objekt-Schlüssel im Bucket

        Returns:
            Dateiinhalt als Bytes oder None
        """
        print(f"🔍 [DEBUG] Cloud Storage: Lade Datei herunter: {object_key}")
        if not self.client:
            print("❌ [DEBUG] Cloud Storage Client nicht verfügbar")
            logger.error("Cloud Storage Client nicht verfügbar")
            return None

        try:
            print(
                f"🔍 [DEBUG] Cloud Storage: Versuche GetObject für Bucket: {self.bucket_name}, Key: {object_key}"
            )
            response = self.client.get_object(Bucket=self.bucket_name, Key=object_key)

            content = response["Body"].read()
            print(
                f"✅ [DEBUG] Cloud Storage: Datei erfolgreich heruntergeladen ({len(content)} Bytes)"
            )
            logger.info(
                f"Datei {object_key} erfolgreich heruntergeladen ({len(content)} Bytes)"
            )
            return content

        except ClientError as e:
            print(f"❌ [DEBUG] Cloud Storage ClientError: {e}")
            logger.error(f"Fehler beim Herunterladen von {object_key}: {e}")
            return None
        except Exception as e:
            print(f"❌ [DEBUG] Cloud Storage Exception: {e}")
            logger.error(
                f"Unerwarteter Fehler beim Herunterladen von {object_key}: {e}"
            )
            return None

    def test_connection(self) -> bool:
        """
        Testet die Verbindung zum Cloud Storage.

        Returns:
            True wenn Verbindung erfolgreich, False sonst
        """
        if not self.client:
            logger.error("Cloud Storage Client nicht verfügbar")
            return False

        try:
            # Teste Bucket-Zugriff
            self.client.head_bucket(Bucket=self.bucket_name)
            logger.info("Cloud Storage Verbindung erfolgreich")
            return True
        except ClientError as e:
            logger.error(f"Cloud Storage Verbindung fehlgeschlagen: {e}")
            return False
