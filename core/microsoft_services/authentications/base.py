"""
Base Module for Microsoft Authentication

This module provides the core, reusable client for interacting with the
Microsoft Identity Platform (OAuth 2.0 and Graph API). It is designed to be
application-agnostic and should not contain any business logic specific to
employees, customers, or other user types.

Key Responsibilities:
- Building OAuth authorization URLs.
- Exchanging authorization codes for access tokens.
- Retrieving user profiles from Microsoft Graph.
- Centralized error handling for Microsoft APIs.

Author: DSP Development Team
Version: 2.0.0 (Refactored)
"""

import logging
import requests
from typing import Dict, Any
from urllib.parse import urlencode
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from core.microsoft_services.core_integrations.exceptions import (
    AzureAuthException,
    MicrosoftGraphException,
)

logger = logging.getLogger(__name__)


class MicrosoftAuthClient:
    """
    A client for handling the OAuth 2.0 flow with Microsoft Identity Platform.
    """

    OAUTH_SCOPE = "openid email profile User.Read"
    TOKEN_URL_TEMPLATE = (
        "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    )
    AUTH_URL_TEMPLATE = (
        "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize"
    )
    GRAPH_USER_URL = "https://graph.microsoft.com/v1.0/me"

    def __init__(self):
        self.client_id = settings.AZURE_CLIENT_ID
        self.client_secret = settings.AZURE_CLIENT_SECRET
        self.tenant_id = settings.AZURE_TENANT_ID
        if not all([self.client_id, self.client_secret, self.tenant_id]):
            raise ImproperlyConfigured(
                "Azure AD settings (CLIENT_ID, CLIENT_SECRET, TENANT_ID) must be configured."
            )

    def build_authorization_url(self, request, state: str, redirect_uri: str) -> str:
        """Builds the full authorization URL to redirect the user to Microsoft."""
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": self.OAUTH_SCOPE,
            "state": state,
            "response_mode": "query",
        }
        auth_url = self.AUTH_URL_TEMPLATE.format(tenant_id=self.tenant_id)
        return f"{auth_url}?{urlencode(params)}"

    def exchange_code_for_token(
        self, auth_code: str, redirect_uri: str
    ) -> Dict[str, Any]:
        """Exchanges an authorization code for an access token."""
        token_url = self.TOKEN_URL_TEMPLATE.format(tenant_id=self.tenant_id)
        token_data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": auth_code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }

        try:
            logger.debug("Exchanging authorization code for access token.")
            response = requests.post(
                token_url, data=token_data, headers=headers, timeout=30
            )
            response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)

            token_response = response.json()
            if "access_token" not in token_response:
                raise AzureAuthException(
                    "Invalid token response: 'access_token' missing.",
                    auth_step="token_validation",
                )
            logger.info("Successfully exchanged authorization code for access token.")
            return token_response

        except requests.exceptions.HTTPError as e:
            error_data = e.response.json() if e.response.content else {}
            error_msg = error_data.get("error_description", str(e))
            logger.error(
                f"Token exchange failed: {e.response.status_code} - {error_msg}"
            )
            raise AzureAuthException(
                f"Token exchange failed: {error_msg}", auth_step="token_exchange"
            ) from e
        except requests.exceptions.RequestException as e:
            logger.error(f"Token exchange request failed: {e}")
            raise AzureAuthException(
                f"Token exchange request failed: {e}", auth_step="request_error"
            ) from e

    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Retrieves user information from the Microsoft Graph API."""
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        user_fields = "id,displayName,mail,userPrincipalName,givenName,surname"

        try:
            logger.debug("Retrieving user info from Microsoft Graph.")
            response = requests.get(
                f"{self.GRAPH_USER_URL}?$select={user_fields}",
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()

            user_data = response.json()
            logger.debug(
                f"Retrieved user info for: {user_data.get('mail') or user_data.get('userPrincipalName')}"
            )
            return user_data

        except requests.exceptions.HTTPError as e:
            error_data = e.response.json() if e.response.content else {}
            error_msg = error_data.get("error", {}).get("message", str(e))
            logger.error(
                f"Failed to get user info: {e.response.status_code} - {error_msg}"
            )
            raise MicrosoftGraphException(
                f"Failed to retrieve user information: {error_msg}",
                status_code=e.response.status_code,
            ) from e
        except requests.exceptions.RequestException as e:
            logger.error(f"User info request failed: {e}")
            raise MicrosoftGraphException(f"User info request failed: {e}") from e
