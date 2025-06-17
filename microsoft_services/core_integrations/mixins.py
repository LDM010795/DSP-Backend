import requests
import logging
from typing import Dict, Any, Optional
from rest_framework.response import Response
from rest_framework import status
from .token_manager import azure_token_manager
from .exceptions import (
    MicrosoftGraphException,
    AzureAuthException,
    TokenExpiredException,
    InvalidTokenException,
    InsufficientPermissionsException,
    RateLimitException,
    ResourceNotFoundException,
    BadRequestException,
    ServiceUnavailableException
)

logger = logging.getLogger(__name__)

class GraphAPIBaseMixin:
    """
    READ-ONLY Basis-Mixin für Microsoft Graph API Integrationen
    Nutzt AzureTokenManager für Authentication und Custom Exceptions
    Nur GET-Requests erlaubt für Sicherheit
    """
    
    GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
    
    def call_graph_api(self, endpoint: str, params: Optional[Dict] = None, timeout: int = 5) -> Dict[str, Any]:
        """
        Führt READ-ONLY Microsoft Graph API Call aus (mit Timeout)
        
        Args:
            endpoint: Graph API Endpunkt (z.B. 'me', 'users')
            params: URL Query Parameter
            timeout: Request Timeout in Sekunden (default: 5)
            
        Returns:
            Dict mit Graph API Response
            
        Raises:
            AzureAuthException: Bei Token-Fehlern
            MicrosoftGraphException: Bei Graph API Fehlern
            requests.Timeout: Bei Timeout
        """
        try:
            # 1. Token vom TokenManager holen
            access_token = azure_token_manager.get_access_token()
            
            # 2. URL und Headers vorbereiten
            url = f"{self.GRAPH_BASE_URL}/{endpoint.lstrip('/')}"
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            # 3. Nur GET Request ausführen (READ-ONLY mit Timeout)
            logger.info(f"Graph API Call: GET {endpoint} (timeout: {timeout}s)")
            response = requests.get(url, headers=headers, params=params, timeout=timeout)
            
            # 4. Response verarbeiten
            return self._handle_graph_response(response)
            
        except AzureAuthException:
            # Auth-Fehler weiterleiten
            raise
        except requests.exceptions.Timeout:
            logger.warning(f"Graph API timeout after {timeout}s for endpoint: {endpoint}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Graph API Request failed: {str(e)}")
            raise MicrosoftGraphException(f"Graph API Request failed: {str(e)}")
    
    def proxy_request(self, request, graph_path: str) -> Response:
        """
        READ-ONLY Proxy für Django Request zu Graph API
        Nur GET-Requests werden weitergeleitet
        
        Args:
            request: Django Request Object
            graph_path: Graph API Pfad aus URL
            
        Returns:
            Django Response mit Graph API Daten
        """
        try:
            # Nur GET-Requests erlauben
            if request.method.upper() != 'GET':
                return Response(
                    {
                        'error': f'Method {request.method} not allowed. Only GET requests supported.',
                        'endpoint': graph_path
                    }, 
                    status=status.HTTP_405_METHOD_NOT_ALLOWED
                )
            
            # Query Parameter extrahieren
            params = request.GET.dict() if hasattr(request, 'GET') else None
            
            # Graph API Call (nur GET)
            result = self.call_graph_api(endpoint=graph_path,params=params)
            
            return Response(result, status=status.HTTP_200_OK)
            
        except TokenExpiredException as e:
            logger.warning(f"Token expired for endpoint {graph_path}")
            return Response(
                {
                    'error': 'Azure access token has expired',
                    'error_code': 'TokenExpired',
                    'endpoint': graph_path
                }, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        except InsufficientPermissionsException as e:
            logger.warning(f"Insufficient permissions for endpoint {graph_path}")
            return Response(
                {
                    'error': 'Insufficient permissions for this resource',
                    'error_code': 'Forbidden',
                    'endpoint': graph_path
                }, 
                status=status.HTTP_403_FORBIDDEN
            )
        except RateLimitException as e:
            logger.warning(f"Rate limit exceeded for endpoint {graph_path}")
            return Response(
                {
                    'error': 'Rate limit exceeded',
                    'error_code': 'TooManyRequests',
                    'retry_after': e.retry_after,
                    'endpoint': graph_path
                }, 
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        except ResourceNotFoundException as e:
            logger.info(f"Resource not found: {graph_path}")
            return Response(
                {
                    'error': 'Requested resource not found',
                    'error_code': 'NotFound',
                    'endpoint': graph_path
                }, 
                status=status.HTTP_404_NOT_FOUND
            )
        except (MicrosoftGraphException, AzureAuthException) as e:
            logger.error(f"Proxy request failed: {str(e)}")
            return Response(
                {
                    'error': str(e),
                    'error_code': getattr(e, 'error_code', 'Unknown'),
                    'endpoint': graph_path,
                    'method': request.method
                }, 
                status=getattr(e, 'status_code', status.HTTP_400_BAD_REQUEST)
            )
    
    def _handle_graph_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Verarbeitet Graph API Response und wirft spezifische Exceptions
        
        Args:
            response: requests Response Object
            
        Returns:
            Parsed JSON Response
            
        Raises:
            Spezifische Microsoft Graph Exceptions basierend auf Status Code
        """
        try:
            response_data = response.json()
        except ValueError:
            # Fallback für non-JSON responses
            response_data = {'message': 'Success', 'status_code': response.status_code}
        
        if response.status_code >= 400:
            error_info = response_data.get('error', {})
            error_msg = error_info.get('message', f'HTTP {response.status_code}')
            error_code = error_info.get('code', 'Unknown')
            
            logger.error(f"Graph API Error {response.status_code}: {error_msg}")
            
            # Spezifische Exceptions basierend auf Status Code
            if response.status_code == 401:
                if 'token' in error_msg.lower() or error_code == 'InvalidAuthenticationToken':
                    raise TokenExpiredException(error_msg)
                else:
                    raise InvalidTokenException(error_msg)
            elif response.status_code == 403:
                raise InsufficientPermissionsException(error_msg)
            elif response.status_code == 404:
                raise ResourceNotFoundException(error_msg)
            elif response.status_code == 400:
                raise BadRequestException(error_msg)
            elif response.status_code == 429:
                retry_after = response.headers.get('Retry-After')
                retry_seconds = int(retry_after) if retry_after else None
                raise RateLimitException(error_msg, retry_after=retry_seconds)
            elif response.status_code == 503:
                raise ServiceUnavailableException(error_msg)
            else:
                # Fallback für andere Fehler
                raise MicrosoftGraphException(
                    error_msg,
                    status_code=response.status_code,
                    error_code=error_code
                )
        
        logger.debug(f"Graph API Success: {response.status_code}")
        return response_data