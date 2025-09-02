from rest_framework import serializers
from core.employees.models import Employee
from .models import Availability, ShiftSchedule


class EmployeeSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Employee
        fields = [
            "id",
            "first_name",
            "last_name",
            "full_name",
            "email",
            "max_working_hours",
            "department",
            "department_name",
            "position",
            "position_title",
        ]

    department_name = serializers.CharField(source="department.name", read_only=True)

    position_title = serializers.CharField(source="position.title", read_only=True)


class AvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Availability
        fields = ["id", "employee", "date", "status", "note"]


class ShiftScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShiftSchedule
        fields = [
            "id",
            "employee",
            "date",
            "shift_type",
            "hours",
            "activity",
            "groups",
        ]
