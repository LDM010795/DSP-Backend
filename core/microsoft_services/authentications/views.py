"""
Main Views for Microsoft Authentication

This module provides the public-facing API endpoints for the authentication flow.
It acts as a conductor, orchestrating calls to the MicrosoftAuthClient for
OAuth interactions and to the appropriate business logic handler for user
validation and processing.

The views are designed to be slim and delegate all heavy lifting to other
components, adhering to the principle of separation of concerns.

Author: DSP Development Team
Version: 2.1.0 (Refactored & Corrected)
"""
import logging
import secrets
from urllib.parse import urlencode

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponseRedirect
from django.core.cache import cache
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings

from core.employees.models import Tool
from .base import MicrosoftAuthClient
from .handlers import EmployeeAuthHandler, get_redirect_url
from ..core_integrations.exceptions import AzureAuthException, MicrosoftGraphException

logger = logging.getLogger(__name__)

# This is the single, backend redirect URI registered in Azure AD
CALLBACK_PATH = "/api/microsoft/auth/callback/"


class MicrosoftLoginRedirectView(APIView):
    """
    Initiates the Microsoft OAuth 2.0 login flow for a specific tool.
    Redirects the user to the Microsoft login page.
    """

    def get(self, request, tool_slug: str, *args, **kwargs):
        try:
            Tool.objects.get(slug=tool_slug, is_active=True)
        except Tool.DoesNotExist:
            return Response(
                {"error": f"Tool '{tool_slug}' not found or is inactive."},
                status=status.HTTP_404_NOT_FOUND,
            )

        state = secrets.token_urlsafe(32)
        # We store the tool_slug against the state to remember which tool started the flow
        cache.set(f"oauth_state_{state}", tool_slug, timeout=600)

        client = MicrosoftAuthClient()
        redirect_uri = request.build_absolute_uri(CALLBACK_PATH)

        # Azure AD often requires 'localhost' for development, not '127.0.0.1'.
        # We must ensure the redirect URI exactly matches what's configured in Azure.
        if "127.0.0.1" in redirect_uri:
            redirect_uri = redirect_uri.replace("127.0.0.1", "localhost")
        
        auth_url = client.build_authorization_url(
            request, state=state, redirect_uri=redirect_uri
        )
        
        return HttpResponseRedirect(auth_url)


class MicrosoftCallbackView(APIView):
    """
    Handles both the initial redirect from Microsoft and the subsequent
    token exchange request from the frontend SPA.
    """

    def get(self, request, *args, **kwargs):
        """
        Handles the redirect from Microsoft. This view is just a passthrough.
        It retrieves the tool's frontend URL from the cached state and redirects
        the user's browser there, passing along the `code` and `state` parameters.
        """
        state = request.GET.get("state")
        if not state:
            return Response({"error": "No state found in callback. Cannot proceed."}, status=status.HTTP_400_BAD_REQUEST)

        tool_slug = cache.get(f"oauth_state_{state}")
        if not tool_slug:
            return Response({"error": "Invalid or expired state. Please try logging in again."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            tool = Tool.objects.get(slug=tool_slug, is_active=True)
            # Forward all query params from Microsoft to the frontend
            query_params = request.GET.urlencode()
            
            # Use the new get_redirect_url function for dynamic frontend URL
            frontend_url = get_redirect_url(request)
            redirect_url = f"{frontend_url}?{query_params}"
            
            logger.info(f"Redirecting user to frontend for tool '{tool_slug}': {redirect_url}")
            return HttpResponseRedirect(redirect_url)
        except Tool.DoesNotExist:
            logger.warning(f"Tool with slug '{tool_slug}' not found after Microsoft callback.")
            return Response({"error": "Tool configured for this login does not exist."}, status=status.HTTP_404_NOT_FOUND)


    def post(self, request, tool_slug: str, *args, **kwargs):
        """
        Handles the secure, server-to-server token exchange, initiated by the frontend.
        The frontend sends the `code` it received, and this view returns JWTs.
        """
        auth_code = request.data.get("code")
        state = request.data.get("state")
        
        if not all([auth_code, state]):
            return Response({"error": "Missing 'code' or 'state' in request body."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify that the tool from the URL matches the one stored in the state
        cached_tool_slug = cache.get(f"oauth_state_{state}")
        if not cached_tool_slug or cached_tool_slug != tool_slug:
            return Response({"error": "State-Tool mismatch or expired state."}, status=status.HTTP_400_BAD_REQUEST)
        
        cache.delete(f"oauth_state_{state}")

        try:
            tool = Tool.objects.get(slug=tool_slug, is_active=True)
            client = MicrosoftAuthClient()
            redirect_uri = request.build_absolute_uri(CALLBACK_PATH)
            
            # Ensure consistency for the token exchange redirect URI
            if "127.0.0.1" in redirect_uri:
                redirect_uri = redirect_uri.replace("127.0.0.1", "localhost")

            token_data = client.exchange_code_for_token(auth_code, redirect_uri)
            user_info = client.get_user_info(token_data["access_token"])

            handler = EmployeeAuthHandler()
            auth_response_data = handler.handle_authentication(user_info, tool)
            
            return Response(auth_response_data)

        except (AzureAuthException, MicrosoftGraphException, ValueError, PermissionError) as e:
            logger.error(f"Authentication failed for tool '{tool_slug}': {e}")
            return Response({"success": False, "error": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except Tool.DoesNotExist:
             return Response({"error": f"Tool '{tool_slug}' not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.exception(f"An unexpected error occurred during authentication postback: {e}")
            return Response({"error": "An unexpected server error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MicrosoftLogoutView(APIView):
    """Logs out user by blacklisting refresh token (JWT)"""

    def post(self, request, *args, **kwargs):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"error": "No refresh token provided."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()

            # Prepare optional Azure logout URL
            azure_logout = "https://login.microsoftonline.com/common/oauth2/v2.0/logout"
            post_logout = request.data.get("post_logout_redirect_uri") or get_redirect_url(request)
            logout_url = f"{azure_logout}?post_logout_redirect_uri={post_logout}"

            response = Response({"success": True, "logout_url": logout_url})
            # Remove Django session cookie if present
            response.delete_cookie(settings.SESSION_COOKIE_NAME, path="/")
            return response
        except Exception as e:
            logger.error(f"Logout failed: {e}")
            return Response({"error": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)
