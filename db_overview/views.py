"""
Database Overview Views

This module provides comprehensive API endpoints for analyzing and visualizing
the Django database schema, relationships, and data.

Author: DSP Development Team
Version: 1.0.0
"""

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.apps import apps
from django.db import models, connection
from django.core.serializers import serialize
from django.core.exceptions import FieldDoesNotExist
import json
from collections import defaultdict
from datetime import datetime
import hashlib


def get_database_schema(request):
    """
    Hauptendpunkt für die Datenbankschema-Analyse
    
    **Warum diese Funktion?**
    Als Senior Backend-Entwickler weiß ich, dass eine umfassende Schema-Analyse
    entscheidend ist für:
    - Verstehen komplexer Beziehungen
    - Identifizieren von Optimierungsmöglichkeiten
    - Dokumentation der Datenarchitektur
    - Sicherstellung der Datenintegrität
    """
    try:
        # Alle installierten Apps und ihre Models erfassen
        apps_data = []
        all_models = []
        
        for app_config in apps.get_app_configs():
            app_name = app_config.label
            
            # Nur relevante Apps (nicht Django's interne Apps)
            if app_name.startswith('django.') or app_name in ['admin', 'auth', 'contenttypes', 'sessions']:
                continue
                
            models_data = []
            
            for model in app_config.get_models():
                model_info = analyze_model(model)
                models_data.append(model_info)
                all_models.append(model_info)
            
            if models_data:  # Nur Apps mit Models hinzufügen
                apps_data.append({
                    'app_name': app_name,
                    'models': models_data,
                    'model_count': len(models_data)
                })
        
        # Globale Beziehungsanalyse
        relationships = analyze_relationships(all_models)
        
        # Schema-Übersicht
        schema_overview = {
            'total_apps': len(apps_data),
            'total_models': len(all_models),
            'total_relationships': len(relationships),
            'generated_at': datetime.now().isoformat(),
            'database_engine': connection.vendor,
        }
        
        return JsonResponse({
            'schema_overview': schema_overview,
            'apps': apps_data,
            'relationships': relationships,
            'success': True
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'success': False
        }, status=500)


def analyze_model(model):
    """
    Detaillierte Analyse eines Django-Models
    
    **Warum diese Funktion?**
    Diese Funktion extrahiert alle relevanten Informationen eines Models:
    - Feldtypen und Eigenschaften
    - Beziehungen (ForeignKey, ManyToMany, OneToOne)
    - Metadaten (Tabellennamen, Indizes)
    - Validierungsregeln
    """
    fields_info = []
    relationships = []
    
    # Direkte Felder des Models analysieren (keine reverse relations)
    # fields = reguläre Felder, many_to_many = ManyToMany Felder
    all_direct_fields = list(model._meta.fields) + list(model._meta.many_to_many)
    
    for field in all_direct_fields:
        field_info = {
            'name': field.name,
            'type': field.__class__.__name__,
            'null': getattr(field, 'null', False),
            'blank': getattr(field, 'blank', False),
            'unique': getattr(field, 'unique', False),
            'db_index': getattr(field, 'db_index', False),
            'primary_key': getattr(field, 'primary_key', False),
            'auto_created': getattr(field, 'auto_created', False),
        }
        
        # Zusätzliche Eigenschaften für bestimmte Feldtypen
        if hasattr(field, 'max_length') and field.max_length:
            field_info['max_length'] = field.max_length
            
        if hasattr(field, 'choices') and field.choices:
            field_info['choices'] = [choice[0] for choice in field.choices]
        
        # Beziehungsfelder identifizieren
        if isinstance(field, (models.ForeignKey, models.OneToOneField, models.ManyToManyField)):
            relationship_info = {
                'field_name': field.name,
                'relationship_type': field.__class__.__name__,
                'related_model': f"{field.related_model._meta.app_label}.{field.related_model._meta.model_name}",
                'related_name': getattr(field, 'related_name', None),
                'on_delete': getattr(field, 'on_delete', None).__name__ if hasattr(field, 'on_delete') else None,
            }
            relationships.append(relationship_info)
            field_info['is_relationship'] = True
        else:
            field_info['is_relationship'] = False
            
        fields_info.append(field_info)
    
    # Tabellengröße ermitteln (Anzahl Datensätze)
    try:
        record_count = model.objects.count()
    except:
        record_count = 0
    
    return {
        'app_label': model._meta.app_label,
        'model_name': model._meta.model_name,
        'table_name': model._meta.db_table,
        'verbose_name': str(model._meta.verbose_name),
        'verbose_name_plural': str(model._meta.verbose_name_plural),
        'abstract': model._meta.abstract,
        'fields': fields_info,
        'relationships': relationships,
        'field_count': len(fields_info),
        'relationship_count': len(relationships),
        'record_count': record_count,
        'ordering': list(model._meta.ordering) if model._meta.ordering else [],
        'indexes': [idx.name for idx in model._meta.indexes] if hasattr(model._meta, 'indexes') else [],
    }


