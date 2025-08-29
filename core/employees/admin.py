"""
Employee Management Admin - DSP (Digital Solutions Platform)

Dieses Modul enthält die Django Admin-Konfiguration für das Mitarbeiter-Management.
Ermöglicht die komfortable Verwaltung von Departments, Positionen, Mitarbeitern,
Tools und Tool-Freigaben über das Django Admin Interface.

Features:
- Erweiterte Listendarstellung und Filteroptionen
- Readonly-Felder für Zeitstempel
- Inline-Bearbeitung und Suchfunktionen
- Übersichtliche Fieldsets für bessere Usability

Admin-Klassen:
- DepartmentAdmin: Verwaltung von Abteilungen
- PositionAdmin: Verwaltung von Positionen
- EmployeeAdmin: Verwaltung von Mitarbeitern
- ToolAdmin: Verwaltung von DSP-Tools
- EmployeeToolAccessAdmin: Verwaltung von Tool-Freigaben

Author: DSP Development Team
Created: 10.07.2025
Version: 1.0.0
"""

from django.contrib import admin
from .models import Department, Position, Employee, Tool, EmployeeToolAccess


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ["name", "is_active", "created_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name", "description"]
    ordering = ["name"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        ("Grundinformationen", {"fields": ("name", "description", "is_active")}),
        (
            "Zeitstempel",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ["title", "is_active", "created_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["title", "description"]
    ordering = ["title"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        ("Grundinformationen", {"fields": ("title", "description", "is_active")}),
        (
            "Zeitstempel",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = [
        "full_name",
        "department",
        "position",
        "max_working_hours",
        "is_active",
    ]
    list_filter = ["department", "position", "is_active", "created_at"]
    search_fields = ["first_name", "last_name", "department__name", "position__title"]
    ordering = ["last_name", "first_name"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        ("Persönliche Daten", {"fields": ("first_name", "last_name")}),
        ("Arbeitsplatz", {"fields": ("department", "position", "max_working_hours")}),
        ("Status", {"fields": ("is_active",)}),
        (
            "Zeitstempel",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    # Ermöglicht Inline-Bearbeitung bestimmter Felder
    list_editable = ["is_active"]

    # Anzahl der Einträge pro Seite
    list_per_page = 25

    def full_name(self, obj):
        return obj.full_name

    full_name.short_description = "Name"
    full_name.admin_order_field = "last_name"


@admin.register(Tool)
class ToolAdmin(admin.ModelAdmin):
    list_display = ("slug", "name", "is_active", "frontend_url")
    search_fields = ("slug", "name")
    list_filter = ("is_active",)


@admin.register(EmployeeToolAccess)
class EmployeeToolAccessAdmin(admin.ModelAdmin):
    list_display = ("employee", "tool", "granted_at", "expires_at", "is_valid")
    list_filter = ("tool", "expires_at")
    search_fields = (
        "employee__first_name",
        "employee__last_name",
        "employee__email",
        "tool__slug",
    )
