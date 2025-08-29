from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from django.utils import timezone


class Department(models.Model):
    """
    Model für Unternehmensbereiche/Abteilungen
    """

    name = models.CharField(max_length=100, unique=True, verbose_name="Abteilungsname")
    description = models.TextField(blank=True, null=True, verbose_name="Beschreibung")
    is_active = models.BooleanField(default=True, verbose_name="Aktiv")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Aktualisiert am")

    class Meta:
        verbose_name = "Abteilung"
        verbose_name_plural = "Abteilungen"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Position(models.Model):
    """
    Model für Positionen/Rollen im Unternehmen
    """

    title = models.CharField(
        max_length=100, unique=True, verbose_name="Positionsbezeichnung"
    )
    description = models.TextField(blank=True, null=True, verbose_name="Beschreibung")
    is_active = models.BooleanField(default=True, verbose_name="Aktiv")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Aktualisiert am")

    class Meta:
        verbose_name = "Position"
        verbose_name_plural = "Positionen"
        ordering = ["title"]

    def __str__(self):
        return self.title


class Employee(models.Model):
    """
    Model für Mitarbeiterdaten
    """

    first_name = models.CharField(max_length=50, verbose_name="Vorname")
    last_name = models.CharField(max_length=50, verbose_name="Nachname")
    email = models.EmailField(
        unique=True,
        verbose_name="E-Mail-Adresse",
        help_text="Geschäftliche E-Mail-Adresse des Mitarbeiters",
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        verbose_name="Abteilung",
        help_text="Abteilung in der der Mitarbeiter arbeitet",
    )
    position = models.ForeignKey(
        Position,
        on_delete=models.PROTECT,
        verbose_name="Position",
        help_text="Position/Rolle des Mitarbeiters",
    )
    max_working_hours = models.PositiveIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(60),  # Maximal 60h pro Woche als sinnvolles Limit
        ],
        verbose_name="Maximale Arbeitsstunden",
        help_text="Maximale Arbeitsstunden pro Woche",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Aktiv",
        help_text="Ist der Mitarbeiter noch aktiv beschäftigt?",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Aktualisiert am")

    class Meta:
        verbose_name = "Mitarbeiter"
        verbose_name_plural = "Mitarbeiter"
        ordering = ["last_name", "first_name"]
        indexes = [
            models.Index(fields=["last_name", "first_name"]),
            models.Index(fields=["department", "is_active"]),
            models.Index(fields=["email"]),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.department.name})"

    @property
    def full_name(self):
        """Vollständiger Name des Mitarbeiters"""
        return f"{self.first_name} {self.last_name}"

    def get_department_display(self):
        """Zeigt Abteilung und Position zusammen an"""
        return f"{self.department.name} - {self.position.title}"


class Attendance(models.Model):
    """Anwesenheitsdaten für Werkstudenten und Freelancer"""

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="attendances",
        verbose_name="Mitarbeiter",
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        verbose_name="Abteilung",
    )
    date = models.DateField(verbose_name="Datum")
    hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(24),
        ],
        verbose_name="Arbeitsstunden",
        help_text="Gearbeitete Stunden am angegebenen Datum (z. B. 7.5)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Anwesenheit"
        verbose_name_plural = "Anwesenheiten"
        ordering = ["-date"]
        unique_together = ("employee", "date")
        indexes = [
            models.Index(fields=["employee", "date"]),
            models.Index(fields=["department", "date"]),
        ]

    def __str__(self):
        return f"{self.employee.full_name} – {self.date}: {self.hours}h"


class Tool(models.Model):
    """Representiert eine interne DSP-Applikation (Shift-Planner, E-Learning, …)."""

    slug = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    frontend_url = models.URLField(
        blank=True,
        help_text="URL des zugehörigen Frontends (z.B. http://localhost:5174)",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tool"
        verbose_name_plural = "Tools"
        ordering = ["slug"]

    def __str__(self):
        return self.name


class EmployeeToolAccess(models.Model):
    """Freigabe eines Tools für einen Mitarbeiter."""

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="tool_access"
    )
    tool = models.ForeignKey(
        Tool, on_delete=models.CASCADE, related_name="employee_access"
    )
    granted_at = models.DateTimeField(auto_now_add=True)
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="granted_tool_accesses",
    )
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("employee", "tool")
        verbose_name = "Tool-Freigabe"
        verbose_name_plural = "Tool-Freigaben"
        ordering = ["-granted_at"]

    def __str__(self):
        return f"{self.employee.full_name} → {self.tool.slug}"

    @property
    def is_valid(self):
        return self.tool.is_active and (
            self.expires_at is None or self.expires_at > timezone.now()
        )
