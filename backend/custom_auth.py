from typing import Optional, TypeVar

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser
from django.utils.translation import gettext_lazy as _
from rest_framework import HTTP_HEADER_ENCODING, authentication
from rest_framework.request import Request

from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken, TokenError
from rest_framework_simplejwt.models import TokenUser
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import Token
from rest_framework_simplejwt.utils import get_md5_hash_password
from rest_framework_simplejwt.authentication import JWTAuthentication as origial_auth

AUTH_HEADER_TYPES = api_settings.AUTH_HEADER_TYPES

if not isinstance(api_settings.AUTH_HEADER_TYPES, (list, tuple)):
    AUTH_HEADER_TYPES = (AUTH_HEADER_TYPES,)

AUTH_HEADER_TYPE_BYTES: set[bytes] = {
    h.encode(HTTP_HEADER_ENCODING) for h in AUTH_HEADER_TYPES
}

AuthUser = TypeVar("AuthUser", AbstractBaseUser, TokenUser)

class JWTAuthentication(origial_auth):
    """
    Custom JWT redefinition, read JWT token form cookie contents, not header. Everything else is automatically included from JWT
    """

    www_authenticate_realm = "api"
    media_type = "application/json"


    def authenticate(self, request: Request) -> Optional[tuple[AuthUser, Token]]:
        cookie = request.COOKIES.get("access_token") or None
        if cookie is None:
            return None

        raw_token = cookie.encode(HTTP_HEADER_ENCODING)

        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)

        return self.get_user(validated_token), validated_token
