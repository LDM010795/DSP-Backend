"""
Einfache Test API für Microsoft Graph User.Read.All Permission
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ..core_integrations.mixins import GraphAPIBaseMixin
from ..core_integrations.token_manager import azure_token_manager
import logging

logger = logging.getLogger(__name__)

class UserReadTestView(APIView):
    """
    Test View für User.Read.All Permission
    
    Endpoints:
    GET /api/microsoft/graph/test/ - Testet User.Read.All Permission
    """
    
    def get(self, request):
        """
        Testet ob User.Read.All Permission korrekt konfiguriert ist
        
        Returns:
            Response mit Test-Ergebnis
        """
        try:
            logger.info("Testing User.Read.All permission")
            
            # 1. Token holen
            try:
                token = azure_token_manager.get_access_token()
                token_success = True
                token_message = "Token successfully obtained"
            except Exception as e:
                token_success = False
                token_message = f"Token failed: {str(e)}"
                logger.error(f"Token error: {str(e)}")
            
            if not token_success:
                return Response({
                    'success': False,
                    'message': 'Azure Token Test failed',
                    'token_test': {
                        'success': False,
                        'error': token_message
                    },
                    'next_steps': [
                        'Check AZURE_TENANT_ID environment variable',
                        'Check AZURE_CLIENT_ID environment variable', 
                        'Check AZURE_CLIENT_SECRET environment variable'
                    ]
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 2. User.Read.All Test mit /me endpoint
            try:
                mixin = GraphAPIBaseMixin()
                me_info = mixin.call_graph_api('me')
                
                user_read_success = True
                user_read_message = "User.Read.All permission working"
                user_display_name = me_info.get('displayName', 'Unknown')
                user_email = me_info.get('mail') or me_info.get('userPrincipalName', 'No email')
                
            except Exception as e:
                user_read_success = False
                user_read_message = f"User.Read.All failed: {str(e)}"
                user_display_name = None
                user_email = None
                logger.error(f"User.Read.All error: {str(e)}")
            
            # 3. Ergebnis
            overall_success = token_success and user_read_success
            
            response_data = {
                'success': overall_success,
                'message': 'User.Read.All permission test completed',
                'tests': {
                    'token_test': {
                        'success': token_success,
                        'message': token_message
                    },
                    'user_read_test': {
                        'success': user_read_success,
                        'message': user_read_message
                    }
                }
            }
            
            # Wenn erfolgreich, User-Info hinzufügen
            if overall_success:
                response_data['user_info'] = {
                    'display_name': user_display_name,
                    'email': user_email
                }
                response_data['next_steps'] = [
                    'User.Read.All permission is working!',
                    'You can now add more permissions like Directory.Read.All',
                    'Try endpoint: GET /api/microsoft/graph/me'
                ]
            else:
                response_data['troubleshooting'] = [
                    'Go to Azure Portal → App registrations → Your App',
                    'Navigate to API permissions',
                    'Add permission → Microsoft Graph → Application permissions',
                    'Select User.Read.All',
                    'Click "Grant admin consent for [your organization]"'
                ]
            
            return Response(
                response_data, 
                status=status.HTTP_200_OK if overall_success else status.HTTP_403_FORBIDDEN
            )
            
        except Exception as e:
            logger.error(f"User.Read.All test failed: {str(e)}")
            return Response({
                'success': False,
                'message': f'Test failed with unexpected error: {str(e)}',
                'error_type': type(e).__name__
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)