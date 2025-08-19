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


class ExternalUserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for registering external users (non-company, non-Microsoft) on the platform.

    This serializer handles user sign-up requests for individuals who do not possess a company account
    (i.e., not part of Datasmart Point or not using Microsoft SSO). It validates user input for common
    requirements (unique username/email, password confirmation), creates a new Django user, and
    optionally manages the associated profile to ensure external users are not forced to change their
    password on first login.

    Key Features:
    - Ensures that username and email are unique within the system.
    - Validates password length and enforces password confirmation.
    - Creates both the User and, if necessary, an associated Profile object.
    - Sets force_password_change to False so external users can immediately access the platform.
    - Designed to be integrated with a public registration endpoint (e.g., /api/register/).

    Fields:
    - username: Required, must be unique.
    - email: Required, must be unique.
    - first_name: Optional (can be required as needed).
    - last_name: Optional (can be required as needed).
    - password: Required, write-only, min 8 characters.
    - password_confirm: Required, write-only, must match password.

    Example usage:
        serializer = ExternalUserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
    """

    # Write-only password fields; not included in responses for security
    password = serializers.CharField(write_only=True, min_length=8, required=True)
    password_confirm = serializers.CharField(write_only=True, min_length=8, required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password', 'password_confirm']
        extra_kwargs = {'email': {'required': True}}

    def validate_email(self, value):
        """
        Ensure the provided email is unique within the User model.
        """
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate(self, data):
        """
        Object-level validation to ensure passwords match.
        """
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match"})
        return data

    def create(self, validated_data):
        """
        Create the new User and, if necessary, an associated Profile with force_password_change=False.

        Args:
            validated_data (dict): Validated user data.

        Returns:
            User: The newly created user instance.
        """

        # Remove password fields form validated data before creating the user
        password = validated_data.pop('password')
        validated_data.pop('password_confirm')

        # Create the user instance using Django's built-in create-user method
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()

        # Ensure the associated Profile exists, and set force_password_change to False
        if hasattr(user, 'profile'):
            user.profile.force_password_change = False
            user.profile.save()
        else:
            Profile.objects.create(user=user, force_password_change=False)

        return user
