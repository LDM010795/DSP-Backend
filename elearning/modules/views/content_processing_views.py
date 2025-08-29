"""
Content Processing Views für DSP E-Learning Platform

API-Endpoints für die automatische Content-Verarbeitung:
- POST /api/content/process-module/ - Verarbeitet ein Modul
- GET /api/content/available-modules/ - Holt verfügbare Module
- GET /api/content/module-statistics/ - Holt Modul-Statistiken
- POST /api/content/test-services/ - Testet alle Services

Author: DSP Development Team
Version: 1.0.0
"""

import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

# Import des Orchestration Services
from ...services.content_processing import ContentOrchestrationService
from ...services.cloud_storage import CloudStorageService
import os

logger = logging.getLogger(__name__)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def process_module_content(request):
    """
    Verarbeitet den Inhalt eines Moduls.

    POST /api/content/process-module/

    Request Body:
    {
        "module_name": "SQL"  // Name des Moduls
    }

    Response:
    {
        "success": true,
        "module_name": "SQL",
        "images_processed": 5,
        "articles_processed": 2,
        "images_saved": 5,
        "articles_saved": 2,
        "errors": [],
        "warnings": []
    }
    """
    try:
        # Request-Daten validieren
        module_name = request.data.get("module_name")
        if not module_name:
            return Response(
                {"success": False, "error": "module_name ist erforderlich"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Orchestration Service initialisieren
        orchestration_service = ContentOrchestrationService()

        # Modul verarbeiten
        result = orchestration_service.process_module_content(module_name)

        # Response erstellen
        response_data = {
            "success": result.success,
            "module_name": result.module_name,
            "images_processed": result.images_processed,
            "articles_processed": result.articles_processed,
            "images_saved": result.images_saved,
            "articles_saved": result.articles_saved,
            "errors": result.errors,
            "warnings": result.warnings,
        }

        if result.success:
            logger.info(f"Modul {module_name} erfolgreich verarbeitet")
            return Response(response_data, status=status.HTTP_200_OK)
        else:
            logger.error(
                f"Fehler bei der Verarbeitung von Modul {module_name}: {result.errors}"
            )
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.error(f"Unerwarteter Fehler in process_module_content: {e}")
        return Response(
            {"success": False, "error": f"Interner Serverfehler: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def validate_video_url(request):
    """
    Validiert eine Video-URL aus der Cloud und extrahiert den Dateinamen.

    POST /api/content/validate-video-url/

    Request Body:
    {
        "video_url": "https://s3.eu-central-2.wasabisys.com/dsp-e-learning/Lerninhalte/SQL/Videos/1.1 Einführung.mp4"
    }

    Response:
    {
        "success": true,
        "video_url": "https://s3.eu-central-2.wasabisys.com/dsp-e-learning/Lerninhalte/SQL/Videos/1.1 Einführung.mp4",
        "filename": "1.1 Einführung.mp4",
        "title": "1.1 Einführung",
        "is_valid": true
    }
    """
    try:
        video_url = request.data.get("video_url")
        if not video_url:
            return Response(
                {"success": False, "error": "video_url ist erforderlich"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Cloud Storage Service initialisieren
        cloud_service = CloudStorageService()

        # URL validieren (muss Wasabi Cloud URL sein)
        if not video_url.startswith(
            "https://s3.eu-central-2.wasabisys.com/dsp-e-learning/"
        ):
            return Response(
                {
                    "success": False,
                    "error": "Ungültige Cloud-URL. Muss eine Wasabi Cloud URL sein.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Dateiname aus URL extrahieren
        filename = video_url.split("/")[-1]

        # Prüfen ob es eine Video-Datei ist
        video_extensions = [".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm"]
        if not any(filename.lower().endswith(ext) for ext in video_extensions):
            return Response(
                {
                    "success": False,
                    "error": "Keine gültige Video-Datei. Unterstützte Formate: mp4, avi, mov, mkv, wmv, flv, webm",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Titel aus Dateiname extrahieren (ohne Extension)
        title = os.path.splitext(filename)[0]

        # Prüfen ob die Datei tatsächlich existiert
        try:
            # Object key aus URL extrahieren
            object_key = video_url.replace(
                "https://s3.eu-central-2.wasabisys.com/dsp-e-learning/", ""
            )

            # Prüfen ob Datei existiert
            cloud_service.client.head_object(
                Bucket=cloud_service.bucket_name, Key=object_key
            )
        except Exception as e:
            return Response(
                {"success": False, "error": f"Video-Datei nicht gefunden: {str(e)}"},
                status=status.HTTP_404_NOT_FOUND,
            )

        response_data = {
            "success": True,
            "video_url": video_url,
            "filename": filename,
            "title": title,
            "is_valid": True,
        }

        logger.info(f"Video-URL validiert: {filename}")
        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Fehler bei der Video-URL-Validierung: {e}")
        return Response(
            {"success": False, "error": f"Fehler bei der Validierung: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_available_modules(request):
    """
    Holt alle verfügbaren Module aus dem Cloud Storage.

    GET /api/content/available-modules/

    Response:
    {
        "success": true,
        "modules": ["SQL", "Python Grundlagen", "JavaScript"]
    }
    """
    try:
        orchestration_service = ContentOrchestrationService()
        modules = orchestration_service.get_available_modules()

        return Response(
            {"success": True, "modules": modules}, status=status.HTTP_200_OK
        )

    except Exception as e:
        logger.error(f"Fehler beim Abrufen der verfügbaren Module: {e}")
        return Response(
            {"success": False, "error": f"Fehler beim Abrufen der Module: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_module_statistics(request):
    """
    Holt Statistiken für ein spezifisches Modul.

    GET /api/content/module-statistics/?module_name=SQL

    Response:
    {
        "success": true,
        "module_name": "SQL",
        "module_id": 1,
        "is_public": true,
        "category": "Standard",
        "images_count": 5,
        "articles_count": 2,
        "content_count": 0,
        "tasks_count": 0
    }
    """
    try:
        module_name = request.GET.get("module_name")
        if not module_name:
            return Response(
                {"success": False, "error": "module_name Parameter ist erforderlich"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        orchestration_service = ContentOrchestrationService()
        stats = orchestration_service.get_module_statistics(module_name)

        if "error" in stats:
            return Response(
                {"success": False, "error": stats["error"]},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response({"success": True, **stats}, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Fehler beim Abrufen der Modul-Statistiken: {e}")
        return Response(
            {
                "success": False,
                "error": f"Fehler beim Abrufen der Statistiken: {str(e)}",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAdminUser])
def test_all_services(request):
    """
    Testet alle Services auf Funktionalität.

    POST /api/content/test-services/

    Response:
    {
        "success": true,
        "cloud_storage": true,
        "word_processing": true,
        "database": true
    }
    """
    try:
        orchestration_service = ContentOrchestrationService()
        test_results = orchestration_service.test_all_services()

        all_working = all(test_results.values())

        return Response(
            {"success": all_working, **test_results}, status=status.HTTP_200_OK
        )

    except Exception as e:
        logger.error(f"Fehler beim Testen der Services: {e}")
        return Response(
            {"success": False, "error": f"Fehler beim Testen der Services: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def process_multiple_modules(request):
    """
    Verarbeitet mehrere Module gleichzeitig.

    POST /api/content/process-multiple-modules/

    Request Body:
    {
        "module_names": ["SQL", "Python Grundlagen"]
    }

    Response:
    {
        "success": true,
        "results": [
            {
                "success": true,
                "module_name": "SQL",
                "images_processed": 5,
                "articles_processed": 2,
                "images_saved": 5,
                "articles_saved": 2,
                "errors": [],
                "warnings": []
            }
        ]
    }
    """
    try:
        module_names = request.data.get("module_names", [])
        if not module_names:
            return Response(
                {"success": False, "error": "module_names Array ist erforderlich"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        orchestration_service = ContentOrchestrationService()
        results = orchestration_service.process_multiple_modules(module_names)

        # Ergebnisse in Response-Format konvertieren
        response_results = []
        for result in results:
            response_results.append(
                {
                    "success": result.success,
                    "module_name": result.module_name,
                    "images_processed": result.images_processed,
                    "articles_processed": result.articles_processed,
                    "images_saved": result.images_saved,
                    "articles_saved": result.articles_saved,
                    "errors": result.errors,
                    "warnings": result.warnings,
                }
            )

        all_successful = all(r["success"] for r in response_results)

        return Response(
            {"success": all_successful, "results": response_results},
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        logger.error(f"Fehler bei der Verarbeitung mehrerer Module: {e}")
        return Response(
            {"success": False, "error": f"Fehler bei der Verarbeitung: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAdminUser])
def cleanup_module_content(request):
    """
    Bereinigt alten Content für ein Modul.

    POST /api/content/cleanup-module/

    Request Body:
    {
        "module_name": "SQL"
    }

    Response:
    {
        "success": true,
        "module_name": "SQL",
        "cleaned_images": 2,
        "current_images_count": 5,
        "current_articles_count": 2
    }
    """
    try:
        module_name = request.data.get("module_name")
        if not module_name:
            return Response(
                {"success": False, "error": "module_name ist erforderlich"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        orchestration_service = ContentOrchestrationService()
        cleanup_result = orchestration_service.cleanup_old_content(module_name)

        if cleanup_result["success"]:
            return Response(cleanup_result, status=status.HTTP_200_OK)
        else:
            return Response(cleanup_result, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.error(f"Fehler bei der Bereinigung von Modul {module_name}: {e}")
        return Response(
            {"success": False, "error": f"Fehler bei der Bereinigung: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
