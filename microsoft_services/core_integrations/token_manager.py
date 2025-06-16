import os
import requests
import logging
from typing import Optional
from datetime import datetime, timedelta
from django.core.cache import cache
from .exceptions import AzureAuthException

logger = logging.getLogger(__name__)

class AzureTokenManager:
    """
    Zentrale Klasse für Azure AD Token Management
    Holt Environment Variables und verwaltet Access Tokens
    """
    
    def __init__(self):
        # Environment Variables laden
        self.tenant_id = os.environ.get('AZURE_TENANT_ID')
        self.client_id = os.environ.get('AZURE_CLIENT_ID')
        self.client_secret = os.environ.get('AZURE_CLIENT_SECRET')
        self.scope = "https://graph.microsoft.com/.default"
        
        # Validierung
        self._validate_credentials()
    
    def _validate_credentials(self):
        """Validiert dass alle Environment Variables gesetzt sind"""
        missing = []
        if not self.tenant_id:
            missing.append('AZURE_TENANT_ID')
        if not self.client_id:
            missing.append('AZURE_CLIENT_ID')
        if not self.client_secret:
            missing.append('AZURE_CLIENT_SECRET')
        
        if missing:
            raise AzureAuthException(
                f"Missing Azure credentials in environment: {', '.join(missing)}"
            )
    
    def get_access_token(self) -> str:
        """
        Holt oder erneuert Azure Access Token
        Verwendet Caching für Performance
        
        Returns:
            Azure Access Token String
            
        Raises:
            AzureAuthException: Bei Token-Fehlern
        """
        # Cache Key
        cache_key = f"azure_token_{self.client_id}"
        
        # Prüfe Cache
        cached_token = cache.get(cache_key)
        if cached_token:
            logger.debug("Using cached Azure access token")
            return cached_token
        
        # Neuen Token von Azure holen
        logger.info("Requesting new Azure access token")
        token = self._request_token_from_azure()
        
        # Token cachen (55 Minuten - Azure Tokens sind 60min gültig)
        cache.set(cache_key, token, timeout=3300)
        
        return token
    
    def _request_token_from_azure(self) -> str:
        """
        Fordert neuen Access Token von Azure AD an
        Verwendet Client Credentials Flow
        
        Returns:
            Access Token String
            
        Raises:
            AzureAuthException: Bei Azure API Fehlern
        """
        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        
        # POST Data für Client Credentials Flow
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': self.scope
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        try:
            logger.debug(f"Requesting token from: {token_url}")
            response = requests.post(token_url, data=data, headers=headers, timeout=30)
            response.raise_for_status()
            
            token_data = response.json()
            access_token = token_data.get('access_token')
            
            if not access_token:
                raise AzureAuthException("No access_token in Azure response")
            
            logger.info("Successfully obtained Azure access token")
            return access_token
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Azure token request failed: {str(e)}")
            raise AzureAuthException(f"Failed to obtain Azure token: {str(e)}")
        except KeyError as e:
            logger.error(f"Invalid Azure token response: {str(e)}")
            raise AzureAuthException(f"Invalid token response from Azure: {str(e)}")
    
    def test_token(self, token: Optional[str] = None) -> dict:
        """
        Testet ob ein Token funktioniert
        
        Args:
            token: Token zum Testen (optional, sonst wird neuer geholt)
            
        Returns:
            Dict mit Test-Ergebnis
        """
        if not token:
            try:
                token = self.get_access_token()
            except AzureAuthException as e:
                return {
                    'success': False,
                    'message': f'Token generation failed: {str(e)}'
                }
        
        # Test Graph API Call
        try:
            headers = {'Authorization': f'Bearer {token}'}
            response = requests.get(
                'https://graph.microsoft.com/v1.0/organization',
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'message': 'Token is valid',
                    'graph_api_accessible': True
                }
            else:
                return {
                    'success': False,
                    'message': f'Graph API returned status {response.status_code}',
                    'response': response.text[:200]
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'Token test failed: {str(e)}'
            }

# Singleton Instance für App-weite Nutzung
azure_token_manager = AzureTokenManager()