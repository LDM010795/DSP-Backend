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

from typing import Any, Dict, Optional
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from ..models import Profile
from ..serializers import CustomTokenObtainPairSerializer, SetInitialPasswordSerializer


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Enhanced JWT token authentication view.
    
    Extends the default JWT token view to include additional user metadata
    in the token and response for improved frontend integration and
    user experience.
    
    Features:
    - Enhanced token payload with user role information
    - Profile integration for force password change status
    - Comprehensive error handling for authentication failures
    """
    
    serializer_class = CustomTokenObtainPairSerializer
    
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """
        Authenticate user and return enhanced JWT tokens.
        
        Args:
            request: HTTP request containing authentication credentials
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
            
        Returns:
            Response containing JWT tokens and user metadata
            
        Raises:
            ValidationError: If authentication credentials are invalid
        """
        try:
            response = super().post(request, *args, **kwargs)
            
            # Log successful authentication
            if response.status_code == status.HTTP_200_OK and hasattr(self, 'user'):
                # Could add audit logging here
                pass
                
            return response
            
        except Exception as e:
            # Log authentication failure
            return Response(
                {'detail': _('Authentication failed. Please check your credentials.')},
                status=status.HTTP_401_UNAUTHORIZED
            )


class LogoutView(APIView):
    """
    Secure user logout view with token blacklisting.
    
    Provides secure logout functionality by blacklisting the refresh token
    to prevent its reuse, ensuring proper session termination.
    
    Security Features:
    - Token blacklisting to prevent reuse
    - Comprehensive error handling for invalid tokens
    - Proper HTTP status codes for different scenarios
    """
    
    permission_classes = (IsAuthenticated,)
    
    def post(self, request: Request) -> Response:
        """
        Logout user by blacklisting their refresh token.
        
        Args:
            request: HTTP request containing refresh token
            
        Returns:
            Response indicating logout success or failure
            
        Expected Request Data:
            - refresh_token: JWT refresh token to blacklist
        """
        try:
            refresh_token = request.data.get("refresh_token")
            
            if not refresh_token:
                return Response(
                    {'detail': _('Refresh token is required for logout.')},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Blacklist the refresh token
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            # Log successful logout
            # Could add audit logging here
            
            return Response(
                {'detail': _('Successfully logged out.')},
                status=status.HTTP_205_RESET_CONTENT
            )
            
        except TokenError as e:
            return Response(
                {'detail': _('Invalid token provided.')},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'detail': _('An error occurred during logout.')},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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
                    {'detail': _('Password has already been set.')},
                    status=status.HTTP_400_BAD_REQUEST
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
                    {'detail': _('Password successfully set.')},
                    status=status.HTTP_200_OK
                )
                
            except Exception as e:
                return Response(
                    {'detail': _('An error occurred while setting the password.')},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        ) 