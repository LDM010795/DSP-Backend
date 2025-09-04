"""
Business Logic Handlers for Microsoft Authentication

This module defines handler classes that encapsulate the business logic
for different types of users authenticating via Microsoft. Each handler
is responsible for validating a user against specific criteria (e.g.,
is an employee, has tool access) and creating or updating the
corresponding user model in the database.

This approach allows for a clean separation of concerns and makes the
authentication flow easily extensible for new user types (e.g., customers).

Author: DSP Development Team
Version: 2.0.0 (Refactored)
"""

import logging
from typing import Dict, Any, Tuple
from abc import ABC, abstractmethod

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Q

from core.employees.models import Employee, Tool, EmployeeToolAccess

logger = logging.getLogger(__name__)
User = get_user_model()


class BaseAuthHandler(ABC):
    """Abstract base class for an authentication handler."""

    @abstractmethod
    def handle_authentication(
        self, user_info: Dict[str, Any], tool: Tool
    ) -> Dict[str, Any]:
        """
        Handles the authentication and authorization logic for a user.
        Should be implemented by subclasses.

        Args:
            user_info: User profile data from Microsoft Graph.
            tool: The specific tool the user is trying to access.

        Returns:
            A dictionary containing the final authentication response data,
            including JWT tokens.
        """
        pass

    def _generate_jwt_tokens(self, user: User) -> Dict[str, str]:
        """Generates JWT refresh and access tokens for a given user."""
        refresh = RefreshToken.for_user(user)
        return {"refresh": str(refresh), "access": str(refresh.access_token)}


class EmployeeAuthHandler(BaseAuthHandler):
    """Handles authentication for internal employees."""

    def handle_authentication(
        self, user_info: Dict[str, Any], tool: Tool
    ) -> Dict[str, Any]:
        """
        Handles the authentication flow for a DSP employee.
        1. Validates the user's email domain.
        2. Finds the corresponding Employee record.
        3. Verifies access to the requested tool.
        4. Creates or updates the Django User model.
        5. Generates JWT tokens.
        """
        email = user_info.get("mail") or user_info.get("userPrincipalName")
        if not email:
            raise ValueError("No email address found in Microsoft profile.")

        if not self._is_valid_domain(email):
            raise PermissionError(f"Email domain not allowed: {email.split('@')[-1]}")

        try:
            employee = Employee.objects.get(email__iexact=email, is_active=True)
        except Employee.DoesNotExist:
            raise PermissionError(f"No active employee record found for email: {email}")

        if not self._has_tool_access(employee, tool):
            raise PermissionError(
                f"Employee {email} does not have access to tool '{tool.slug}'."
            )

        user, created = self._create_or_update_django_user(employee, user_info)
        tokens = self._generate_jwt_tokens(user)

        return {
            "success": True,
            "user": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
            },
            "employee_info": {
                "id": employee.id,
                "first_name": employee.first_name,
                "last_name": employee.last_name,
                "email": employee.email,
                "department": {
                    "id": employee.department.id,
                    "name": employee.department.name,
                },
                "position": {
                    "id": employee.position.id,
                    "title": employee.position.title,
                },
                "max_working_hours": employee.max_working_hours,
                "is_active": employee.is_active,
            },
            "tool": {"slug": tool.slug, "name": tool.name},
            "tokens": tokens,
            "created": created,
        }

    def _is_valid_domain(self, email: str) -> bool:
        """Checks if the email's domain is in the allowed list."""
        allowed_domains = getattr(settings, "ALLOWED_EMAIL_DOMAINS", None)
        if not allowed_domains:
            return True  # Skip check if not configured
        domain = email.split("@")[-1]
        return domain.lower() in [d.lower() for d in allowed_domains]

    def _has_tool_access(self, employee: Employee, tool: Tool) -> bool:
        """
        Checks if the employee has active (non-expired) access to the given tool.
        """
        now = timezone.now()
        return EmployeeToolAccess.objects.filter(
            Q(employee=employee, tool=tool),
            Q(expires_at__isnull=True) | Q(expires_at__gt=now),
        ).exists()

    def _create_or_update_django_user(
        self, employee: Employee, user_info: Dict[str, Any]
    ) -> Tuple[User, bool]:
        """
        Creates a new Django user or updates an existing one based on
        the employee profile.
        """
        defaults = {
            "first_name": employee.first_name,
            "last_name": employee.last_name,
        }
        user, created = User.objects.update_or_create(
            email=employee.email, defaults=defaults
        )
        return user, created
