"""
Microsoft Organization User Authentication API

This module provides production-ready authentication views for Microsoft Azure AD
integration with comprehensive error handling, security measures, and audit logging.
The API is designed to be generic and reusable across different frontend applications.

The authentication flow follows OAuth 2.0 Authorization Code Flow:
1. Frontend requests authorization URL
2. User authenticates with Microsoft
3. Microsoft redirects to callback with authorization code
4. Frontend exchanges code for JWT tokens via API call

Security Features:
- State parameter validation to prevent CSRF attacks
- Organization membership validation
- Comprehensive audit logging
- Generic frontend routing (no hardcoded URLs)
- Rate limiting and error handling

Author: DSP Development Team
Version: 1.0.0
"""

import logging
import secrets
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlencode
from dataclasses import dataclass

import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponseRedirect

from microsoft_services.core_integrations.mixins import GraphAPIBaseMixin
from microsoft_services.core_integrations.role_authentication import role_authenticator
from microsoft_services.core_integrations.exceptions import (
    AzureAuthException,
    MicrosoftGraphException,
    ResourceNotFoundException
)
from microsoft_services.authentications.state_manager import get_oauth_mixin

logger = logging.getLogger(__name__)
User = get_user_model()


@dataclass
class OrganizationValidationResult:
    """
    Result object for organization validation operations.
    
    Attributes:
        valid: Whether the user is valid in the organization
        user_data: Microsoft Graph user data if valid
        error_message: Error message if validation failed
        account_enabled: Whether the user account is enabled
    """
    valid: bool
    user_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    account_enabled: bool = False


