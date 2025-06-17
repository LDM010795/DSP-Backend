"""
Microsoft Organization User Authentication API

Diese API authentifiziert Benutzer gegen die Microsoft Organization
und prüft, ob sie aktive Accounts in der DSP Organization haben.

Flow:
1. Frontend → GET /api/microsoft/auth/login/ → Redirect URL
2. User loggt sich bei Microsoft ein
3. Microsoft → Callback mit Code
4. Backend → POST /api/microsoft/auth/callback/ → User + JWT Token
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model, login
from django.conf import settings
from microsoft_services.core_integrations.mixins import GraphAPIBaseMixin
from microsoft_services.core_integrations.token_manager import azure_token_manager
import requests
import secrets
import logging
from urllib.parse import urlencode

logger = logging.getLogger(__name__)
User = get_user_model()

class MicrosoftOrganizationLoginView(APIView):
    """
    Startet Microsoft OAuth2 Login Flow für Organization Users
    
    GET /api/microsoft/auth/login/
    """
    
    def get(self, request):
        """
        Erstellt Microsoft OAuth2 Login URL für Organisation
        
        Returns:
            - redirect_url: Microsoft Login URL
            - state: Security State Parameter
        """
        try:
            # 1. State Parameter für Security erstellen
            state = secrets.token_urlsafe(32)
            request.session['oauth_state'] = state
            
            # 2. Redirect URL nach Login
            redirect_uri = request.build_absolute_uri('/api/microsoft/auth/callback/')
            
            # 3. Microsoft OAuth2 Parameters
            oauth_params = {
                'client_id': settings.AZURE_CLIENT_ID,
                'response_type': 'code',
                'redirect_uri': redirect_uri,
                'scope': 'openid email profile User.Read Directory.Read.All',
                'state': state,
                'response_mode': 'query',
                # WICHTIG: Nur Organisation-Accounts erlauben
                'prompt': 'select_account',
            }
            
            # 4. Microsoft Authorization URL (Tenant-spezifisch)
            tenant_id = settings.AZURE_TENANT_ID
            auth_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize"
            full_auth_url = f"{auth_url}?{urlencode(oauth_params)}"
            
            logger.info(f"Generated Microsoft OAuth URL for organization login")
            
            return Response({
                'success': True,
                'message': 'Microsoft organization login URL generated',
                'redirect_url': full_auth_url,
                'state': state,
                'instructions': [
                    'Redirect user to redirect_url',
                    'User will login with their DSP Microsoft account',
                    'Microsoft will redirect back to /api/microsoft/auth/callback/',
                    'Frontend should handle the callback'
                ]
            })
            
        except Exception as e:
            logger.error(f"Failed to generate Microsoft login URL: {str(e)}")
            return Response({
                'success': False,
                'error': f'Failed to generate login URL: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MicrosoftOrganizationCallbackView(APIView):
    """
    Verarbeitet Microsoft OAuth2 Callback und validiert Organization User
    
    POST /api/microsoft/auth/callback/
    """
    
    def post(self, request):
        """
        Verarbeitet Microsoft OAuth2 Callback
        
        Expected POST data:
        {
            "code": "OAuth2 authorization code",
            "state": "Security state parameter"
        }
        
        Returns:
            - success: Boolean
            - user: User data
            - tokens: JWT access + refresh tokens
            - organization_info: Microsoft organization data
        """
        try:
            # 1. Input validieren
            auth_code = request.data.get('code')
            state = request.data.get('state')
            
            if not auth_code:
                return Response({
                    'success': False,
                    'error': 'Authorization code missing'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 2. State validieren (Security)
            session_state = request.session.get('oauth_state')
            if not session_state or session_state != state:
                logger.warning("OAuth state mismatch - possible CSRF attack")
                return Response({
                    'success': False,
                    'error': 'Invalid state parameter'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 3. Authorization Code gegen Access Token tauschen
            token_data = self._exchange_code_for_token(auth_code, request)
            if not token_data:
                return Response({
                    'success': False,
                    'error': 'Failed to exchange authorization code'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 4. User Info von Microsoft Graph API holen
            user_info = self._get_microsoft_user_info(token_data['access_token'])
            if not user_info:
                return Response({
                    'success': False,
                    'error': 'Failed to get user information'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 5. Organization Validierung
            org_validation = self._validate_organization_user(user_info)
            if not org_validation['valid']:
                return Response({
                    'success': False,
                    'error': org_validation['error'],
                    'error_code': 'ORGANIZATION_ACCESS_DENIED'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # 6. Django User erstellen/updaten
            user = self._create_or_update_user(user_info, org_validation['org_data'])
            
            # 7. JWT Tokens erstellen
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            
            # 8. Session cleanup
            request.session.pop('oauth_state', None)
            
            logger.info(f"Microsoft organization login successful for user: {user.email}")
            
            return Response({
                'success': True,
                'message': 'Microsoft organization login successful',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'is_staff': user.is_staff,
                    'is_superuser': user.is_superuser,
                },
                'organization_info': {
                    'display_name': org_validation['org_data'].get('displayName'),
                    'job_title': org_validation['org_data'].get('jobTitle'),
                    'department': org_validation['org_data'].get('department'),
                    'office_location': org_validation['org_data'].get('officeLocation'),
                    'account_enabled': org_validation['org_data'].get('accountEnabled'),
                },
                'tokens': {
                    'access': str(access_token),
                    'refresh': str(refresh),
                },
                'expires_in': access_token.lifetime.total_seconds()
            })
            
        except Exception as e:
            logger.error(f"Microsoft organization callback failed: {str(e)}")
            return Response({
                'success': False,
                'error': f'Authentication failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _exchange_code_for_token(self, auth_code, request):
        """
        Tauscht Authorization Code gegen Access Token
        """
        try:
            token_url = f"https://login.microsoftonline.com/{settings.AZURE_TENANT_ID}/oauth2/v2.0/token"
            
            token_data = {
                'client_id': settings.AZURE_CLIENT_ID,
                'client_secret': settings.AZURE_CLIENT_SECRET,
                'code': auth_code,
                'grant_type': 'authorization_code',
                'redirect_uri': request.build_absolute_uri('/api/microsoft/auth/callback/'),
                'scope': 'openid email profile User.Read Directory.Read.All'
            }
            
            response = requests.post(token_url, data=token_data)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Token exchange failed: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Token exchange error: {str(e)}")
            return None
    
    def _get_microsoft_user_info(self, access_token):
        """
        Holt User Info von Microsoft Graph API
        """
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # User Profile von Graph API
            response = requests.get('https://graph.microsoft.com/v1.0/me', headers=headers)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get user info: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Get user info error: {str(e)}")
            return None
    
    def _validate_organization_user(self, user_info):
        """
        Validiert ob User aktiv in der DSP Organization ist
        
        Returns:
            {
                'valid': True/False,
                'error': 'Error message if invalid',
                'org_data': 'Organization user data'
            }
        """
        try:
            email = user_info.get('mail') or user_info.get('userPrincipalName')
            
            if not email:
                return {
                    'valid': False,
                    'error': 'No email address found in Microsoft profile'
                }
            
            # 1. Email Domain Check (optional)
            allowed_domains = getattr(settings, 'DSP_ALLOWED_DOMAINS', [])
            if allowed_domains:
                email_domain = email.split('@')[-1].lower()
                if email_domain not in allowed_domains:
                    return {
                        'valid': False,
                        'error': f'Email domain {email_domain} not allowed for this organization'
                    }
            
            # 2. Organization User Check über Graph API (Application Token)
            mixin = GraphAPIBaseMixin()
            
            # User in Organization suchen
            user_filter = f"mail eq '{email}' or userPrincipalName eq '{email}'"
            search_query = f"users?$filter={user_filter}&$select=id,displayName,mail,userPrincipalName,accountEnabled,jobTitle,department,officeLocation"
            
            users_response = mixin.call_graph_api(search_query)
            users = users_response.get('value', [])
            
            if not users:
                return {
                    'valid': False,
                    'error': f'User {email} not found in DSP organization directory'
                }
            
            org_user = users[0]
            
            # 3. Account Status prüfen
            if not org_user.get('accountEnabled', False):
                return {
                    'valid': False,
                    'error': f'Account {email} is disabled in organization'
                }
            
            logger.info(f"Organization validation successful for: {email}")
            
            return {
                'valid': True,
                'error': None,
                'org_data': org_user
            }
            
        except Exception as e:
            logger.error(f"Organization validation error: {str(e)}")
            return {
                'valid': False,
                'error': f'Organization validation failed: {str(e)}'
            }
    
    def _create_or_update_user(self, user_info, org_data):
        """
        Erstellt oder aktualisiert Django User basierend auf Microsoft Daten
        """
        email = user_info.get('mail') or user_info.get('userPrincipalName')
        
        # User suchen oder erstellen
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': email,
                'first_name': user_info.get('givenName', ''),
                'last_name': user_info.get('surname', ''),
                'is_active': True,
            }
        )
        
        # User Daten aktualisieren
        user.first_name = user_info.get('givenName', user.first_name)
        user.last_name = user_info.get('surname', user.last_name)
        user.is_active = org_data.get('accountEnabled', True)
        
        # Berechtigungen basierend auf Job Title setzen
        job_title = org_data.get('jobTitle', '').lower()
        department = org_data.get('department', '').lower()
        
        # Admin-Rechte für bestimmte Rollen
        admin_keywords = ['ceo', 'cto', 'geschäftsführer', 'leiter', 'director', 'admin']
        is_admin = any(keyword in job_title for keyword in admin_keywords)
        
        # Staff-Rechte für bestimmte Departments
        staff_departments = ['it', 'management', 'verwaltung', 'hr']
        is_staff = any(dept in department for dept in staff_departments) or is_admin
        
        user.is_staff = is_staff
        user.is_superuser = is_admin
        
        user.save()
        
        if created:
            logger.info(f"Created new user from Microsoft organization: {email}")
        else:
            logger.info(f"Updated existing user from Microsoft organization: {email}")
        
        return user


class OrganizationUserStatusView(APIView):
    """
    Prüft den aktuellen Status eines Organization Users
    
    GET /api/microsoft/auth/user-status/
    """
    
    def get(self, request):
        """
        Prüft ob der aktuelle User noch aktiv in der Organization ist
        """
        if not request.user.is_authenticated:
            return Response({
                'success': False,
                'error': 'User not authenticated'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            # User in Organization prüfen
            mixin = GraphAPIBaseMixin()
            user_filter = f"mail eq '{request.user.email}' or userPrincipalName eq '{request.user.email}'"
            search_query = f"users?$filter={user_filter}&$select=id,displayName,accountEnabled,jobTitle,department"
            
            users_response = mixin.call_graph_api(search_query)
            users = users_response.get('value', [])
            
            if not users:
                return Response({
                    'success': False,
                    'active': False,
                    'error': 'User not found in organization'
                }, status=status.HTTP_404_NOT_FOUND)
            
            org_user = users[0]
            is_active = org_user.get('accountEnabled', False)
            
            return Response({
                'success': True,
                'active': is_active,
                'user': {
                    'email': request.user.email,
                    'display_name': org_user.get('displayName'),
                    'job_title': org_user.get('jobTitle'),
                    'department': org_user.get('department'),
                    'account_enabled': is_active
                }
            })
            
        except Exception as e:
            logger.error(f"User status check failed: {str(e)}")
            return Response({
                'success': False,
                'error': f'Status check failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
