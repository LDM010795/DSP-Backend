"""
Employee Management URLs - DSP (Digital Solutions Platform)

This module defines the URL routing for employee management API endpoints.
Uses Django REST Framework's DefaultRouter for automatic URL generation
with consistent RESTful patterns.

API Endpoints:
- /api/employees/departments/ - Department management
- /api/employees/positions/ - Position management  
- /api/employees/employees/ - Employee management
- /api/employees/attendances/ - Attendance tracking
- /api/employees/tools/ - Tool management
- /api/employees/tool-access/ - Tool access control

Features:
- Automatic CRUD endpoint generation via DRF Router
- Custom action endpoints for specialized operations
- Consistent RESTful URL patterns
- Comprehensive API documentation in comments

Author: DSP Development Team
Created: 10.07.2025
Version: 1.0.0
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DepartmentViewSet, PositionViewSet, EmployeeViewSet, AttendanceViewSet, ToolViewSet, EmployeeToolAccessViewSet

# Django REST Framework Router für automatische URL-Generierung
router = DefaultRouter()
router.register(r'departments', DepartmentViewSet, basename='department')
router.register(r'positions', PositionViewSet, basename='position')
router.register(r'employees', EmployeeViewSet, basename='employee')
router.register(r'attendances', AttendanceViewSet, basename='attendance')
router.register(r'tools', ToolViewSet, basename='tool')
router.register(r'tool-access', EmployeeToolAccessViewSet, basename='toolaccess')

app_name = 'employees'

urlpatterns = [
    # API-Routen über Router
    path('', include(router.urls)),
]

# Die folgenden URLs werden automatisch durch den Router generiert:
# 
# Departments:
# GET    /employees/departments/          - Liste aller Departments
# POST   /employees/departments/          - Neues Department erstellen
# GET    /employees/departments/{id}/     - Einzelnes Department abrufen
# PUT    /employees/departments/{id}/     - Department vollständig aktualisieren
# PATCH  /employees/departments/{id}/     - Department teilweise aktualisieren
# DELETE /employees/departments/{id}/     - Department löschen
# GET    /employees/departments/active/   - Nur aktive Departments
#
# Positions:
# GET    /employees/positions/            - Liste aller Positions
# POST   /employees/positions/            - Neue Position erstellen
# GET    /employees/positions/{id}/       - Einzelne Position abrufen
# PUT    /employees/positions/{id}/       - Position vollständig aktualisieren
# PATCH  /employees/positions/{id}/       - Position teilweise aktualisieren
# DELETE /employees/positions/{id}/       - Position löschen
# GET    /employees/positions/active/     - Nur aktive Positions
#
# Employees:
# GET    /employees/employees/            - Liste aller Employees
# POST   /employees/employees/            - Neuen Employee erstellen
# GET    /employees/employees/{id}/       - Einzelnen Employee abrufen
# PUT    /employees/employees/{id}/       - Employee vollständig aktualisieren
# PATCH  /employees/employees/{id}/       - Employee teilweise aktualisieren
# DELETE /employees/employees/{id}/       - Employee löschen
# GET    /employees/employees/active/     - Nur aktive Employees
# GET    /employees/employees/by_department/ - Employees gruppiert nach Department
# GET    /employees/employees/statistics/ - Employee-Statistiken 