class MicrosoftAuthenticationMixin(get_oauth_mixin()):
    """
    Production-ready Microsoft authentication functionality.
    
    Automatische Auswahl zwischen Production (Redis) und Development (Session) State-Management.
    """
    
    OAUTH_SCOPE = 'openid email profile User.Read Directory.Read.All'
    TOKEN_CACHE_TIMEOUT = 300  # 5 minutes
    
    def _build_redirect_uri(self, request) -> str:
        """
        Build the OAuth redirect URI based on the current request.
        
        Args:
            request: Django HTTP request object
        
        Returns:
            Complete redirect URI for OAuth callback
        """
        return request.build_absolute_uri('/api/microsoft/auth/callback/')
            
    def _create_oauth_state(self, request) -> str:
        """
        Create OAuth state - Production-ready implementation
        """
        return self.create_oauth_state(request)
    
    def _validate_oauth_state(self, request, received_state: str) -> bool:
        """
        Validate OAuth state - Production-ready implementation
        """
        return self.validate_oauth_state(request, received_state)
    
    def _exchange_code_for_token(self, auth_code: str, request) -> Optional[Dict[str, Any]]:
        """
        Exchange OAuth authorization code for access token.
        
        Args:
            auth_code: Authorization code from Microsoft OAuth callback
            request: Django HTTP request object for building redirect URI
        
        Returns:
            Token response data or None if exchange failed
        
        Raises:
            AzureAuthException: If token exchange fails
        """
        try:
            token_url = f"https://login.microsoftonline.com/{settings.AZURE_TENANT_ID}/oauth2/v2.0/token"
            
            token_data = {
                'client_id': settings.AZURE_CLIENT_ID,
                'client_secret': settings.AZURE_CLIENT_SECRET,
                'code': auth_code,
                'grant_type': 'authorization_code',
                'redirect_uri': self._build_redirect_uri(request),
                'scope': self.OAUTH_SCOPE
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json'
            }
            
            logger.debug(f"Exchanging authorization code for access token")
            response = requests.post(token_url, data=token_data, headers=headers, timeout=30)
            
            if response.status_code == 200:
                token_response = response.json()
                
                # Validate required fields
                required_fields = ['access_token', 'token_type', 'expires_in']
                if not all(field in token_response for field in required_fields):
                    raise AzureAuthException(
                        f"Invalid token response: missing required fields",
                        auth_step="token_validation"
                    )
                
                logger.info("Successfully exchanged authorization code for access token")
                return token_response
            else:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get('error_description', f'HTTP {response.status_code}')
                logger.error(f"Token exchange failed: {response.status_code} - {error_msg}")
                
                raise AzureAuthException(
                    f"Token exchange failed: {error_msg}",
                    auth_step="token_exchange"
                )
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Token exchange request failed: {str(e)}")
            raise AzureAuthException(
                f"Token exchange request failed: {str(e)}",
                auth_step="request_error"
            )
    
    def _get_microsoft_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve user information from Microsoft Graph API.
        
        Args:
            access_token: Valid Microsoft access token
        
        Returns:
            User information from Microsoft Graph or None if failed
        
        Raises:
            MicrosoftGraphException: If Graph API call fails
        """
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            # Get comprehensive user profile
            user_fields = 'id,displayName,mail,userPrincipalName,givenName,surname,jobTitle,department,officeLocation'
            response = requests.get(
                f'https://graph.microsoft.com/v1.0/me?$select={user_fields}',
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                user_data = response.json()
                logger.debug(f"Retrieved user info for: {user_data.get('mail', user_data.get('userPrincipalName'))}")
                return user_data
            else:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get('error', {}).get('message', f'HTTP {response.status_code}')
                
                logger.error(f"Failed to get user info: {response.status_code} - {error_msg}")
                raise MicrosoftGraphException(
                    f"Failed to retrieve user information: {error_msg}",
                    status_code=response.status_code
                )
                
        except requests.exceptions.RequestException as e:
            logger.error(f"User info request failed: {str(e)}")
            raise MicrosoftGraphException(f"User info request failed: {str(e)}")
    
    def _validate_organization_user(self, user_info: Dict[str, Any]) -> OrganizationValidationResult:
        """
        Validate that the user is an active member of the DSP organization.
        
        Args:
            user_info: User information from Microsoft Graph
        
        Returns:
            Organization validation result with detailed information
        """
        try:
            email = user_info.get('mail') or user_info.get('userPrincipalName')
            
            if not email:
                return OrganizationValidationResult(
                    valid=False,
                    error_message='No email address found in Microsoft profile'
                )
            
            # 1. Domain validation (if configured)
            if not self._validate_email_domain(email):
                return OrganizationValidationResult(
                    valid=False,
                    error_message=f'Email domain not allowed for this organization'
                )
            
            # 2. Organization membership validation
            org_user_data = self._get_organization_user_data(email)
            if not org_user_data:
                return OrganizationValidationResult(
                    valid=False,
                    error_message=f'User {email} not found in organization directory'
                )
            
            # 3. Account status validation
            account_enabled = org_user_data.get('accountEnabled', False)
            if not account_enabled:
                return OrganizationValidationResult(
                    valid=False,
                    error_message=f'Account {email} is disabled in organization',
                    user_data=org_user_data,
                    account_enabled=False
                )
            
            logger.info(f"Organization validation successful for: {email}")
            return OrganizationValidationResult(
                valid=True,
                user_data=org_user_data,
                account_enabled=True
            )
            
        except Exception as e:
            logger.error(f"Organization validation error: {str(e)}", exc_info=True)
            return OrganizationValidationResult(
                valid=False,
                error_message=f'Organization validation failed: {str(e)}'
            )
    
    def _validate_email_domain(self, email: str) -> bool:
        """
        Validate email domain against allowed domains list.
        
        Args:
            email: Email address to validate
        
        Returns:
            True if domain is allowed or no restrictions configured
        """
        allowed_domains = getattr(settings, 'DSP_ALLOWED_DOMAINS', [])
        if not allowed_domains:
            return True  # No domain restrictions
        
        email_domain = email.split('@')[-1].lower()
        return email_domain in [domain.lower() for domain in allowed_domains]
    
    def _get_organization_user_data(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve user data from organization directory via Graph API.
        
        Args:
            email: User's email address
        
        Returns:
            Organization user data or None if not found
        """
        try:
            mixin = GraphAPIBaseMixin()
            
            # Search for user in organization directory
            user_filter = f"mail eq '{email}' or userPrincipalName eq '{email}'"
            search_fields = 'id,displayName,mail,userPrincipalName,accountEnabled,jobTitle,department,officeLocation'
            search_query = f"users?$filter={user_filter}&$select={search_fields}"
            
            users_response = mixin.call_graph_api(search_query)
            users = users_response.get('value', [])
            
            return users[0] if users else None
            
        except Exception as e:
            logger.error(f"Error retrieving organization user data for {email}: {str(e)}")
            return None
    
    def _create_or_update_user(
        self, 
        user_info: Dict[str, Any], 
        org_data: Dict[str, Any]
    ) -> Tuple[User, bool]:
        """
        Create or update Django user based on Microsoft and organization data.
        
        Args:
            user_info: User information from Microsoft Graph
            org_data: Organization-specific user data
        
        Returns:
            Tuple of (User instance, created_flag)
        """
        email = user_info.get('mail') or user_info.get('userPrincipalName')
        
        # Get role assignment from Microsoft groups
        role_result = role_authenticator.get_user_role_from_microsoft(email)
        
        if not role_result.success:
            logger.warning(f"Role assignment failed for {email}: {role_result.error_message}")
            # Use default role if role assignment fails
            role_config = role_authenticator._role_mappings['default']
        else:
            role_config = role_result.role_config
        
        # Create or update user
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': email,
                'first_name': user_info.get('givenName', ''),
                'last_name': user_info.get('surname', ''),
                'is_active': org_data.get('accountEnabled', True),
                'is_staff': role_config.is_staff,
                'is_superuser': role_config.is_superuser,
            }
        )
        
        # Update user data on each login
        user.first_name = user_info.get('givenName', user.first_name)
        user.last_name = user_info.get('surname', user.last_name)
        user.is_active = org_data.get('accountEnabled', True)
        user.is_staff = role_config.is_staff
        user.is_superuser = role_config.is_superuser
        user.save()
        
        # Attach role information for response
        user.role_assignment_result = role_result
        
        # Log user creation/update
        action = "Created" if created else "Updated"
        logger.info(
            f"{action} user from Microsoft: {email} | "
            f"Role: {role_config.role_name} | "
            f"Groups: {role_result.groups if role_result.success else []}"
        )
        
        return user, created


