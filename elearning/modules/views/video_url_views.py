from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from ..models import Content
from ..services.wasabi_service import WasabiService
from urllib.parse import urlparse


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_video_presigned_url(request, content_id):
    print(f"🔍 DEBUG: Video URL Request für content_id: {content_id}")
    print(f"🔍 DEBUG: User: {request.user}")
    print(f"🔍 DEBUG: User authenticated: {request.user.is_authenticated}")

    try:
        print(f"🔍 DEBUG: Versuche Content mit ID {content_id} zu laden...")
        content = Content.objects.get(pk=content_id)
        print(f"🔍 DEBUG: Content gefunden: {content.title}")
        print(f"🔍 DEBUG: Video URL: {content.video_url}")

        # Extrahiere den Key aus der Wasabi URL
        if not content.video_url or "wasabisys.com" not in content.video_url:
            print(f"🔍 DEBUG: Keine gültige Wasabi URL: {content.video_url}")
            return Response(
                {"error": "Keine gültige Wasabi URL gefunden"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Extrahiere den Key aus der URL
        try:
            parsed_url = urlparse(content.video_url)
            path_parts = parsed_url.path.strip("/").split("/")

            if len(path_parts) >= 2:
                # path-style: s3.eu-.../bucket/key...
                key = "/".join(path_parts[1:])  # Skip bucket name
            else:
                # virtual-host: bucket.s3.eu-.../key...
                key = "/".join(path_parts)

            print(f"🔍 DEBUG: Extrahierter Key: {key}")
        except Exception as e:
            print(f"🔍 DEBUG: Fehler beim Extrahieren des Keys: {str(e)}")
            return Response(
                {"error": "Fehler beim Extrahieren des Video-Keys"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Generiere presigned URL
        wasabi_service = WasabiService()
        presigned_url = wasabi_service.generate_presigned_url(key)

        if not presigned_url:
            print("🔍 DEBUG: Konnte keine presigned URL generieren")
            return Response(
                {"error": "Konnte keine presigned URL generieren"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        response_data = {
            "presigned_url": presigned_url,
            "expires_in": 7200,  # 2 Stunden
            "content_id": content_id,
            "video_title": content.title,
        }

        print(f"🔍 DEBUG: Sende Response: {response_data}")
        return Response(response_data)

    except Content.DoesNotExist:
        print(f"🔍 DEBUG: Content mit ID {content_id} nicht gefunden!")
        return Response(
            {"error": "Content nicht gefunden"}, status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        print(f"🔍 DEBUG: Exception aufgetreten: {str(e)}")
        import traceback

        print(f"🔍 DEBUG: Traceback: {traceback.format_exc()}")
        return Response(
            {"error": f"Server-Fehler: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_video_presigned_url_by_key(request):
    """Neuer Endpoint für presigned URLs direkt per Key"""
    print("🔍 DEBUG: Video URL Request by key")
    print(f"🔍 DEBUG: User: {request.user}")

    key = request.GET.get("key")
    if not key:
        return Response(
            {"error": "Key Parameter fehlt"}, status=status.HTTP_400_BAD_REQUEST
        )

    print(f"🔍 DEBUG: Requested Key: {key}")

    try:
        # Generiere presigned URL direkt per Key
        wasabi_service = WasabiService()
        presigned_url = wasabi_service.generate_presigned_url(key)

        if not presigned_url:
            print(f"🔍 DEBUG: Konnte keine presigned URL für Key {key} generieren")
            return Response(
                {"error": "Konnte keine presigned URL generieren"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        response_data = {
            "presigned_url": presigned_url,
            "expires_in": 7200,  # 2 Stunden
            "key": key,
        }

        print(f"🔍 DEBUG: Sende Response für Key {key}: {response_data}")
        return Response(response_data)

    except Exception as e:
        print(f"🔍 DEBUG: Exception bei Key {key}: {str(e)}")
        import traceback

        print(f"🔍 DEBUG: Traceback: {traceback.format_exc()}")
        return Response(
            {"error": f"Server-Fehler: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
def test_video_endpoint(request):
    """Test endpoint ohne Authentifizierung"""
    return JsonResponse(
        {"message": "Video endpoint funktioniert!", "status": "success"}
    )
