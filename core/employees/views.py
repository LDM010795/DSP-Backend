"""
Employee Management Views - DSP (Digital Solutions Platform)

This module contains the Django REST Framework ViewSets for employee management,
including departments, positions, employees, attendance tracking, and tool access control.

Features:
- Complete CRUD operations for all employee-related models
- Advanced filtering and search capabilities
- Role-based access control and permissions
- Statistical endpoints for employee analytics
- Tool access management for DSP applications

API Endpoints:
- /api/employees/departments/ - Department management
- /api/employees/positions/ - Position management
- /api/employees/employees/ - Employee management
- /api/employees/attendance/ - Attendance tracking
- /api/employees/tools/ - Tool management
- /api/employees/tool-access/ - Tool access control

Author: DSP Development Team
Created: 10.07.2025
Version: 1.0.0
"""

from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from .models import Department, Position, Employee, Attendance, Tool, EmployeeToolAccess
from .serializers import (
    DepartmentSerializer,
    PositionSerializer,
    EmployeeSerializer,
    AttendanceSerializer,
    ToolSerializer,
    EmployeeToolAccessSerializer,
)
from django.db import models
from collections import defaultdict
from rest_framework.permissions import IsAuthenticated


# Create your views here.


class DepartmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet für Department CRUD-Operationen
    """

    queryset = Department.objects.all().order_by("name")
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Optionale Filterung nach aktiven/inaktiven Departments
        """
        queryset = super().get_queryset()
        is_active = self.request.query_params.get("is_active", None)

        if is_active is not None:
            is_active_bool = is_active.lower() == "true"
            queryset = queryset.filter(is_active=is_active_bool)

        # Suchfunktion
        search = self.request.query_params.get("search", None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )

        return queryset

    @action(detail=False, methods=["get"])
    def active(self, request):
        """
        Gibt nur aktive Departments zurück
        """
        active_departments = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(active_departments, many=True)
        return Response(serializer.data)