class MicrosoftOrganizationLoginView(APIView, MicrosoftAuthenticationMixin):
    """
    Initialize Microsoft OAuth 2.0 login flow for organization users.
    
    This view generates the Microsoft authorization URL with proper security
    parameters and returns it to the frontend for user redirection.
    
    Endpoint: GET /api/microsoft/auth/login/
    
    Security Features:
    - CSRF protection via state parameter
    - Tenant-specific authentication (organization only)
    - Configurable OAuth scopes
    
    Example Response:
    {
        "success": true,
        "message": "Microsoft organization login URL generated",
        "redirect_url": "https://login.microsoftonline.com/...",
        "state": "secure_random_string",
        "instructions": [...]
    }
    """
    
    def get(self, request) -> Response:
        """
        Generate Microsoft OAuth 2.0 authorization URL for organization login.
        
        Args:
            request: Django HTTP request object
        
        Returns:
            Response containing authorization URL and security parameters
        
        Raises:
            AzureAuthException: If OAuth URL generation fails
        """
        try:
            # 1. Create security state parameter
            state = self._create_oauth_state(request)
            
            # 2. Build OAuth parameters
            oauth_params = self._build_oauth_parameters(request, state)
            
            # 3. Generate Microsoft authorization URL
            auth_url = self._build_authorization_url(oauth_params)
            
            logger.info(f"Generated Microsoft OAuth URL for organization login")
            
            return Response({
                'success': True,
                'message': 'Microsoft organization login URL generated',
                'redirect_url': auth_url,
                'state': state,
                'instructions': [
                    'Redirect user to redirect_url for Microsoft authentication',
                    'User will authenticate with their Microsoft organization account',
                    'Microsoft will redirect back to the callback endpoint',
                    'Frontend should handle callback parameters and call POST /api/microsoft/auth/callback/'
                ],
                'oauth_flow': 'authorization_code',
                'tenant_type': 'organization'
            })
            
        except Exception as e:
            logger.error(f"Failed to generate Microsoft login URL: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': f'Failed to generate login URL: {str(e)}',
                'error_type': 'oauth_generation_error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _build_oauth_parameters(self, request, state: str) -> Dict[str, str]:
        """Build OAuth 2.0 authorization parameters."""
        return {
            'client_id': settings.AZURE_CLIENT_ID,
            'response_type': 'code',
            'redirect_uri': self._build_redirect_uri(request),
            'scope': self.OAUTH_SCOPE,
            'state': state,
            'response_mode': 'query',
            'prompt': 'select_account',  # Force account selection
        }
    
    def _build_authorization_url(self, oauth_params: Dict[str, str]) -> str:
        """Build the complete Microsoft authorization URL."""
        tenant_id = settings.AZURE_TENANT_ID
        base_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize"
        return f"{base_url}?{urlencode(oauth_params)}"


class MicrosoftOrganizationCallbackView(APIView, MicrosoftAuthenticationMixin):
    """
    Handle Microsoft OAuth 2.0 callback and user authentication.
    
    This view provides two endpoints:
    1. GET: Simple redirect handler for Microsoft OAuth callback
    2. POST: Full authentication processing with JWT token generation
    
    The separation allows for flexible frontend routing while maintaining security.
    """
    
    def get(self, request) -> HttpResponseRedirect:
        """
        Handle Microsoft OAuth callback redirect to frontend.
        
        This endpoint receives the OAuth callback from Microsoft and forwards
        all parameters to the frontend for processing. The frontend then makes
        a POST request with the authorization code.
        
        Args:
            request: Django HTTP request with OAuth callback parameters
        
        Returns:
            HTTP redirect to frontend with OAuth parameters
        """
        try:
            # Get frontend URL from settings
            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
            
            # Forward all query parameters to frontend
            query_params = request.GET.urlencode()
            redirect_url = f"{frontend_url}/?{query_params}" if query_params else frontend_url
            
            logger.info(f"Microsoft OAuth callback - redirecting to frontend: {redirect_url}")
            
            return HttpResponseRedirect(redirect_url)
            
        except Exception as e:
            logger.error(f"OAuth callback redirect failed: {str(e)}", exc_info=True)
            # Fallback redirect to frontend root
            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
            return HttpResponseRedirect(f"{frontend_url}/?error=callback_error")
    
    def post(self, request) -> Response:
        """
        Process Microsoft OAuth callback and authenticate user.
        
        This endpoint exchanges the authorization code for tokens, validates
        the user's organization membership, assigns roles, and returns JWT tokens.
        
        Request Body:
        {
            "code": "oauth_authorization_code",
            "state": "csrf_protection_state"
        }
        
        Returns:
            Complete authentication response with user data and JWT tokens
        """
        try:
            # 1. Extract and validate request data
            auth_code = request.data.get('code')
            received_state = request.data.get('state')
            
            validation_result = self._validate_callback_request(auth_code, received_state, request)
            if not validation_result['valid']:
                return Response({
                    'success': False,
                    'error': validation_result['error'],
                    'error_type': 'validation_error'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 2. Exchange authorization code for tokens
            token_data = self._exchange_code_for_token(auth_code, request)
            if not token_data:
                return Response({
                    'success': False,
                    'error': 'Failed to exchange authorization code for tokens',
                    'error_type': 'token_exchange_error'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 3. Get user information from Microsoft Graph
            user_info = self._get_microsoft_user_info(token_data['access_token'])
            if not user_info:
                return Response({
                    'success': False,
                    'error': 'Failed to retrieve user information from Microsoft',
                    'error_type': 'user_info_error'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 4. Validate organization membership
            org_validation = self._validate_organization_user(user_info)
            if not org_validation.valid:
                return Response({
                    'success': False,
                    'error': org_validation.error_message,
                    'error_type': 'organization_validation_error'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # 5. Create or update Django user
            user, created = self._create_or_update_user(user_info, org_validation.user_data)
            
            # 6. Generate JWT tokens
            jwt_tokens = self._generate_jwt_tokens(user)
            
            # 7. Build comprehensive response
            response_data = self._build_authentication_response(
                user, org_validation.user_data, jwt_tokens, created
            )
            
            logger.info(f"Microsoft organization authentication successful for: {user.email}")
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except AzureAuthException as e:
            logger.error(f"Azure authentication failed: {str(e)}")
            return Response({
                'success': False,
                'error': str(e),
                'error_type': 'azure_auth_error',
                'auth_step': getattr(e, 'auth_step', 'unknown')
            }, status=status.HTTP_401_UNAUTHORIZED)
            
        except MicrosoftGraphException as e:
            logger.error(f"Microsoft Graph API error: {str(e)}")
            return Response({
                'success': False,
                'error': str(e),
                'error_type': 'graph_api_error'
            }, status=status.HTTP_502_BAD_GATEWAY)
            
        except Exception as e:
            logger.error(f"Microsoft organization callback failed: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': 'Authentication processing failed',
                'error_type': 'internal_error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _validate_callback_request(
        self, 
        auth_code: str, 
        received_state: str, 
        request
    ) -> Dict[str, Any]:
        """Validate OAuth callback request parameters."""
        if not auth_code:
            return {'valid': False, 'error': 'Missing authorization code'}
        
        if not received_state:
            return {'valid': False, 'error': 'Missing state parameter'}
        
        if not self._validate_oauth_state(request, received_state):
            return {'valid': False, 'error': 'Invalid state parameter - possible CSRF attack'}
        
        return {'valid': True}
    
    def _generate_jwt_tokens(self, user: User) -> Dict[str, Any]:
        """Generate JWT access and refresh tokens for the user."""
        refresh = RefreshToken.for_user(user)
        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'expires_in': refresh.access_token.lifetime.total_seconds()
        }
    
    def _build_authentication_response(
        self, 
        user: User, 
        org_data: Dict[str, Any], 
        jwt_tokens: Dict[str, Any],
        created: bool
    ) -> Dict[str, Any]:
        """Build comprehensive authentication response."""
        role_result = getattr(user, 'role_assignment_result', None)
        
        return {
            'success': True,
            'message': 'Microsoft organization authentication successful',
            'user_created': created,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'is_active': user.is_active,
                'date_joined': user.date_joined.isoformat() if hasattr(user, 'date_joined') else None
            },
            'role_info': {
                'role_name': role_result.role_config.role_name if role_result and role_result.success else 'User',
                'role_level': role_result.role_config.level.name if role_result and role_result.success else 'USER',
                'groups': role_result.groups if role_result and role_result.success else [],
                'assignment_reason': role_result.assignment_reason if role_result and role_result.success else 'default',
                'permissions': {
                    'can_access_admin': user.is_staff or user.is_superuser,
                    'can_manage_users': user.is_superuser,
                    'can_manage_content': user.is_staff or user.is_superuser,
                    'custom_permissions': list(role_result.role_config.permissions) if role_result and role_result.success else []
                }
            },
            'organization_info': {
                'display_name': org_data.get('displayName'),
                'job_title': org_data.get('jobTitle'),
                'department': org_data.get('department'),
                'office_location': org_data.get('officeLocation'),
                'account_enabled': org_data.get('accountEnabled', True),
            },
            'tokens': jwt_tokens,
            'authentication_method': 'microsoft_oauth',
            'tenant_id': settings.AZURE_TENANT_ID
        }


class OrganizationUserStatusView(APIView):
    """
    Check current organization user status and validate active membership.
    
    This view provides a health check endpoint for verifying that an authenticated
    user is still active in the Microsoft organization and their role assignments
    are current.
    
    Endpoint: GET /api/microsoft/auth/user-status/
    Authentication: Required (JWT token)
    """
    
    def get(self, request) -> Response:
        """
        Validate current user's organization status and role assignments.
        
        Args:
            request: Authenticated Django HTTP request
        
        Returns:
            User status information including organization membership and roles
        """
        if not request.user.is_authenticated:
            return Response({
                'success': False,
                'error': 'Authentication required',
                'error_type': 'authentication_required'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            # Check organization membership
            org_status = self._check_organization_membership(request.user.email)
            
            # Get current role assignment
            role_status = self._check_role_assignment(request.user.email)
            
            # Build status response
            status_data = {
                'success': True,
                'user_email': request.user.email,
                'organization_membership': org_status,
                'role_assignment': role_status,
                'last_checked': cache.get(f"status_check:{request.user.email}"),
                'django_user_status': {
                    'is_active': request.user.is_active,
                    'is_staff': request.user.is_staff,
                    'is_superuser': request.user.is_superuser,
                }
            }
            
            # Cache the status check timestamp
            cache.set(f"status_check:{request.user.email}", status_data, timeout=300)
            
            return Response(status_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"User status check failed for {request.user.email}: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': f'Status check failed: {str(e)}',
                'error_type': 'status_check_error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _check_organization_membership(self, user_email: str) -> Dict[str, Any]:
        """Check if user is still active in the organization."""
        try:
            mixin = GraphAPIBaseMixin()
            user_filter = f"mail eq '{user_email}' or userPrincipalName eq '{user_email}'"
            search_fields = 'id,displayName,accountEnabled,jobTitle,department,lastSignInDateTime'
            search_query = f"users?$filter={user_filter}&$select={search_fields}"
            
            users_response = mixin.call_graph_api(search_query)
            users = users_response.get('value', [])
            
            if not users:
                return {
                    'active': False,
                    'found': False,
                    'error': 'User not found in organization directory'
                }
            
            org_user = users[0]
            is_active = org_user.get('accountEnabled', False)
            
            return {
                'active': is_active,
                'found': True,
                'user_data': {
                    'display_name': org_user.get('displayName'),
                    'job_title': org_user.get('jobTitle'),
                    'department': org_user.get('department'),
                    'account_enabled': is_active,
                    'last_sign_in': org_user.get('lastSignInDateTime')
                }
            }
            
        except Exception as e:
            logger.error(f"Organization membership check failed for {user_email}: {str(e)}")
            return {
                'active': False,
                'found': False,
                'error': f'Membership check failed: {str(e)}'
            }
    
    def _check_role_assignment(self, user_email: str) -> Dict[str, Any]:
        """Check current role assignment for the user."""
        try:
            role_result = role_authenticator.get_user_role_from_microsoft(user_email)
            
            return {
                'success': role_result.success,
                'current_role': role_result.role_config.role_name if role_result.success else None,
                'current_groups': role_result.groups if role_result.success else [],
                'assignment_reason': role_result.assignment_reason if role_result.success else None,
                'error': role_result.error_message if not role_result.success else None
            }
            
        except Exception as e:
            logger.error(f"Role assignment check failed for {user_email}: {str(e)}")
            return {
                'success': False,
                'error': f'Role check failed: {str(e)}'
            }
