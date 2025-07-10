"""
Employee Management Serializers - DSP (Digital Solutions Platform)

This module contains Django REST Framework serializers for employee management,
providing data validation, transformation, and API response formatting.

Features:
- Complete serialization for all employee-related models
- Comprehensive validation rules for data integrity
- Nested serialization for related objects
- Custom validation methods for business logic
- Optimized API responses with calculated fields

Serializers:
- DepartmentSerializer: Department CRUD operations
- PositionSerializer: Position CRUD operations
- EmployeeSerializer: Employee management with nested data
- EmployeeCreateUpdateSerializer: Simplified employee operations
- AttendanceSerializer: Attendance tracking with validation
- ToolSerializer: Tool management
- EmployeeToolAccessSerializer: Tool access control

Author: DSP Development Team
Created: 10.07.2025
Version: 1.0.0
"""

from rest_framework import serializers
from .models import Attendance, Department, Position, Employee, Tool, EmployeeToolAccess


class DepartmentSerializer(serializers.ModelSerializer):
    """
    Serializer für Department Model
    """
    class Meta:
        model = Department
        fields = [
            'id', 
            'name', 
            'description', 
            'is_active', 
            'created_at', 
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_name(self, value):
        """
        Validiere dass der Department Name einzigartig ist
        """
        if self.instance:
            # Bei Update: ausschließen des aktuellen Eintrags
            if Department.objects.exclude(id=self.instance.id).filter(name=value).exists():
                raise serializers.ValidationError("Eine Abteilung mit diesem Namen existiert bereits.")
        else:
            # Bei Create: prüfen ob Name bereits existiert
            if Department.objects.filter(name=value).exists():
                raise serializers.ValidationError("Eine Abteilung mit diesem Namen existiert bereits.")
        return value


class PositionSerializer(serializers.ModelSerializer):
    """
    Serializer für Position Model
    """
    class Meta:
        model = Position
        fields = [
            'id', 
            'title', 
            'description', 
            'is_active', 
            'created_at', 
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_title(self, value):
        """
        Validiere dass der Position Title einzigartig ist
        """
        if self.instance:
            # Bei Update: ausschließen des aktuellen Eintrags
            if Position.objects.exclude(id=self.instance.id).filter(title=value).exists():
                raise serializers.ValidationError("Eine Position mit diesem Titel existiert bereits.")
        else:
            # Bei Create: prüfen ob Titel bereits existiert
            if Position.objects.filter(title=value).exists():
                raise serializers.ValidationError("Eine Position mit diesem Titel existiert bereits.")
        return value


class EmployeeSerializer(serializers.ModelSerializer):
    """
    Serializer für Employee Model mit nested Department und Position
    """
    department_name = serializers.CharField(source='department.name', read_only=True)
    position_title = serializers.CharField(source='position.title', read_only=True)
    full_name = serializers.CharField(read_only=True)
    
    # Nested Serializers für vollständige Department und Position Informationen
    department_detail = DepartmentSerializer(source='department', read_only=True)
    position_detail = PositionSerializer(source='position', read_only=True)
    
    class Meta:
        model = Employee
        fields = [
            'id',
            'first_name',
            'last_name',
            'email',
            'department',
            'position',
            'max_working_hours',
            'is_active',
            'created_at',
            'updated_at',
            'full_name',
            'department_name',
            'position_title',
            'department_detail',
            'position_detail'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'full_name']
    
    def validate_department(self, value):
        """
        Validiere dass die Department aktiv ist
        """
        if not value.is_active:
            raise serializers.ValidationError("Die ausgewählte Abteilung ist nicht aktiv.")
        return value
    
    def validate_position(self, value):
        """
        Validiere dass die Position aktiv ist
        """
        if not value.is_active:
            raise serializers.ValidationError("Die ausgewählte Position ist nicht aktiv.")
        return value
    
    def validate_email(self, value):
        """
        Validiere dass die Email einzigartig ist
        """
        if self.instance:
            # Bei Update: ausschließen des aktuellen Eintrags
            if Employee.objects.exclude(id=self.instance.id).filter(email=value).exists():
                raise serializers.ValidationError("Ein Mitarbeiter mit dieser E-Mail-Adresse existiert bereits.")
        else:
            # Bei Create: prüfen ob Email bereits existiert
            if Employee.objects.filter(email=value).exists():
                raise serializers.ValidationError("Ein Mitarbeiter mit dieser E-Mail-Adresse existiert bereits.")
        return value
    
    def validate_max_working_hours(self, value):
        """
        Validiere Arbeitsstunden
        """
        if value < 1:
            raise serializers.ValidationError("Minimale Arbeitsstunden: 1")
        if value > 60:
            raise serializers.ValidationError("Maximale Arbeitsstunden: 60")
        return value
    
    def to_representation(self, instance):
        """
        Angepasste Darstellung für bessere API-Response
        """
        representation = super().to_representation(instance)
        
        # Vereinfachte Department und Position Darstellung
        representation['department'] = {
            'id': instance.department.id,
            'name': instance.department.name
        }
        representation['position'] = {
            'id': instance.position.id,
            'title': instance.position.title
        }
        
        return representation


class EmployeeCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Einfacher Serializer für Create/Update Operationen ohne nested data
    """
    class Meta:
        model = Employee
        fields = [
            'first_name',
            'last_name',
            'email',
            'department',
            'position',
            'max_working_hours',
            'is_active'
        ]
    
    def validate_department(self, value):
        """
        Validiere dass die Department aktiv ist
        """
        if not value.is_active:
            raise serializers.ValidationError("Die ausgewählte Abteilung ist nicht aktiv.")
        return value
    
    def validate_position(self, value):
        """
        Validiere dass die Position aktiv ist
        """
        if not value.is_active:
            raise serializers.ValidationError("Die ausgewählte Position ist nicht aktiv.")
        return value 


class AttendanceSerializer(serializers.ModelSerializer):
    """
    Serializer für Attendance Model mit erweiterten Validierungen
    
    Enthält Validierungen für:
    - Eindeutigkeit pro Mitarbeiter und Tag
    - Übereinstimmung von Mitarbeiter- und Abteilungsdaten
    - Automatische Berechnung von abgeleiteten Feldern
    """
    employee_full_name = serializers.ReadOnlyField(source="employee.full_name")
    department_name = serializers.ReadOnlyField(source="department.name")

    class Meta:
        model = Attendance
        fields = [
            "id",
            "employee",
            "employee_full_name",
            "department",
            "department_name",
            "date",
            "hours",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate(self, attrs):
        """
        Umfassende Validierung der Attendance-Daten
        
        Validierungen:
        - Mitarbeiter gehört zur angegebenen Abteilung
        - Keine doppelten Einträge für denselben Tag
        """
        employee = attrs.get("employee")
        department = attrs.get("department")
        date = attrs.get("date")

        # Ensure employee belongs to department
        if employee and department and employee.department != department:
            raise serializers.ValidationError(
                "Die gewählte Abteilung stimmt nicht mit der Abteilung des Mitarbeiters überein."
            )

        # Prevent duplicate attendance for same day
        if Attendance.objects.filter(employee=employee, date=date).exists():
            raise serializers.ValidationError(
                "Für diesen Tag wurde bereits eine Anwesenheit erfasst."
            )
        return attrs 


class ToolSerializer(serializers.ModelSerializer):
    """
    Serializer für Tool Model
    
    Verwaltet DSP-Anwendungen wie E-Learning, Shift-Planner, etc.
    """
    class Meta:
        model = Tool
        fields = ["id", "slug", "name", "description", "frontend_url", "is_active"]
        read_only_fields = ["id"]


class EmployeeToolAccessSerializer(serializers.ModelSerializer):
    """
    Serializer für Employee Tool Access Model
    
    Verwaltet die Berechtigungen von Mitarbeitern für verschiedene DSP-Tools
    mit automatischer Validierung der Tool-Aktivität.
    """
    tool = ToolSerializer(read_only=True)
    tool_id = serializers.PrimaryKeyRelatedField(
        source="tool", queryset=Tool.objects.filter(is_active=True), write_only=True
    )

    class Meta:
        model = EmployeeToolAccess
        fields = [
            "id",
            "employee",
            "tool",
            "tool_id",
            "granted_at",
            "expires_at",
        ]
        read_only_fields = ["id", "granted_at"] 