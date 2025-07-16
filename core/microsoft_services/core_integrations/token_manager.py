"""
Azure Active Directory Token Manager

This module provides a robust, production-ready Azure AD token management system
for Microsoft Graph API integration. It handles token acquisition, caching,
validation, and automatic refresh with proper error handling and logging.

The token manager implements the OAuth 2.0 Client Credentials flow for
application-level authentication and provides thread-safe token caching
to optimize performance and reduce API calls.

Author: DSP Development Team
Version: 1.0.0
"""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from threading import Lock

import requests
from django.core.cache import cache
from django.conf import settings

from .exceptions import AzureAuthException, ServiceUnavailableException

logger = logging.getLogger(__name__)


class AzureTokenManager:
    """
    Thread-safe Azure AD token manager for Microsoft Graph API authentication.
    
    This class implements the OAuth 2.0 Client Credentials flow to obtain
    application-level access tokens for Microsoft Graph API. It provides
    automatic token caching, validation, and refresh capabilities.
    
    Attributes:
        CACHE_PREFIX (str): Prefix for cache keys
        DEFAULT_SCOPE (str): Default OAuth scope for Microsoft Graph
        TOKEN_BUFFER_SECONDS (int): Buffer time before token expiration
        REQUEST_TIMEOUT (int): HTTP request timeout in seconds
    
    Example:
        >>> token_manager = AzureTokenManager()
        >>> access_token = token_manager.get_access_token()
        >>> # Use access_token for Microsoft Graph API calls
    """
    
    CACHE_PREFIX = "azure_token"
    DEFAULT_SCOPE = "https://graph.microsoft.com/.default"
    TOKEN_BUFFER_SECONDS = 300  # 5 minutes buffer before expiration
    REQUEST_TIMEOUT = 30  # 30 seconds request timeout
    
    def __init__(self) -> None:
        """
        Initialize the Azure Token Manager.
        
        Loads and validates Azure AD credentials from environment variables
        or Django settings.
        
        Raises:
            AzureAuthException: If required credentials are missing or invalid
        """
        self._lock = Lock()
        self._load_credentials()
        self._validate_credentials()
    
    def _load_credentials(self) -> None:
        """
        Load Azure AD credentials from environment variables or Django settings.
        
        Attempts to load credentials from environment variables first,
        then falls back to Django settings if available.
        """
        # Primary: Environment variables
        self.tenant_id = os.environ.get('AZURE_TENANT_ID')
        self.client_id = os.environ.get('AZURE_CLIENT_ID')
        self.client_secret = os.environ.get('AZURE_CLIENT_SECRET')
        
        # Fallback: Django settings (if available)
        if hasattr(settings, 'AZURE_TENANT_ID') and not self.tenant_id:
            self.tenant_id = getattr(settings, 'AZURE_TENANT_ID', None)
        if hasattr(settings, 'AZURE_CLIENT_ID') and not self.client_id:
            self.client_id = getattr(settings, 'AZURE_CLIENT_ID', None)
        if hasattr(settings, 'AZURE_CLIENT_SECRET') and not self.client_secret:
            self.client_secret = getattr(settings, 'AZURE_CLIENT_SECRET', None)
        
        # Configurable scope
        self.scope = os.environ.get('AZURE_SCOPE', self.DEFAULT_SCOPE)
    
    def _validate_credentials(self) -> None:
        """
        Validate that all required Azure AD credentials are present.
        
        Raises:
            AzureAuthException: If any required credential is missing
        """
        missing_credentials = []
        
        if not self.tenant_id:
            missing_credentials.append('AZURE_TENANT_ID')
        if not self.client_id:
            missing_credentials.append('AZURE_CLIENT_ID')
        if not self.client_secret:
            missing_credentials.append('AZURE_CLIENT_SECRET')
        
        if missing_credentials:
            raise AzureAuthException(
                f"Missing required Azure AD credentials: {', '.join(missing_credentials)}. "
                f"Please set these as environment variables or in Django settings.",
                auth_step="credential_validation"
            )
        
        # Validate credential format
        if not self.tenant_id.replace('-', '').replace('_', '').isalnum():
            raise AzureAuthException(
                "Invalid AZURE_TENANT_ID format. Expected UUID or domain name.",
                auth_step="credential_validation"
            )
    
    def get_access_token(self, force_refresh: bool = False) -> str:
        """
        Get a valid Azure AD access token with automatic caching and refresh.
        
        This method first checks the cache for a valid token. If no valid token
        is found or force_refresh is True, it requests a new token from Azure AD.
        
        Args:
            force_refresh: Force token refresh even if cached token is valid
        
        Returns:
            Valid Azure AD access token
        
        Raises:
            AzureAuthException: If token acquisition fails
            ServiceUnavailableException: If Azure AD service is unavailable
        
        Example:
            >>> token = token_manager.get_access_token()
            >>> # Use token for API calls
            >>> 
            >>> # Force refresh if needed
            >>> fresh_token = token_manager.get_access_token(force_refresh=True)
        """
        with self._lock:
            cache_key = f"{self.CACHE_PREFIX}_{self.client_id}"
            
            # Check cache first (unless forced refresh)
            if not force_refresh:
                cached_token = cache.get(cache_key)
                if cached_token:
                    logger.debug("Using cached Azure AD access token")
                    return cached_token
            
            # Request new token from Azure AD
            logger.info("Requesting new Azure AD access token")
            token_data = self._request_token_from_azure()
            
            access_token = token_data.get('access_token')
            if not access_token:
                raise AzureAuthException(
                    "No access_token in Azure AD response",
                    auth_step="token_extraction"
                )
            
            # Calculate cache timeout with buffer
            expires_in = token_data.get('expires_in', 3600)  # Default 1 hour
            cache_timeout = max(expires_in - self.TOKEN_BUFFER_SECONDS, 60)  # Min 1 minute
            
            # Cache the token
            cache.set(cache_key, access_token, timeout=cache_timeout)
            
            logger.info(
                f"Successfully obtained and cached Azure AD access token "
                f"(expires in {expires_in}s, cached for {cache_timeout}s)"
            )
            
            return access_token
    
    def _request_token_from_azure(self) -> Dict[str, Any]:
        """
        Request a new access token from Azure AD using Client Credentials flow.
        
        Returns:
            Token response data from Azure AD
        
        Raises:
            AzureAuthException: If token request fails
            ServiceUnavailableException: If Azure AD is temporarily unavailable
        """
        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        
        # Prepare OAuth 2.0 Client Credentials request
        request_data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': self.scope
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        
        try:
            logger.debug(f"Requesting token from Azure AD: {token_url}")
            
            response = requests.post(
                token_url,
                data=request_data,
                headers=headers,
                timeout=self.REQUEST_TIMEOUT
            )
            
            # Handle different response scenarios
            if response.status_code == 200:
                return self._parse_token_response(response)
            elif response.status_code == 503:
                raise ServiceUnavailableException(
                    "Azure AD service temporarily unavailable",
                    estimated_recovery_time=300  # 5 minutes
                )
            else:
                self._handle_token_error_response(response)
                
        except requests.exceptions.Timeout:
            raise AzureAuthException(
                f"Azure AD token request timed out after {self.REQUEST_TIMEOUT}s",
                auth_step="request_timeout"
            )
        except requests.exceptions.ConnectionError as e:
            raise AzureAuthException(
                f"Failed to connect to Azure AD: {str(e)}",
                auth_step="connection_error"
            )
        except requests.exceptions.RequestException as e:
            raise AzureAuthException(
                f"Azure AD token request failed: {str(e)}",
                auth_step="request_error"
            )
    
    def _parse_token_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Parse and validate the token response from Azure AD.
        
        Args:
            response: HTTP response from Azure AD token endpoint
        
        Returns:
            Parsed token data
        
        Raises:
            AzureAuthException: If response parsing fails
        """
        try:
            token_data = response.json()
            
            # Validate required fields
            required_fields = ['access_token', 'token_type', 'expires_in']
            missing_fields = [field for field in required_fields if field not in token_data]
            
            if missing_fields:
                raise AzureAuthException(
                    f"Invalid Azure AD token response: missing fields {missing_fields}",
                    auth_step="response_validation"
                )
            
            # Validate token type
            if token_data.get('token_type', '').lower() != 'bearer':
                logger.warning(f"Unexpected token type: {token_data.get('token_type')}")
            
            return token_data
            
        except ValueError as e:
            raise AzureAuthException(
                f"Invalid JSON in Azure AD token response: {str(e)}",
                auth_step="response_parsing"
            )
    
    def _handle_token_error_response(self, response: requests.Response) -> None:
        """
        Handle error responses from Azure AD token endpoint.
        
        Args:
            response: HTTP error response from Azure AD
        
        Raises:
            AzureAuthException: With detailed error information
        """
        try:
            error_data = response.json()
            error_code = error_data.get('error', 'unknown_error')
            error_description = error_data.get('error_description', 'No description provided')
            
            logger.error(
                f"Azure AD token request failed: {response.status_code} - "
                f"{error_code}: {error_description}"
            )
            
            raise AzureAuthException(
                f"Azure AD authentication failed ({error_code}): {error_description}",
                auth_step="token_request_error"
            )
            
        except ValueError:
            # Non-JSON error response
            logger.error(f"Azure AD token request failed: {response.status_code} - {response.text}")
            raise AzureAuthException(
                f"Azure AD authentication failed with status {response.status_code}",
                auth_step="token_request_error"
            )
    
    def invalidate_cache(self) -> bool:
        """
        Manually invalidate the cached access token.
        
        This is useful when you know the token has been revoked or
        when you want to force a refresh on the next request.
        
        Returns:
            True if cache was cleared, False if no cached token existed
        """
        cache_key = f"{self.CACHE_PREFIX}_{self.client_id}"
        cached_token = cache.get(cache_key)
        
        if cached_token:
            cache.delete(cache_key)
            logger.info("Azure AD access token cache invalidated")
            return True
        
        return False
    
    def test_token(self, token: Optional[str] = None) -> Dict[str, Any]:
        """
        Test token validity by making a test call to Microsoft Graph API.
        
        Args:
            token: Token to test (if None, gets current token)
        
        Returns:
            Dictionary with test results and token information
        
        Example:
            >>> result = token_manager.test_token()
            >>> if result['valid']:
            ...     print(f"Token valid, expires in {result['expires_in']}s")
            ... else:
            ...     print(f"Token invalid: {result['error']}")
        """
        test_start = datetime.now()
        
        if not token:
            try:
                token = self.get_access_token()
            except AzureAuthException as e:
                return {
                    'valid': False,
                    'error': f'Token acquisition failed: {str(e)}',
                    'auth_step': getattr(e, 'auth_step', 'unknown'),
                    'test_duration_ms': (datetime.now() - test_start).total_seconds() * 1000
                }
        
        # Test token with Microsoft Graph API
        try:
            headers = {
                'Authorization': f'Bearer {token}',
                'Accept': 'application/json'
            }
            
            response = requests.get(
                'https://graph.microsoft.com/v1.0/organization',
                headers=headers,
                timeout=10
            )
            
            test_duration = (datetime.now() - test_start).total_seconds() * 1000
            
            if response.status_code == 200:
                org_data = response.json()
                return {
                    'valid': True,
                    'graph_api_accessible': True,
                    'organization_count': len(org_data.get('value', [])),
                    'test_duration_ms': test_duration
                }
            else:
                return {
                    'valid': False,
                    'error': f'Graph API returned status {response.status_code}',
                    'response_snippet': response.text[:200],
                    'test_duration_ms': test_duration
                }
                
        except Exception as e:
            test_duration = (datetime.now() - test_start).total_seconds() * 1000
            return {
                'valid': False,
                'error': f'Token test failed: {str(e)}',
                'test_duration_ms': test_duration
            }
    
    def get_token_info(self) -> Dict[str, Any]:
        """
        Get information about the current token configuration and status.
        
        Returns:
            Dictionary with token manager configuration and status
        """
        cache_key = f"{self.CACHE_PREFIX}_{self.client_id}"
        cached_token_exists = cache.get(cache_key) is not None
        
        return {
            'tenant_id': self.tenant_id,
            'client_id': self.client_id[:8] + '...' if self.client_id else None,  # Masked for security
            'scope': self.scope,
            'cached_token_exists': cached_token_exists,
            'cache_key': cache_key,
            'token_buffer_seconds': self.TOKEN_BUFFER_SECONDS,
            'request_timeout': self.REQUEST_TIMEOUT
        }


# Lazy-loaded singleton instance for application-wide use
class _LazyAzureTokenManager:
    """
    Lazy wrapper for AzureTokenManager to prevent import-time initialization.
    
    This prevents Azure credential validation during Django startup/imports
    when the token manager is not actually needed (e.g., for management commands).
    The actual AzureTokenManager is only instantiated when first accessed.
    """
    
    def __init__(self):
        self._instance: Optional[AzureTokenManager] = None
        self._lock = Lock()
    
    def __getattr__(self, name):
        """Delegate all attribute access to the actual token manager instance."""
        if self._instance is None:
            with self._lock:
                if self._instance is None:
                    self._instance = AzureTokenManager()
        return getattr(self._instance, name)
    
    def __bool__(self):
        """Support boolean checks without triggering initialization."""
        return True
    
    def __repr__(self):
        """String representation without triggering initialization."""
        return f"<LazyAzureTokenManager: {'initialized' if self._instance else 'not initialized'}>"

azure_token_manager = _LazyAzureTokenManager()