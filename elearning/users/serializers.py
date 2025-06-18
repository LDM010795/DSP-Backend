"""
E-Learning User Management Serializers

This module provides comprehensive serializers for user authentication,
user data management, and password operations in the E-Learning system.

Serializers:
- CustomTokenObtainPairSerializer: Enhanced JWT token with user metadata
- UserSerializer: Complete user data serialization
- SetInitialPasswordSerializer: Secure password setting with validation

Features:
- Enhanced JWT tokens with user role information
- Comprehensive user data validation
- Secure password handling with confirmation
- Profile integration for force password change status

Author: DSP Development Team
Version: 1.0.0
"""

from typing import Dict, Any, Optional
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Profile


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Enhanced JWT token serializer with user metadata integration.
    
    Extends the default JWT token serializer to include additional user
    information in the token payload for frontend convenience and
    profile-specific settings.
    
    Token Payload Includes:
    - username: User identification
    - is_staff: Staff privileges flag
    - is_superuser: Superuser privileges flag
    - force_password_change: Password security requirement
    """
    
    @classmethod
    def get_token(cls, user: User) -> RefreshToken:
        """
        Generate enhanced JWT token with user metadata.
        
        Args:
            user: Authenticated user instance
            
        Returns:
            RefreshToken with additional user information
            
        Raises:
            Profile.DoesNotExist: If user profile is missing
        """
        token = super().get_token(user)
        
        # Add user identification and role information
        token['username'] = user.username
        token['is_staff'] = user.is_staff
        token['is_superuser'] = user.is_superuser
        
        # Add profile-specific security settings
        try:
            token['force_password_change'] = user.profile.force_password_change
        except Profile.DoesNotExist:
            # Create missing profile and set default security requirement
            Profile.objects.create(user=user)
            token['force_password_change'] = True
            
        return token
    
    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate authentication credentials and enhance response.
        
        Args:
            attrs: Authentication credentials
            
        Returns:
            Enhanced authentication response with user metadata
        """
        data = super().validate(attrs)
        
        # Add user information to response for frontend convenience
        data.update({
            'user_id': self.user.id,
            'username': self.user.username,
            'is_staff': self.user.is_staff,
            'is_superuser': self.user.is_superuser,
            'force_password_change': getattr(self.user.profile, 'force_password_change', True)
        })
        
        return data


class UserSerializer(serializers.ModelSerializer):
    """
    Comprehensive user data serializer for the E-Learning system.
    
    Provides complete user information serialization including profile
    integration and proper field validation for user management operations.
    
    Read-only fields are automatically handled to prevent unauthorized
    modifications of critical user attributes.
    """
    
    force_password_change = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'is_staff', 'is_superuser', 'is_active', 'date_joined', 'last_login',
            'force_password_change'
        )
        read_only_fields = (
            'id', 'date_joined', 'last_login', 'is_superuser'
        )
        
    def get_force_password_change(self, obj: User) -> bool:
        """
        Get force password change status from user profile.
        
        Args:
            obj: User instance
            
        Returns:
            Boolean indicating if password change is required
        """
        try:
            return obj.profile.force_password_change
        except Profile.DoesNotExist:
            return True
            
    def get_full_name(self, obj: User) -> str:
        """
        Get formatted full name of the user.
        
        Args:
            obj: User instance
            
        Returns:
            Formatted full name or username if names are not available
        """
        if obj.first_name and obj.last_name:
            return f"{obj.first_name} {obj.last_name}"
        elif obj.first_name:
            return obj.first_name
        elif obj.last_name:
            return obj.last_name
        return obj.username
    
    def validate_email(self, value: str) -> str:
        """
        Validate email uniqueness and format.
        
        Args:
            value: Email address to validate
            
        Returns:
            Validated email address
            
        Raises:
            ValidationError: If email is invalid or already exists
        """
        if value:
            # Check for existing email (excluding current user during updates)
            user_id = self.instance.id if self.instance else None
            if User.objects.filter(email=value).exclude(id=user_id).exists():
                raise serializers.ValidationError(
                    _("A user with this email address already exists.")
                )
        return value
    
    def validate_username(self, value: str) -> str:
        """
        Validate username uniqueness and format.
        
        Args:
            value: Username to validate
            
        Returns:
            Validated username
            
        Raises:
            ValidationError: If username is invalid or already exists
        """
        # Check for existing username (excluding current user during updates)
        user_id = self.instance.id if self.instance else None
        if User.objects.filter(username=value).exclude(id=user_id).exists():
            raise serializers.ValidationError(
                _("A user with this username already exists.")
            )
        return value


class SetInitialPasswordSerializer(serializers.Serializer):
    """
    Secure password setting serializer with comprehensive validation.
    
    Handles initial password setting for new users with security requirements
    including password confirmation, strength validation, and profile updates.
    
    Features:
    - Password confirmation validation
    - Django password strength validation
    - Automatic profile update to remove force password change requirement
    """
    
    password = serializers.CharField(
        write_only=True,
        required=True,
        min_length=8,
        style={'input_type': 'password'},
        help_text=_('Password must be at least 8 characters long')
    )
    
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text=_('Enter the same password for confirmation')
    )
    
    def validate_password(self, value: str) -> str:
        """
        Validate password strength using Django validators.
        
        Args:
            value: Password to validate
            
        Returns:
            Validated password
            
        Raises:
            ValidationError: If password doesn't meet security requirements
        """
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value
    
    def validate(self, data: Dict[str, str]) -> Dict[str, str]:
        """
        Validate password confirmation match.
        
        Args:
            data: Serializer data containing password fields
            
        Returns:
            Validated data
            
        Raises:
            ValidationError: If passwords don't match
        """
        password = data.get('password')
        password_confirm = data.get('password_confirm')
        
        if password != password_confirm:
            raise serializers.ValidationError({
                'password_confirm': _("The passwords do not match.")
            })
            
        return data
    
    def save(self, user: User) -> User:
        """
        Set new password and update user profile.
        
        Args:
            user: User instance to update
            
        Returns:
            Updated user instance
            
        Side Effects:
            - Sets new password for user
            - Removes force password change requirement from profile
        """
        password = self.validated_data['password']
        user.set_password(password)
        user.save()
        
        # Update profile to remove force password change requirement
        try:
            user.profile.mark_password_changed()
        except Profile.DoesNotExist:
            # Create profile if it doesn't exist
            Profile.objects.create(user=user, force_password_change=False)
            
        return user 