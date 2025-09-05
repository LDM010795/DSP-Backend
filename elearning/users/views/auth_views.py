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
from django.utils.translation import gettext_lazy as _
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from djstripe.models import Customer

from backend.settings import SIMPLE_JWT
from ..models import Profile
from ..serializers import (
    SetInitialPasswordSerializer,
    ExternalUserRegistrationSerializer,
)


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom view extending SimpleJWT's TokenObtainPairView to store JWT tokens in secure HTTP-only cookies
    instead of returning them in the response body.
    - Calls the parent class's `post` method to get access/refresh tokens.
    - Removes tokens from the response payload to avoid exposing them in JSON.
    - Sets `refresh_token` and `access_token` cookies with secure flags:
     * httponly=True → prevents JavaScript access (mitigates XSS attacks)
     * secure=True → transmits cookies only over HTTPS
     * samesite="None" → required for cross-site requests; should be "Strict" or "Lax" in production
    """

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            data = response.data
            refresh = data.pop("refresh", None)
            access = data.pop("access", None)

            if refresh:
                response.set_cookie(
                    "refresh_token",
                    refresh,
                    httponly=True,
                    secure=True,
                    samesite="None",
                    path="/",
                    max_age=SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"],
                )
            if access:
                response.set_cookie(
                    "access_token",
                    access,
                    httponly=True,
                    secure=True,
                    samesite="None",  # TODO: Definitely change this to Strict on Prod!
                    path="/",
                    max_age=SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"],
                )
        return response


class CustomTokenRefreshView(TokenRefreshView):
    """
    Custom view extending SimpleJWT's TokenRefreshView to refresh JWT tokens and store them
    in secure HTTP-only cookies instead of returning them in the response body.
    - Calls the parent class's `post` method to generate new access/refresh tokens.
    - Removes tokens from the response payload.
    - Updates `refresh_token` and `access_token` cookies with secure flags.
    """

    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get("refresh_token")
        if not refresh_token:
            return Response(
                {"detail": "Refresh token not provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = TokenRefreshSerializer(data={"refresh": refresh_token})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        refresh = data.pop("refresh", None)
        access = data.pop("access", None)

        response = Response(status=status.HTTP_200_OK)

        if refresh:
            response.set_cookie(
                "refresh_token", refresh, httponly=True, secure=True, samesite="None"
            )
        if access:
            response.set_cookie(
                "access_token",
                access,
                httponly=True,
                secure=True,
                samesite="None",  # switch to Strict in prod
            )

        return response


class LogoutView(APIView):
    """
    API endpoint to handle user logout by invalidating JWT tokens and clearing cookies.
    - Requires authentication (IsAuthenticated).
    - On POST:
      * Attempts to retrieve the refresh token from cookies.
      * If present, constructs a RefreshToken instance and blacklists it.
      * Any errors during token invalidation are silently ignored.
    - Always returns a 205 Reset Content response with a success message.
    - Deletes both "refresh_token" and "access_token" cookies from the client to complete logout.
    """

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


class SetInitialPasswordView(APIView):
    """
    Secure initial password setting view for new users.

    Handles the initial password setup process for users who are required
    to change their password on first login, ensuring security compliance
    and proper profile management.

    Security Features:
    - Password strength validation
    - Confirmation matching validation
    - Profile-based access control
    - Automatic profile update after successful password change
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        """
        Set initial password for authenticated user.

        Args:
            request: HTTP request containing new password data

        Returns:
            Response indicating password change success or failure

        Expected Request Data:
            - password: New password (minimum 8 characters)
            - password_confirm: Password confirmation

        Security Requirements:
            - User must be authenticated
            - User profile must have force_password_change=True
            - Password must meet Django's validation requirements
        """
        user = request.user

        try:
            # Check if user is required to change password
            if not user.profile.force_password_change:
                return Response(
                    {"detail": _("Password has already been set.")},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Profile.DoesNotExist:
            # Create missing profile
            Profile.objects.create(user=user, force_password_change=True)

        # Validate and process password change
        serializer = SetInitialPasswordSerializer(data=request.data)
        if serializer.is_valid():
            try:
                # Use serializer's save method for comprehensive handling
                updated_user = serializer.save(user)

                # Log successful password change
                # Could add audit logging here

                return Response(
                    {"detail": _("Password successfully set.")},
                    status=status.HTTP_200_OK,
                )

            except Exception:
                return Response(
                    {"detail": _("An error occurred while setting the password.")},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ExternalUserRegistrationView(generics.CreateAPIView):
    """
    API endpoint for the registration of external users
    (i.e., users who are not part of the company and do not have a Microsoft account).

    Features:
    - Accepts POST requests with registration data (username, email, password, etc.).
    - Uses the ExternalUserRegistrationSerializer for data validation and user creation.
    - Returns a success message and HTTP 201 status on successful registration.
    - Returns detailed validation errors and HTTP 400 status if registration fails.

    Typical Use Case:
    This endpoint allows people outside the company to sign up for access to the e-learning platform,
    enabling self-service onboarding and payment in the future.

    Methods:
        post(request): Handles the registration logic for incoming data.
    """

    serializer_class = ExternalUserRegistrationSerializer
    permission_classes = [AllowAny]  # <-- make public

    def post(self, request, *args, **kwargs):
        """
        Handle POST requests to register a new external user.

        Request Body Example (JSON):
        {
            "username": "johndoe",
            "email": "johndoe@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "password": "secret1234",
            "password_confirm": "secret1234"
        }

        Response (success):
            {
                "detail": "Registration successful."
            }
        Response (validation error):
            {
                "email": ["A user with this email already exists."],
                "password_confirm": ["Passwords do not match."]
            }
        """
        # Initialize the serializer with the incoming data
        serializer = self.get_serializer(data=request.data)

        # Validate the data
        if serializer.is_valid():
            user = serializer.save()

            Customer.get_or_create(subscriber=user)
            return Response(
                {"detail": _("Registration successful.")},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
