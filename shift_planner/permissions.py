from rest_framework.permissions import BasePermission, SAFE_METHODS
from core.employees.models import Employee

# ------------------------------------------------------------
# Helper: Prüft, ob der eingeloggte Benutzer laut Employee-Rolle
# als Admin gilt (Positions-Titel enthält "admin", case-insensitiv).
# ------------------------------------------------------------


def is_employee_role_admin(user) -> bool:
    """Returns True, wenn der User über seinen Employee-Datensatz eine Admin-Rolle hat."""

    from core.employees.models import Employee  # local import to avoid circular

    # Preferred: direkte Relation user.employee
    emp = getattr(user, "employee", None)

    # Fallback: Suche per E-Mail, falls keine direkte Relation existiert
    if emp is None:
        try:
            emp = Employee.objects.select_related("position").get(email=user.email)
        except Employee.DoesNotExist:
            return False

    title = (getattr(emp.position, "title", "") or "").lower()
    return "admin" in title


class IsOwnerOrAdmin(BasePermission):
    """Erlaubt Änderungen nur dem betroffenen Mitarbeiter selbst oder Admins."""

    def has_permission(self, request, view):
        # Lesezugriffe immer erlaubt
        if request.method in SAFE_METHODS:
            return True

        # Admins dürfen alles (is_staff ODER Employee-Rolle = Admin)
        if (
            request.user
            and request.user.is_authenticated
            and (request.user.is_staff or is_employee_role_admin(request.user))
        ):
            return True

        # Für POST muss employee_id im Body zur eingeloggten Person gehören
        if request.method == "POST":
            employee_id = request.data.get("employee")
            try:
                employee = Employee.objects.get(id=employee_id)
            except Employee.DoesNotExist:
                return False
            return employee.email == request.user.email

        return True  # Detail-View handled in has_object_permission

    def has_object_permission(self, request, view, obj):
        # Read safe
        if request.method in SAFE_METHODS:
            return True
        # Admin (is_staff ODER Employee-Rolle = Admin)
        if (
            request.user
            and request.user.is_authenticated
            and (request.user.is_staff or is_employee_role_admin(request.user))
        ):
            return True
        # Owner
        return obj.employee.email == request.user.email
