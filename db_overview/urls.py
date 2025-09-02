"""
Database Overview URL Configuration

This module defines URL patterns for the Database Overview API endpoints.

Author: DSP Development Team
Version: 1.0.0
"""

from django.urls import path
from . import views

app_name = "db_overview"

urlpatterns = [
    # --- Schema Analysis Endpoints ---
    # Hauptendpunkt für Schema-Analyse
    path("schema/", views.get_database_schema, name="database_schema"),
    # --- Table Data Endpoints ---
    # Tabellendaten für spezifisches Model
    path(
        "table/<str:app_label>/<str:model_name>/",
        views.get_table_data,
        name="table_data",
    ),
    # --- Statistics Endpoints ---
    # Datenbankstatistiken
    path("statistics/", views.get_database_statistics, name="database_statistics"),
]
