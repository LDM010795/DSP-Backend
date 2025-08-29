"""
E-Learning User Management CRUD Views

This module provides comprehensive user management functionality for administrators
in the E-Learning system, including user creation, modification, and profile management.

Views:
- UserCrudViewSet: Complete CRUD operations for user management
- Administrative user management with proper permissions

Features:
- Full user lifecycle management
- Profile integration and management
- Admin-only access control
- Comprehensive error handling and validation
- Optimized database queries for performance

Author: DSP Development Team
Version: 1.0.0
"""

from typing import Optional
from django.contrib.auth.models import User
from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from ..models import Profile
from ..serializers import UserSerializer


class UserCrudViewSet(viewsets.ModelViewSet):
    """
    Complete user management ViewSet for administrative operations.

    Provides full CRUD (Create, Read, Update, Delete) functionality for user
    management with proper administrative permissions and profile integration.

    Features:
    - Complete user lifecycle management
    - Automatic profile creation and management
    - Admin-only access control
    - Optimized database queries with profile prefetching
    - Custom actions for user-specific operations

    Permissions:
    - Requires administrator privileges (IsAdminUser)
    - All operations are restricted to staff users
    """

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self) -> QuerySet[User]:
        """
        Get optimized queryset with profile prefetching.

        Returns:
            Optimized QuerySet with related profile data
        """
        return User.objects.select_related("profile").order_by("id")

    def perform_create(self, serializer: UserSerializer) -> None:
        """
        Create new user with automatic profile creation.

        Args:
            serializer: Validated user serializer

        Side Effects:
            - Creates user instance
            - Automatically creates associated profile
            - Sets force_password_change to True for security
        """
        user = serializer.save()

        # Ensure profile exists (signal should handle this, but safety check)
        if not hasattr(user, "profile"):
            Profile.objects.create(user=user, force_password_change=True)

    def perform_update(self, serializer: UserSerializer) -> None:
        """
        Update user with profile management.

        Args:
            serializer: Validated user serializer

        Side Effects:
            - Updates user instance
            - Maintains profile integrity
        """
        user = serializer.save()

        # Ensure profile exists after update
        if not hasattr(user, "profile"):
            Profile.objects.create(user=user, force_password_change=True)

    def perform_destroy(self, instance: User) -> None:
        """
        Delete user with proper cleanup.

        Args:
            instance: User instance to delete

        Note:
            Profile is automatically deleted due to CASCADE relationship
        """
        # Could add additional cleanup logic here if needed
        # (e.g., handling user-related data, logging, etc.)
        super().perform_destroy(instance)

    @action(
        detail=True,
        methods=["post"],
        url_path="force-password-change",
        permission_classes=[permissions.IsAdminUser],
    )
    def force_password_change(
        self, request: Request, pk: Optional[str] = None
    ) -> Response:
        """
        Force password change for specific user.

        Args:
            request: HTTP request
            pk: User primary key

        Returns:
            Response indicating success or failure
        """
        user = self.get_object()

        try:
            user.profile.force_password_change = True
            user.profile.save(update_fields=["force_password_change"])

            return Response(
                {
                    "detail": _(
                        "User will be required to change password on next login."
                    )
                },
                status=status.HTTP_200_OK,
            )
        except Profile.DoesNotExist:
            # Create profile if it doesn't exist
            Profile.objects.create(user=user, force_password_change=True)

            return Response(
                {
                    "detail": _(
                        "Profile created and user will be required to change password."
                    )
                },
                status=status.HTTP_200_OK,
            )
        except Exception:
            return Response(
                {
                    "detail": _(
                        "An error occurred while updating password requirements."
                    )
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(
        detail=True,
        methods=["post"],
        url_path="reset-password-requirement",
        permission_classes=[permissions.IsAdminUser],
    )
    def reset_password_requirement(
        self, request: Request, pk: Optional[str] = None
    ) -> Response:
        """
        Remove password change requirement for specific user.

        Args:
            request: HTTP request
            pk: User primary key

        Returns:
            Response indicating success or failure
        """
        user = self.get_object()

        try:
            user.profile.force_password_change = False
            user.profile.save(update_fields=["force_password_change"])

            return Response(
                {"detail": _("Password change requirement removed for user.")},
                status=status.HTTP_200_OK,
            )
        except Profile.DoesNotExist:
            # Create profile if it doesn't exist
            Profile.objects.create(user=user, force_password_change=False)

            return Response(
                {"detail": _("Profile created without password change requirement.")},
                status=status.HTTP_200_OK,
            )
        except Exception:
            return Response(
                {
                    "detail": _(
                        "An error occurred while updating password requirements."
                    )
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(
        detail=False,
        methods=["get"],
        url_path="statistics",
        permission_classes=[permissions.IsAdminUser],
    )
    def user_statistics(self, request: Request) -> Response:
        """
        Get user statistics for administrative overview.

        Args:
            request: HTTP request

        Returns:
            Response containing user statistics
        """
        try:
            queryset = self.get_queryset()

            statistics = {
                "total_users": queryset.count(),
                "active_users": queryset.filter(is_active=True).count(),
                "staff_users": queryset.filter(is_staff=True).count(),
                "superusers": queryset.filter(is_superuser=True).count(),
                "users_requiring_password_change": queryset.filter(
                    profile__force_password_change=True
                ).count(),
            }

            return Response(statistics, status=status.HTTP_200_OK)

        except Exception:
            return Response(
                {"detail": _("An error occurred while retrieving user statistics.")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
