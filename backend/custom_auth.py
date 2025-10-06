from typing import Optional, TypeVar

from django.contrib.auth.models import AbstractBaseUser
from rest_framework import HTTP_HEADER_ENCODING
from rest_framework.request import Request

from rest_framework_simplejwt.models import TokenUser
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import Token
from rest_framework_simplejwt.authentication import JWTAuthentication as original_auth

AUTH_HEADER_TYPES = api_settings.AUTH_HEADER_TYPES

if not isinstance(api_settings.AUTH_HEADER_TYPES, (list, tuple)):
    AUTH_HEADER_TYPES = (AUTH_HEADER_TYPES,)

AUTH_HEADER_TYPE_BYTES: set[bytes] = {
    h.encode(HTTP_HEADER_ENCODING) for h in AUTH_HEADER_TYPES
}

AuthUser = TypeVar("AuthUser", AbstractBaseUser, TokenUser)


class JWTAuthentication(original_auth):
    """
    Custom JWT redefinition, read JWT token form cookie contents, not header. Everything else is automatically included from JWT
    """

    www_authenticate_realm = "api"
    media_type = "application/json"

    def authenticate(self, request: Request) -> Optional[tuple[AuthUser, Token]]:
        # Hybrid-Auth: Versuche zuerst Cookie, dann Authorization-Header
        raw_token = None
        
        # 1. Versuche Cookie (E-Learning-Style)
        cookie = request.COOKIES.get("access_token")
        if cookie:
            raw_token = cookie.encode(HTTP_HEADER_ENCODING)
        else:
            # 2. Fallback: Authorization-Header (DB-Overview-Style)
            header = self.get_header(request)
            if header:
                raw_token = self.get_raw_token(header)

        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)

        return self.get_user(validated_token), validated_token

    def get_header(self, request: Request) -> Optional[str]:
        """
        Extracts the header containing the JSON web token from the given
        request.
        """
        header = request.META.get(self.header_name)

        if isinstance(header, str):
            # Work around django test client oddness
            header = header.encode(HTTP_HEADER_ENCODING)

        return header

    def get_raw_token(self, header: bytes) -> Optional[bytes]:
        """
        Extracts an unvalidated JSON web token from the given "Authorization"
        header value.
        """
        parts = header.split()

        if len(parts) == 0:
            # Empty AUTHORIZATION header sent
            return None

        if parts[0].decode(HTTP_HEADER_ENCODING) not in AUTH_HEADER_TYPE_BYTES:
            # Assume the header does not contain a JSON web token
            return None

        if len(parts) != 2:
            return None

        return parts[1]
