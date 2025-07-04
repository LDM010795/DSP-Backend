"""
Database Overview URL Configuration

This module defines URL patterns for the Database Overview API endpoints.

Author: DSP Development Team
Version: 1.0.0
"""

from django.urls import path
from . import views

app_name = 'db_overview'

urlpatterns = [
    # Hauptendpunkt für Schema-Analyse
    path('api/schema/', views.get_database_schema, name='database_schema'),
    
    # Tabellendaten für spezifisches Model
    path('api/table/<str:app_label>/<str:model_name>/', views.get_table_data, name='table_data'),
    
    # Datenbankstatistiken
    path('api/statistics/', views.get_database_statistics, name='database_statistics'),
] 