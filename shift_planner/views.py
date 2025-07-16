"""
Shift Planner Views - DSP (Digital Solutions Platform)

Dieses Modul enthält die Views für das Schichtplanungs-System.
Aktuell als Platzhalter für zukünftige Views implementiert.

Geplante Views:
- Schichtplanungs-Interface
- Mitarbeiterverwaltung
- Anwesenheitsverfolgung
- Schichtplan-Analytics
- API-Endpoints für Frontend-Integration

Status: In Entwicklung - Grundstruktur implementiert

Author: DSP Development Team
Created: 10.07.2025
Version: 1.0.0
"""

from django.shortcuts import render
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from .permissions import IsOwnerOrAdmin
from core.employees.models import Employee
from .models import Availability, ShiftSchedule
from .serializers import EmployeeSerializer, AvailabilitySerializer, ShiftScheduleSerializer


class EmployeeListView(generics.ListAPIView):
    """Liefert aktive Mitarbeiter mit max_working_hours für den Shift-Planner."""

    serializer_class = EmployeeSerializer
    permission_classes = [permissions.AllowAny]  # TODO: Auth integrieren

    def get_queryset(self):
        qs = Employee.objects.filter(is_active=True).select_related("department", "position")
        department_id = self.request.query_params.get("department")
        if department_id:
            qs = qs.filter(department_id=department_id)
        return qs.order_by("last_name", "first_name")


class AvailabilityListCreateView(generics.ListCreateAPIView):
    serializer_class = AvailabilitySerializer
    permission_classes = [IsOwnerOrAdmin]

    def get_queryset(self):
        employee_id = self.request.query_params.get("employee")
        qs = Availability.objects.all()
        if employee_id:
            qs = qs.filter(employee_id=employee_id)
        return qs.order_by("-date")

    def post(self, request, *args, **kwargs):
        """Upsert-Verhalten: Existiert Eintrag für employee+date, wird er aktualisiert."""
        # Direktes Upsert ohne doppelten Unique-Check

        employee_id = request.data.get("employee")
        date = request.data.get("date")
        status_val = request.data.get("status")
        note = request.data.get("note", "")

        # Basisvalidierung – fehlende Felder
        if not all([employee_id, date, status_val]):
            return Response({"detail": "employee, date und status sind Pflichtfelder."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            employee = Employee.objects.get(id=employee_id)
        except Employee.DoesNotExist:
            return Response({"detail": "Employee nicht gefunden."}, status=status.HTTP_400_BAD_REQUEST)

        obj, created = Availability.objects.update_or_create(
            employee=employee,
            date=date,
            defaults={"status": status_val, "note": note},
        )

        return Response(
            self.get_serializer(obj).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class AvailabilityDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AvailabilitySerializer
    queryset = Availability.objects.all()
    permission_classes = [IsOwnerOrAdmin]


class ShiftScheduleListCreateView(generics.ListCreateAPIView):
    serializer_class = ShiftScheduleSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        employee_id = self.request.query_params.get("employee")
        qs = ShiftSchedule.objects.all()
        if employee_id:
            qs = qs.filter(employee_id=employee_id)
        return qs.order_by("-date")

    def post(self, request, *args, **kwargs):
        """Upsert für ShiftSchedule (employee+date eindeutig)."""

        employee_id = request.data.get("employee")
        date = request.data.get("date")
        shift_type = request.data.get("shift_type")
        hours = request.data.get("hours")
        activity = request.data.get("activity", "")
        groups = request.data.get("groups", "")

        if not all([employee_id, date, shift_type, hours]):
            return Response({"detail": "employee, date, shift_type und hours sind Pflichtfelder."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            employee = Employee.objects.get(id=employee_id)
        except Employee.DoesNotExist:
            return Response({"detail": "Employee nicht gefunden."}, status=status.HTTP_400_BAD_REQUEST)

        obj, created = ShiftSchedule.objects.update_or_create(
            employee=employee,
            date=date,
            defaults={
                "shift_type": shift_type,
                "hours": hours,
                "activity": activity,
                "groups": groups,
            },
        )

        return Response(
            self.get_serializer(obj).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class ShiftScheduleDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ShiftScheduleSerializer
    queryset = ShiftSchedule.objects.all()
    permission_classes = [permissions.AllowAny]