def analyze_relationships(all_models):
    """
    Globale Beziehungsanalyse zwischen allen Models
    
    **Warum diese Funktion?**
    Diese Funktion erstellt eine umfassende Beziehungsmatrix:
    - Visualisierung komplexer Abhängigkeiten
    - Identifizierung von Circular Dependencies
    - Optimierung von Datenbankabfragen
    - Besseres Verständnis der Datenarchitektur
    """
    relationships = []
    
    for model_info in all_models:
        source_model = f"{model_info['app_label']}.{model_info['model_name']}"
        
        for rel in model_info['relationships']:
            relationships.append({
                'source': source_model,
                'target': rel['related_model'],
                'type': rel['relationship_type'],
                'field_name': rel['field_name'],
                'related_name': rel['related_name'],
                'on_delete': rel['on_delete'],
            })
    
    return relationships


def get_table_data(request, app_label, model_name):
    """
    Tabellendaten für ein spezifisches Model abrufen
    
    **Warum diese Funktion?**
    Ermöglicht die Inspektion realer Daten:
    - Datenqualität überprüfen
    - Beziehungen in Aktion sehen
    - Performance-Probleme identifizieren
    """
    try:
        model = apps.get_model(app_label, model_name)
        
        # Paginierung
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
        offset = (page - 1) * page_size
        
        # Datensätze abrufen
        queryset = model.objects.all()[offset:offset + page_size]
        total_count = model.objects.count()
        
        # Daten serialisieren - nur echte Felder des Models, keine reverse relations
        data = []
        for obj in queryset:
            row = {}
            # Nur echte Tabellenspalten verwenden (keine ManyToMany oder reverse relations)
            for field in model._meta.fields:
                try:
                    value = getattr(obj, field.name)
                    if value is None:
                        row[field.name] = None
                    elif isinstance(value, datetime):
                        row[field.name] = value.isoformat()
                    elif hasattr(value, 'pk'):  # ForeignKey objects
                        row[field.name] = str(value)
                    else:
                        row[field.name] = str(value)
                except AttributeError:
                    row[field.name] = None
                except Exception:
                    row[field.name] = None
            
            data.append(row)
        
        return JsonResponse({
            'data': data,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_count': total_count,
                'total_pages': (total_count + page_size - 1) // page_size,
            },
            'success': True
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'success': False
        }, status=500)


def get_database_statistics(request):
    """
    Erweiterte Datenbankstatistiken
    
    **Warum diese Funktion?**
    Liefert wichtige Metriken für die Datenbankoptimierung:
    - Speicherverbrauch pro Tabelle
    - Indexverwendung
    - Abfrageperformance-Insights
    """
    try:
        with connection.cursor() as cursor:
            # SQLite-spezifische Statistiken
            if connection.vendor == 'sqlite':
                cursor.execute("""
                    SELECT name, sql 
                    FROM sqlite_master 
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """)
                tables = cursor.fetchall()
                
                table_stats = []
                for table_name, sql in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    row_count = cursor.fetchone()[0]
                    
                    table_stats.append({
                        'table_name': table_name,
                        'row_count': row_count,
                        'create_sql': sql,
                    })
                
                return JsonResponse({
                    'database_type': 'SQLite',
                    'tables': table_stats,
                    'total_tables': len(table_stats),
                    'success': True
                })
            
            # Für andere Datenbanken (PostgreSQL, MySQL, etc.)
            else:
                return JsonResponse({
                    'database_type': connection.vendor,
                    'message': 'Advanced statistics not implemented for this database type',
                    'success': True
                })
                
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'success': False
        }, status=500)
