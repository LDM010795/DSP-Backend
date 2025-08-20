"""
Article Processing Views für DSP E-Learning Platform

API-Endpoints für die automatische Artikel-Verarbeitung:
- POST /api/modules/content/process-article/ - Verarbeitet einen Artikel aus Cloud-URL

Author: DSP Development Team
Version: 1.0.0
"""

import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

# Import des Article Processing Services
from ...services.content_processing import ArticleProcessingService

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_article_from_cloud(request):
    """
    Verarbeitet einen Artikel aus einer Cloud-URL.
    
    POST /api/modules/content/process-article/
    
    Request Body:
    {
        "moduleId": 1,
        "chapterId": 2,  // Optional
        "cloudUrl": "https://s3.eu-central-2.wasabisys.com/dsp-e-learning/Lerninhalte/SQL/Artikel/1.1 Installation und erste Schritte.docx"
    }
    
    Response:
    {
        "success": true,
        "article_title": "Installation und erste Schritte",
        "article_id": 1,
        "images_found": ["ABB1.1", "ABB1.2"],
        "images_saved": 2,
        "errors": [],
        "warnings": []
    }
    """
    try:
        # Request-Daten validieren
        module_id = request.data.get('moduleId')
        chapter_id = request.data.get('chapterId')  # Optional
        cloud_url = request.data.get('cloudUrl')
        
        if not module_id:
            return Response({
                'success': False,
                'error': 'moduleId ist erforderlich'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not cloud_url:
            return Response({
                'success': False,
                'error': 'cloudUrl ist erforderlich'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Article Processing Service initialisieren
        article_service = ArticleProcessingService()
        
        # URL validieren
        validation = article_service.validate_cloud_url(cloud_url)
        if not validation['valid']:
            return Response({
                'success': False,
                'error': 'Ungültige Cloud-URL',
                'details': validation['errors']
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Artikel verarbeiten mit optionaler Chapter-Zuordnung
        result = article_service.process_article_from_cloud_url(module_id, cloud_url, chapter_id)
        
        # Response erstellen
        response_data = {
            'success': result.success,
            'article_title': result.article_title,
            'article_id': result.article_id,
            'images_found': result.images_found,
            'images_saved': result.images_saved,
            'errors': result.errors,
            'warnings': result.warnings
        }
        
        if result.success:
            logger.info(f"Artikel '{result.article_title}' erfolgreich verarbeitet")
            return Response(response_data, status=status.HTTP_200_OK)
        else:
            logger.error(f"Fehler bei der Artikel-Verarbeitung: {result.errors}")
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Unerwarteter Fehler in process_article_from_cloud: {e}")
        return Response({
            'success': False,
            'error': f'Interner Serverfehler: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validate_cloud_url(request):
    """
    Validiert eine Cloud-URL.
    
    POST /api/modules/content/validate-cloud-url/
    
    Request Body:
    {
        "cloudUrl": "https://s3.eu-central-2.wasabisys.com/dsp-e-learning/Lerninhalte/SQL/Artikel/1.1 Installation und erste Schritte.docx"
    }
    
    Response:
    {
        "valid": true,
        "parsed_info": {
            "bucket_name": "dsp-e-learning",
            "module_name": "SQL",
            "file_name": "1.1 Installation und erste Schritte.docx",
            "object_key": "dsp-e-learning/Lerninhalte/SQL/Artikel/1.1 Installation und erste Schritte.docx"
        }
    }
    """
    try:
        cloud_url = request.data.get('cloudUrl')
        
        if not cloud_url:
            return Response({
                'valid': False,
                'error': 'cloudUrl ist erforderlich'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Article Processing Service initialisieren
        article_service = ArticleProcessingService()
        
        # URL validieren
        validation = article_service.validate_cloud_url(cloud_url)
        
        return Response(validation, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Unerwarteter Fehler in validate_cloud_url: {e}")
        return Response({
            'valid': False,
            'error': f'Interner Serverfehler: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 