import boto3
from botocore.config import Config
import os
import urllib.parse

class WasabiService:
    def __init__(self):
        self.bucket = "dsp-e-learning"
        self.region = os.getenv("WASABI_REGION")
        self.endpoint_url = os.getenv("WASABI_ENDPOINT_URL")
        self.access_key = os.getenv("WASABI_ACCESS_KEY_ID")
        self.secret_key = os.getenv("WASABI_SECRET_ACCESS_KEY")
        
        print(f"🔧 DEBUG: WasabiService Initialisierung:")
        print(f"  - Bucket: {self.bucket}")
        print(f"  - Region: {self.region}")
        print(f"  - Endpoint: {self.endpoint_url}")
        print(f"  - Access Key: {self.access_key[:10] if self.access_key else 'None'}...")
        print(f"  - Secret Key: {'***' if self.secret_key else 'None'}")
        
    def get_s3_client(self):
        """Erstellt einen boto3 S3-Client für Wasabi"""
        return boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            region_name=self.region,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            config=Config(s3={"addressing_style": "virtual"})
        )
    
    def _normalize_key(self, key: str) -> str:
        """Normalisiert eingehende Keys robust für Virtual-Host-Style.

        - URL-Decoding (z.B. %20 → Leerzeichen)
        - führende Slashes entfernen
        - optionales Bucket-Präfix im Pfad entfernen ("<bucket>/...")
        """
        if not key:
            return key
        # URL decode
        decoded = urllib.parse.unquote(key)
        # trim leading slashes
        trimmed = decoded.lstrip('/')
        # remove duplicate bucket prefix in path
        bucket_prefix = f"{self.bucket}/"
        if trimmed.startswith(bucket_prefix):
            trimmed = trimmed[len(bucket_prefix):]
        return trimmed
    
    def generate_presigned_url(self, key: str, expires_seconds: int = 7200) -> str:
        """
        Generiert eine presigned URL für ein Video
        
        Args:
            key: Der S3-Key (z.B. "Lerninhalte/SQL/Videos/Einführung.mp4")
            expires_seconds: Gültigkeitsdauer in Sekunden (Standard: 2 Stunden)
        
        Returns:
            Presigned URL für direkten Zugriff
        """
        print(f"🔧 DEBUG: generate_presigned_url aufgerufen mit:")
        print(f"  - Key: {key}")
        print(f"  - Expires: {expires_seconds} Sekunden")
        
        try:
            print(f"🔧 DEBUG: Erstelle S3 Client...")
            client = self.get_s3_client()
            print(f"🔧 DEBUG: S3 Client erstellt erfolgreich")
            
            print(f"🔧 DEBUG: Generiere presigned URL...")
            normalized_key = self._normalize_key(key)
            print(f"🔧 DEBUG: Normalized Key: {normalized_key}")
            url = client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": self.bucket, "Key": normalized_key},
                ExpiresIn=expires_seconds
            )
            print(f"🔧 DEBUG: Presigned URL erfolgreich generiert: {url[:50]}...")
            return url
        except Exception as e:
            print(f"🔧 DEBUG: Fehler beim Generieren der presigned URL: {e}")
            print(f"🔧 DEBUG: Exception Type: {type(e)}")
            import traceback
            print(f"🔧 DEBUG: Traceback: {traceback.format_exc()}")
            return None
