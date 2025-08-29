"""Setup Wasabi CORS Management Command"""

import boto3
import json
import logging
from django.core.management.base import BaseCommand
import os

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Konfiguriert CORS für Wasabi Bucket für Progressive Video-Streaming"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Zeige nur was konfiguriert werden würde, ohne tatsächlich zu ändern",
        )
        parser.add_argument(
            "--verify",
            action="store_true",
            help="Verifiziere die aktuelle CORS-Konfiguration",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        verify = options["verify"]

        if verify:
            self.verify_cors_configuration()
            return

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN: CORS-Konfiguration wird nur simuliert")
            )

        success = self.configure_cors(dry_run)

        if success:
            self.stdout.write(self.style.SUCCESS("CORS-Konfiguration erfolgreich"))
        else:
            self.stdout.write(self.style.ERROR("CORS-Konfiguration fehlgeschlagen"))

    def configure_cors(self, dry_run=False):
        wasabi_access_key = os.getenv("WASABI_ACCESS_KEY_ID")
        wasabi_secret_key = os.getenv("WASABI_SECRET_ACCESS_KEY")
        bucket_name = "dsp-e-learning"

        if not wasabi_access_key or not wasabi_secret_key:
            self.stdout.write(
                self.style.ERROR(
                    "WASABI_ACCESS_KEY_ID und WASABI_SECRET_ACCESS_KEY müssen in .env gesetzt sein"
                )
            )
            return False

        try:
            s3_client = boto3.client(
                "s3",
                endpoint_url="https://s3.eu-central-2.wasabisys.com",
                aws_access_key_id=wasabi_access_key,
                aws_secret_access_key=wasabi_secret_key,
                region_name="eu-central-2",
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Fehler beim Initialisieren des S3 Clients: {e}")
            )
            return False

        cors_config = {
            "CORSRules": [
                {
                    "AllowedOrigins": [
                        "http://localhost:3000",
                        "http://localhost:5173",
                        "http://localhost:5174",
                        "http://127.0.0.1:3000",
                        "http://127.0.0.1:5173",
                        "http://127.0.0.1:5174",
                        "https://dsp-e-learning.onrender.com",
                        "https://dsp-db-overview.onrender.com",
                        "https://dsp-shift-planner.onrender.com",
                        "*",
                    ],
                    "AllowedMethods": ["GET", "HEAD"],
                    "AllowedHeaders": ["*"],
                    "ExposeHeaders": [
                        "Accept-Ranges",
                        "Content-Range",
                        "Content-Length",
                        "Content-Type",
                        "ETag",
                        "Last-Modified",
                    ],
                    "MaxAgeSeconds": 3000,
                }
            ]
        }

        if dry_run:
            self.stdout.write("CORS-Konfiguration die angewendet werden würde:")
            self.stdout.write(json.dumps(cors_config, indent=2))
            return True

        try:
            s3_client.put_bucket_cors(Bucket=bucket_name, CORSConfiguration=cors_config)

            self.stdout.write(
                self.style.SUCCESS(
                    f"CORS-Konfiguration für Bucket '{bucket_name}' erfolgreich angewendet"
                )
            )
            self.stdout.write("Erlaubte Origins:")
            for origin in cors_config["CORSRules"][0]["AllowedOrigins"]:
                self.stdout.write(f"   - {origin}")
            return True

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Fehler bei CORS-Konfiguration: {e}"))
            return False

    def verify_cors_configuration(self):
        wasabi_access_key = os.getenv("WASABI_ACCESS_KEY_ID")
        wasabi_secret_key = os.getenv("WASABI_SECRET_ACCESS_KEY")
        bucket_name = "dsp-e-learning"

        if not wasabi_access_key or not wasabi_secret_key:
            self.stdout.write(self.style.ERROR("Credentials nicht gesetzt"))
            return

        try:
            s3_client = boto3.client(
                "s3",
                endpoint_url="https://s3.eu-central-2.wasabisys.com",
                aws_access_key_id=wasabi_access_key,
                aws_secret_access_key=wasabi_secret_key,
                region_name="eu-central-2",
            )

            cors_config = s3_client.get_bucket_cors(Bucket=bucket_name)
            self.stdout.write(self.style.SUCCESS("CORS-Konfiguration gefunden:"))
            self.stdout.write(json.dumps(cors_config, indent=2))

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Keine CORS-Konfiguration gefunden: {e}")
            )
