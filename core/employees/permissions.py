from rest_framework.permissions import BasePermission
from core.employees.models import EmployeeToolAccess, Tool

class HasToolAccess(BasePermission):
    """Erlaubt Zugriff nur, wenn der Employee für das Tool freigeschaltet ist."""

    def __init__(self, tool_slug: str):
        self.tool_slug = tool_slug

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        employee = getattr(user, "employee_profile", None)
        if not employee:
            return False
        return EmployeeToolAccess.objects.filter(
            employee=employee,
            tool__slug=self.tool_slug,
            expires_at__isnull=True,
            tool__is_active=True,
        ).exists() 