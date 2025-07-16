"""
Shift Planner Models - DSP (Digital Solutions Platform)

Dieses Modul enthält die Datenmodelle für das Schichtplanungs-System.
Aktuell als Platzhalter für zukünftige Modelle implementiert.

Geplante Models:
- Shift: Schichtdefinitionen und -zeiten
- Employee: Mitarbeiterverwaltung und -daten
- Schedule: Schichtpläne und -zuordnungen
- Attendance: Anwesenheitsverfolgung
- Department: Abteilungsverwaltung

Status: In Entwicklung - Grundstruktur implementiert

Author: DSP Development Team
Created: 10.07.2025
Version: 1.0.0
"""

from django.db import models
from django.conf import settings
from core.employees.models import Employee  # type: ignore
from django.core.validators import MinValueValidator, MaxValueValidator


class Availability(models.Model):
    """Verfügbarkeiten je Mitarbeiter und Tag."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    STATUS_CHOICES = [
        (AVAILABLE, "Verfügbar"),
        (UNAVAILABLE, "Nicht verfügbar"),
    ]

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="availabilities",
        verbose_name="Mitarbeiter",
    )
    date = models.DateField(verbose_name="Datum")
    status = models.CharField(
        max_length=12,
        choices=STATUS_CHOICES,
        default=AVAILABLE,
        verbose_name="Status",
    )
    note = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Notiz",
        help_text="Optionale Anmerkung (z. B. Urlaub, Arzttermin).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Verfügbarkeit"
        verbose_name_plural = "Verfügbarkeiten"
        unique_together = ("employee", "date")
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["employee", "date"]),
        ]

    def __str__(self):
        return f"{self.employee.full_name} – {self.date}: {self.status}"


class ShiftSchedule(models.Model):
    """Geplante Schicht(en) pro Mitarbeiter und Tag."""

    MORNING = "morning"
    EVENING = "evening"
    OFF = "off"
    HOLIDAY = "holiday"
    CUSTOM = "custom"

    # Neue Aktivitäts-Typen – Trainingsaktivitäten (TA) und Dokumentation (D)
    ACTIVITY_TA = "TA"
    ACTIVITY_D = "D"
    ACTIVITY_DTA = "D/TA"

    ACTIVITY_CHOICES = [
        (ACTIVITY_TA, "Trainingsaktivität"),
        (ACTIVITY_D, "Dozent"),
        (ACTIVITY_DTA, "D und TA kombiniert"),
    ]

    SHIFT_CHOICES = [
        (MORNING, "Frühschicht"),
        (EVENING, "Spätschicht"),
        (OFF, "Frei"),
        (HOLIDAY, "Feiertag"),
        (CUSTOM, "Individuell"),
    ]

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="shift_schedules",
        verbose_name="Mitarbeiter",
    )
    date = models.DateField(verbose_name="Datum")
    shift_type = models.CharField(
        max_length=10,
        choices=SHIFT_CHOICES,
        verbose_name="Schichtart",
    )
    hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(24)],
        verbose_name="Geplante Stunden",
        help_text="Geplante Arbeitsstunden (z. B. 7.5)",
    )

    # Neue optionale Felder
    activity = models.CharField(
        max_length=5,
        choices=ACTIVITY_CHOICES,
        blank=True,
        verbose_name="Aktivität",
        help_text="Optionaler Aktivitätscode (TA, D, D/TA)",
    )

    groups = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Gruppen",
        help_text="Optionale Gruppenangabe (z. B. '5 / 6 / 7')",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Schichtplan-Eintrag"
        verbose_name_plural = "Schichtplan-Einträge"
        unique_together = ("employee", "date")
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["employee", "date"]),
        ]

    def __str__(self):
        activity_display = f" [{self.activity}]" if self.activity else ""
        groups_display = f" {self.groups}" if self.groups else ""
        return (
            f"{self.employee.full_name} – {self.date}: {self.shift_type}{activity_display} "
            f"({self.hours}h){groups_display}"
        )