class PositionViewSet(viewsets.ModelViewSet):
    """
    ViewSet für Position CRUD-Operationen
    """

    queryset = Position.objects.all().order_by("title")
    serializer_class = PositionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Optionale Filterung nach aktiven/inaktiven Positions
        """
        queryset = super().get_queryset()
        is_active = self.request.query_params.get("is_active", None)

        if is_active is not None:
            is_active_bool = is_active.lower() == "true"
            queryset = queryset.filter(is_active=is_active_bool)

        # Suchfunktion
        search = self.request.query_params.get("search", None)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )

        return queryset

    @action(detail=False, methods=["get"])
    def active(self, request):
        """
        Gibt nur aktive Positions zurück
        """
        active_positions = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(active_positions, many=True)
        return Response(serializer.data)


class EmployeeViewSet(viewsets.ModelViewSet):
    """
    ViewSet für Employee CRUD-Operationen
    """

    queryset = (
        Employee.objects.select_related("department", "position")
        .all()
        .order_by("last_name", "first_name")
    )
    serializer_class = EmployeeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Filterung und Suchfunktionen für Employees
        """
        queryset = super().get_queryset()

        # Filter nach aktiven/inaktiven Employees
        is_active = self.request.query_params.get("is_active", None)
        if is_active is not None:
            is_active_bool = is_active.lower() == "true"
            queryset = queryset.filter(is_active=is_active_bool)

        # Filter nach Department
        department_id = self.request.query_params.get("department", None)
        if department_id:
            queryset = queryset.filter(department_id=department_id)

        # Filter nach Position
        position_id = self.request.query_params.get("position", None)
        if position_id:
            queryset = queryset.filter(position_id=position_id)

        # Suchfunktion
        search = self.request.query_params.get("search", None)
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
                | Q(department__name__icontains=search)
                | Q(position__title__icontains=search)
            )

        return queryset

    @action(detail=False, methods=["get"])
    def active(self, request):
        """
        Gibt nur aktive Employees zurück
        """
        active_employees = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(active_employees, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def by_department(self, request):
        """
        Gibt Employees gruppiert nach Department zurück
        """
        employees = self.get_queryset().filter(is_active=True)
        departments_data = defaultdict(list)

        for employee in employees:
            departments_data[employee.department.name].append(
                self.get_serializer(employee).data
            )

        return Response(dict(departments_data))

    @action(detail=False, methods=["get"])
    def statistics(self, request):
        """
        Grundlegende Statistiken über Employees
        """
        queryset = self.get_queryset()

        stats = {
            "total_employees": queryset.count(),
            "active_employees": queryset.filter(is_active=True).count(),
            "inactive_employees": queryset.filter(is_active=False).count(),
            "departments_count": Department.objects.filter(is_active=True).count(),
            "positions_count": Position.objects.filter(is_active=True).count(),
            "average_working_hours": queryset.filter(is_active=True).aggregate(
                avg_hours=models.Avg("max_working_hours")
            )["avg_hours"]
            or 0,
        }

        return Response(stats)


class ToolViewSet(viewsets.ModelViewSet):
    """
    ViewSet für Tool CRUD-Operationen

    Verwaltet die verschiedenen DSP-Anwendungen (E-Learning, Shift-Planner, etc.)
    mit rollenbasierter Zugriffskontrolle.
    """

    queryset = Tool.objects.all().order_by("slug")
    serializer_class = ToolSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Filtert Tools basierend auf Benutzerberechtigungen.
        Nicht-Admin Benutzer sehen nur aktive Tools.
        """
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(is_active=True)
        return qs


class EmployeeToolAccessViewSet(viewsets.ModelViewSet):
    """
    ViewSet für Employee Tool Access CRUD-Operationen

    Verwaltet die Berechtigungen von Mitarbeitern für verschiedene DSP-Tools.
    """

    serializer_class = EmployeeToolAccessSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Filtert Tool-Zugriffe basierend auf Query-Parametern.
        """
        qs = EmployeeToolAccess.objects.select_related("employee", "tool")
        employee_id = self.request.query_params.get("employee")
        tool_id = self.request.query_params.get("tool")
        if employee_id:
            qs = qs.filter(employee_id=employee_id)
        if tool_id:
            qs = qs.filter(tool_id=tool_id)
        return qs


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Custom Permission: Erlaubt Zugriff, wenn der User Admin ist oder die Attendance ihm gehört

    Diese Permission-Klasse wird für Attendance-Objekte verwendet, um sicherzustellen,
    dass Benutzer nur ihre eigenen Anwesenheitsdaten einsehen und bearbeiten können.
    """

    def has_object_permission(self, request, view, obj):
        """
        Überprüft, ob der Benutzer Berechtigung für das spezifische Objekt hat.

        Args:
            request: HTTP Request
            view: ViewSet View
            obj: Attendance-Objekt

        Returns:
            bool: True wenn Zugriff erlaubt, False sonst
        """
        if request.user.is_staff or request.user.is_superuser:
            return True
        try:
            return obj.employee.user == request.user
        except AttributeError:
            return False


class AttendanceViewSet(viewsets.ModelViewSet):
    """
    ViewSet für Attendance CRUD-Operationen

    Verwaltet Anwesenheitsdaten für Werkstudenten und Freelancer mit
    rollenbasierter Zugriffskontrolle und erweiterten Filteroptionen.
    """

    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        """
        Filtert Anwesenheitsdaten basierend auf Benutzerberechtigungen und Query-Parametern.

        Filter-Optionen:
        - month: Monat (1-12)
        - year: Jahr (YYYY)
        - department: Abteilungs-ID

        Nicht-Admin Benutzer sehen nur ihre eigenen Anwesenheitsdaten.
        """
        queryset = Attendance.objects.select_related("employee", "department")

        # Filter nach Berechtigung
        if not self.request.user.is_staff:
            queryset = queryset.filter(employee__user=self.request.user)

        # Filter nach Monat/Jahr
        month = self.request.query_params.get("month")
        year = self.request.query_params.get("year")
        if month and year:
            queryset = queryset.filter(date__month=month, date__year=year)

        # Abteilungsfilter
        department_id = self.request.query_params.get("department")
        if department_id:
            queryset = queryset.filter(department_id=department_id)

        return queryset.order_by("date")

    def perform_create(self, serializer):
        """
        Speichert eine neue Anwesenheitsdaten-Eintragung.

        Args:
            serializer: AttendanceSerializer-Instanz
        """
        serializer.save()
