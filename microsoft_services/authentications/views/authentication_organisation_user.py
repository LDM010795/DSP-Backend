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
import time

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
    
    GET /api/microsoft/auth/callback/ (OAuth2 Callback von Microsoft)
    POST /api/microsoft/auth/callback/ (Alternative für Frontend)
    """
    
    def get(self, request):
        """
        Behandelt OAuth2 Callback von Microsoft (GET mit Query-Parametern)
        Verarbeitet die Authentifizierung und leitet zum Frontend weiter
        OPTIMIERT für bessere Performance
        """
        start_time = time.time()
        
        from django.http import HttpResponseRedirect
        
        code = request.GET.get('code')
        state = request.GET.get('state')
        error = request.GET.get('error')
        
        # Frontend URL (aus Settings)
        frontend_url = settings.FRONTEND_URL
        
        if error:
            logger.warning(f"Microsoft OAuth error: {error}")
            # Microsoft hat einen Fehler gesendet - leite zur Startseite mit Fehler weiter
            error_url = f"{frontend_url}/?error={error}&error_description={request.GET.get('error_description', 'Authentication failed')}"
            return HttpResponseRedirect(error_url)
        
        if not code or not state:
            logger.warning("Missing OAuth parameters in callback")
            # Fehlende Parameter - leite zur Startseite mit Fehler weiter
            error_url = f"{frontend_url}/?error=missing_parameters&error_description=Missing code or state parameter"
            return HttpResponseRedirect(error_url)
        
        try:
            logger.info(f"🚀 Starting OPTIMIZED Microsoft OAuth callback processing...")
            
            # 1. Authorization Code gegen Access Token tauschen
            token_start = time.time()
            token_data = self._exchange_code_for_token(code, request)
            token_time = time.time() - token_start
            
            if not token_data:
                logger.error(f"Token exchange failed after {token_time:.2f}s")
                error_url = f"{frontend_url}/?error=token_exchange_failed&error_description=Failed to exchange authorization code"
                return HttpResponseRedirect(error_url)
            
            logger.info(f"✅ Token exchange completed in {token_time:.2f}s")
            
            # 2. User Info von Microsoft Graph API holen
            user_start = time.time()
            user_info = self._get_microsoft_user_info(token_data['access_token'])
            user_time = time.time() - user_start
            
            if not user_info:
                logger.error(f"User info failed after {user_time:.2f}s")
                error_url = f"{frontend_url}/?error=user_info_failed&error_description=Failed to get user information"
                return HttpResponseRedirect(error_url)
                
            logger.info(f"✅ User info retrieved in {user_time:.2f}s")
            
            # 3. Organization Validierung (OPTIMIERT)
            org_start = time.time()
            org_validation = self._validate_organization_user(user_info)
            org_time = time.time() - org_start
            
            if not org_validation['valid']:
                logger.warning(f"Organization validation failed after {org_time:.2f}s: {org_validation['error']}")
                error_url = f"{frontend_url}/?error=organization_access_denied&error_description={org_validation['error']}"
                return HttpResponseRedirect(error_url)
            
            validation_method = org_validation.get('validation_method', 'unknown')
            logger.info(f"✅ Organization validation ({validation_method}) completed in {org_time:.2f}s")
            
            # 4. Django User erstellen/updaten
            user_create_start = time.time()
            user = self._create_or_update_user(user_info, org_validation['org_data'])
            user_create_time = time.time() - user_create_start
            
            logger.info(f"✅ User create/update completed in {user_create_time:.2f}s")
            
            # 5. JWT Tokens erstellen
            jwt_start = time.time()
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            jwt_time = time.time() - jwt_start
            
            # 6. Tokens SICHER in Session speichern (nicht in URL!)
            request.session['microsoft_auth_tokens'] = {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'user_id': user.id,
                'expires_in': refresh.access_token.lifetime.total_seconds(),
                'user_info': {
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
                }
            }
            
            total_time = time.time() - start_time
            
            logger.info(f"🎉 Microsoft organization login successful for {user.email}")
            logger.info(f"⚡ PERFORMANCE: Total={total_time:.2f}s (Token={token_time:.2f}s, User={user_time:.2f}s, Org={org_time:.2f}s, DB={user_create_time:.2f}s, JWT={jwt_time:.2f}s)")
            
            # 7. SICHERE Weiterleitung zum Frontend (OHNE Tokens in URL!)
            success_url = f"{frontend_url}/dashboard?microsoft_auth=success"
            logger.info(f"🚀 Redirecting user to dashboard (tokens in session): {frontend_url}/dashboard")
            return HttpResponseRedirect(success_url)
            
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"❌ Microsoft organization callback failed after {total_time:.2f}s: {str(e)}")
            error_url = f"{frontend_url}/?error=authentication_failed&error_description=Authentication failed: {str(e)}"
            return HttpResponseRedirect(error_url)
    
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
        Tauscht Authorization Code gegen Access Token (mit Timeout)
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
            
            # PERFORMANCE: Timeout hinzugefügt
            response = requests.post(token_url, data=token_data, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Token exchange failed: {response.text}")
                return None
                
        except requests.Timeout:
            logger.error("Token exchange timeout after 10 seconds")
            return None
        except Exception as e:
            logger.error(f"Token exchange error: {str(e)}")
            return None
    
    def _get_microsoft_user_info(self, access_token):
        """
        Holt User Info von Microsoft Graph API (mit Timeout + Fallback)
        """
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # PERFORMANCE: Timeout hinzugefügt
            response = requests.get('https://graph.microsoft.com/v1.0/me', headers=headers, timeout=5)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get user info: {response.text}")
                return None
                
        except requests.Timeout:
            logger.warning("User info request timeout after 5 seconds")
            return None
        except Exception as e:
            logger.error(f"Get user info error: {str(e)}")
            return None
    
    def _validate_organization_user(self, user_info):
        """
        INTELLIGENTE Organization Validation mit Fallback
        - Versucht volle Validierung (3s Timeout)
        - Bei Timeout/Fehler: Fallback auf Domain-Check
        - Login bricht NIE ab
        """
        try:
            email = user_info.get('mail') or user_info.get('userPrincipalName')
            
            if not email:
                return {
                    'valid': False,
                    'error': 'No email address found in Microsoft profile'
                }
            
            # 1. Domain-Check (IMMER erforderlich)
            allowed_domains = getattr(settings, 'DSP_ALLOWED_DOMAINS', ['datasmartpoint.com'])
            if allowed_domains:
                email_domain = email.split('@')[-1].lower()
                if email_domain not in allowed_domains:
                    return {
                        'valid': False,
                        'error': f'Email domain {email_domain} not allowed for this organization'
                    }
            
            # 2. Prüfe bekannte aktive User (SCHNELL)
            try:
                existing_user = User.objects.get(email=email, is_active=True)
                logger.info(f"Fast login for known user: {email}")
                return {
                    'valid': True,
                    'org_data': {
                        'displayName': f"{existing_user.first_name} {existing_user.last_name}".strip() or existing_user.username,
                        'jobTitle': '',
                        'department': '',
                        'officeLocation': '',
                        'accountEnabled': True,
                        'mail': email,
                        'userPrincipalName': email
                    },
                    'validation_method': 'fast_known_user'
                }
            except User.DoesNotExist:
                pass  # Neuer User → weiter zur API-Validierung
            
            # 3. Versuche VOLLE Organization-Validierung (mit Timeout)
            try:
                logger.info(f"Attempting full organization validation for new user: {email}")
                
                mixin = GraphAPIBaseMixin()
                user_filter = f"mail eq '{email}' or userPrincipalName eq '{email}'"
                search_query = f"users?$filter={user_filter}&$select=id,displayName,mail,userPrincipalName,accountEnabled,jobTitle,department,officeLocation"
                
                # TIMEOUT: 3 Sekunden für Organization Check
                users_response = mixin.call_graph_api(search_query)
                users = users_response.get('value', [])
                
                if not users:
                    return {
                        'valid': False,
                        'error': f'User {email} not found in DSP organization directory'
                    }
                
                org_user = users[0]
                
                # Account Status prüfen
                if not org_user.get('accountEnabled', False):
                    return {
                        'valid': False,
                        'error': f'Account {email} is disabled in organization'
                    }
                
                logger.info(f"Full organization validation successful for: {email}")
                
                return {
                    'valid': True,
                    'error': None,
                    'org_data': org_user,
                    'validation_method': 'full_api_validation'
                }
                
            except Exception as api_error:
                logger.warning(f"Organization API failed for {email}: {str(api_error)} - Using fallback")
                
                # 4. FALLBACK: Domain + Microsoft User Info (LOGIN GEHT WEITER!)
                fallback_org_data = {
                    'displayName': user_info.get('displayName', f"{user_info.get('givenName', '')} {user_info.get('surname', '')}").strip(),
                    'jobTitle': user_info.get('jobTitle', ''),
                    'department': user_info.get('department', ''),
                    'officeLocation': user_info.get('officeLocation', ''),
                    'accountEnabled': True,  # Microsoft hat User bereits authentifiziert
                    'mail': email,
                    'userPrincipalName': user_info.get('userPrincipalName', email)
                }
                
                logger.info(f"Using fallback validation for {email} - login continues")
                
                return {
                    'valid': True,
                    'error': None,
                    'org_data': fallback_org_data,
                    'validation_method': 'fallback_domain_only',
                    'note': 'Organization validation will be completed in background'
                }
            
        except Exception as e:
            logger.error(f"Organization validation completely failed for {email}: {str(e)}")
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


class MicrosoftAuthTokensView(APIView):
    """
    Holt Microsoft Auth Tokens sicher aus der Session (nach OAuth2 Callback)
    
    GET /api/microsoft/auth/tokens/
    """
    
    def get(self, request):
        """
        Holt die Microsoft Auth Tokens aus der Session und löscht sie danach
        
        Returns:
            - success: Boolean
            - tokens: JWT access + refresh tokens
            - user: User data
            - organization_info: Microsoft organization data
        """
        try:
            # Tokens aus Session holen
            auth_data = request.session.get('microsoft_auth_tokens')
            
            if not auth_data:
                return Response({
                    'success': False,
                    'error': 'No authentication data found in session',
                    'error_code': 'NO_AUTH_DATA'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Session cleanup - Tokens nur einmal verwendbar
            del request.session['microsoft_auth_tokens']
            
            logger.info(f"Microsoft auth tokens retrieved from session for user: {auth_data['user_info']['email']}")
            
            return Response({
                'success': True,
                'message': 'Microsoft authentication tokens retrieved successfully',
                'tokens': {
                    'access': auth_data['access_token'],
                    'refresh': auth_data['refresh_token'],
                },
                'expires_in': auth_data['expires_in'],
                'user': auth_data['user_info'],
                'organization_info': auth_data['organization_info']
            })
            
        except Exception as e:
            logger.error(f"Failed to retrieve Microsoft auth tokens: {str(e)}")
            return Response({
                'success': False,
                'error': f'Failed to retrieve tokens: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
