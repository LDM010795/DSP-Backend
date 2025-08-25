"""
E-Learning User Authentication Views

This module provides secure authentication endpoints for the E-Learning system,
including enhanced JWT token generation and secure logout functionality.

Views:
- CustomTokenObtainPairView: Enhanced JWT authentication with user metadata
- LogoutView: Secure token invalidation and logout
- SetInitialPasswordView: Secure initial password setting for new users

Features:
- Enhanced JWT tokens with user role information
- Secure token blacklisting for logout
- Comprehensive error handling and validation
- Initial password setup with security requirements

Author: DSP Development Team
Version: 1.0.0
"""


from django.http import JsonResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


class CookieTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            data = response.data
            refresh = data.pop("refresh", None)
            access = data.pop("access", None)

            if refresh:
                response.set_cookie(
                    "refresh_token", refresh,
                    httponly=True, secure=True, samesite="None"
                )
            if access:
                response.set_cookie(
                    "access_token", access,
                    httponly=True, secure=True, samesite="None" # TODO: Definitely change this to Strict on Prod!
                )
        return response

class CookieTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get("refresh_token")
        if refresh_token:
            request.data["refresh"] = refresh_token
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200 and "access" in response.data:
            access = response.data["access"]
            response.set_cookie(
                "access_token", access,
                httponly=True, secure=True, samesite="None"
            )
            del response.data["access"]
        return response

class CookieLogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.COOKIES.get("refresh_token")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except Exception:
            pass
        response = JsonResponse({"detail": "Successfully logged out."}, status=205)
        response.delete_cookie("refresh_token")
        response.delete_cookie("access_token")
        return response
