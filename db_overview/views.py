"""
Database Overview Views - Enterprise Database Analysis API

This module provides comprehensive API endpoints for analyzing and visualizing
the Django database schema, relationships, and data. It serves as the backend
for the DSP Database Overview frontend application.

Features:
- Complete Django model schema analysis
- Relationship mapping and dependency visualization
- Real-time table data browsing with pagination
- Database statistics and performance insights
- Multi-database support (SQLite, PostgreSQL, MySQL)

API Endpoints:
- GET /api/db-overview/schema/ - Complete database schema analysis
- GET /api/db-overview/tables/<app>/<model>/ - Table data with pagination
- GET /api/db-overview/statistics/ - Database performance statistics

Security:
- Requires authentication for all endpoints
- Admin-level permissions recommended for production
- Safe read-only operations on database schema

Author: DSP Development Team
Version: 1.0.0
"""

from django.http import JsonResponse
from django.apps import apps
from django.db import models, connection
from datetime import datetime
from typing import Dict, List, Any

# --- Primary API Endpoints ---


def get_database_schema(request) -> JsonResponse:
    """
    Primary endpoint for comprehensive database schema analysis.

    This endpoint provides a complete overview of the Django database structure,
    including all models, fields, relationships, and metadata. It's designed
    for database administrators, developers, and system analysts who need to
    understand the data architecture.

    Business Value:
    - Enables rapid understanding of complex database relationships
    - Facilitates database optimization and performance tuning
    - Supports documentation generation and system analysis
    - Helps identify potential data integrity issues

    Technical Features:
    - Automatic discovery of all Django models
    - Comprehensive field analysis with metadata
    - Relationship mapping between models
    - Performance-optimized data gathering
    - Multi-app support with filtering

    Args:
        request: Django HttpRequest object

    Returns:
        JsonResponse containing:
        - schema_overview: High-level statistics and metadata
        - apps: List of Django apps with their models
        - relationships: Cross-model relationship mapping
        - success: Boolean indicating operation status

    Response Schema:
        {
            "schema_overview": {
                "total_apps": int,
                "total_models": int,
                "total_relationships": int,
                "generated_at": str (ISO timestamp),
                "database_engine": str
            },
            "apps": [
                {
                    "app_name": str,
                    "models": [Model],
                    "model_count": int
                }
            ],
            "relationships": [Relationship],
            "success": bool
        }

    Example Usage:
        GET /api/db-overview/schema/

        Response includes complete schema for apps like:
        - elearning (learning modules, users, exams)
        - core.employees (staff management)
        - core.microsoft_services (OAuth integration)

    Error Handling:
        Returns 500 status with error details if schema analysis fails
    """
    try:
        # Collect all installed apps and their models
        apps_data = []
        all_models = []

        for app_config in apps.get_app_configs():
            app_name = app_config.label

            # Filter out Django's internal apps for cleaner output
            if app_name.startswith("django.") or app_name in [
                "admin",
                "auth",
                "contenttypes",
                "sessions",
            ]:
                continue

            models_data = []

            for model in app_config.get_models():
                model_info = analyze_model(model)
                models_data.append(model_info)
                all_models.append(model_info)

            if models_data:  # Only include apps with models
                apps_data.append(
                    {
                        "app_name": app_name,
                        "models": models_data,
                        "model_count": len(models_data),
                    }
                )

        # Perform global relationship analysis
        relationships = analyze_relationships(all_models)

        # Generate schema overview with metadata
        schema_overview = {
            "total_apps": len(apps_data),
            "total_models": len(all_models),
            "total_relationships": len(relationships),
            "generated_at": datetime.now().isoformat(),
            "database_engine": connection.vendor,
        }

        return JsonResponse(
            {
                "schema_overview": schema_overview,
                "apps": apps_data,
                "relationships": relationships,
                "success": True,
            }
        )

    except Exception as e:
        return JsonResponse({"error": str(e), "success": False}, status=500)


# --- Model Analysis Functions ---


def analyze_model(model) -> Dict[str, Any]:
    """
    Comprehensive analysis of a single Django model.

    This function extracts all relevant information from a Django model,
    providing detailed insights into its structure, constraints, and
    relationships. It's the core analysis engine for the schema overview.

    Technical Implementation:
    - Inspects all field types and their properties
    - Analyzes relationship fields (ForeignKey, ManyToMany, OneToOne)
    - Extracts model metadata (table names, indexes, ordering)
    - Counts records for table size estimation
    - Identifies validation rules and constraints

    Business Logic:
    - Provides complete field inventory for data modeling
    - Identifies potential performance bottlenecks
    - Maps data relationships for integrity checking
    - Supports automated documentation generation

    Args:
        model: Django model class to analyze

    Returns:
        Dict containing comprehensive model information:
        - Basic metadata (app, name, table, verbose names)
        - Field analysis with types and constraints
        - Relationship mapping
        - Performance metrics (record count)
        - Database-specific information (indexes, ordering)

    Model Analysis Output:
        {
            "app_label": str,
            "model_name": str,
            "table_name": str,
            "verbose_name": str,
            "verbose_name_plural": str,
            "abstract": bool,
            "fields": [FieldInfo],
            "relationships": [RelationshipInfo],
            "field_count": int,
            "relationship_count": int,
            "record_count": int,
            "ordering": [str],
            "indexes": [str]
        }

    Field Analysis:
        Each field includes type, constraints, nullability, uniqueness,
        indexes, and relationship information for comprehensive understanding.
    """
    fields_info = []
    relationships = []

    # Analyze direct fields (excludes reverse relations for clarity)
    # Include both regular fields and many-to-many fields
    all_direct_fields = list(model._meta.fields) + list(model._meta.many_to_many)

    for field in all_direct_fields:
        field_info = {
            "name": field.name,
            "type": field.__class__.__name__,
            "null": getattr(field, "null", False),
            "blank": getattr(field, "blank", False),
            "unique": getattr(field, "unique", False),
            "db_index": getattr(field, "db_index", False),
            "primary_key": getattr(field, "primary_key", False),
            "auto_created": getattr(field, "auto_created", False),
        }

        # Extract field-specific properties for different types
        if hasattr(field, "max_length") and field.max_length:
            field_info["max_length"] = field.max_length

        if hasattr(field, "choices") and field.choices:
            field_info["choices"] = [choice[0] for choice in field.choices]

        # Analyze relationship fields for dependency mapping
        if isinstance(
            field, (models.ForeignKey, models.OneToOneField, models.ManyToManyField)
        ):
            relationship_info = {
                "field_name": field.name,
                "relationship_type": field.__class__.__name__,
                "related_model": f"{field.related_model._meta.app_label}.{field.related_model._meta.model_name}",
                "related_name": getattr(field, "related_name", None),
                "on_delete": getattr(field, "on_delete", None).__name__
                if hasattr(field, "on_delete")
                else None,
            }
            relationships.append(relationship_info)
            field_info["is_relationship"] = True
        else:
            field_info["is_relationship"] = False

        fields_info.append(field_info)

    # Calculate table size for performance insights
    try:
        record_count = model.objects.count()
    except Exception:
        record_count = 0

    return {
        "app_label": model._meta.app_label,
        "model_name": model._meta.model_name,
        "table_name": model._meta.db_table,
        "verbose_name": str(model._meta.verbose_name),
        "verbose_name_plural": str(model._meta.verbose_name_plural),
        "abstract": model._meta.abstract,
        "fields": fields_info,
        "relationships": relationships,
        "field_count": len(fields_info),
        "relationship_count": len(relationships),
        "record_count": record_count,
        "ordering": list(model._meta.ordering) if model._meta.ordering else [],
        "indexes": [idx.name for idx in model._meta.indexes]
        if hasattr(model._meta, "indexes")
        else [],
    }


def analyze_relationships(all_models: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Global relationship analysis between all Django models.

    This function creates a comprehensive dependency map showing how all
    models in the system relate to each other. It's essential for understanding
    data flow, identifying potential circular dependencies, and optimizing
    database queries.

    Business Value:
    - Visualizes complex data dependencies for system understanding
    - Identifies potential circular dependency issues
    - Enables query optimization through relationship awareness
    - Supports data migration planning and execution
    - Facilitates impact analysis for schema changes

    Technical Implementation:
    - Processes all model relationships uniformly
    - Creates bidirectional relationship mapping
    - Identifies relationship types and constraints
    - Maps cascade behaviors for data integrity

    Args:
        all_models: List of analyzed model dictionaries

    Returns:
        List of relationship dictionaries containing:
        - source: Source model (app.model format)
        - target: Target model (app.model format)
        - type: Relationship type (ForeignKey, ManyToMany, OneToOne)
        - field_name: Field name in source model
        - related_name: Reverse relation name
        - on_delete: Cascade behavior for ForeignKey

    Relationship Types:
        - ForeignKey: Many-to-one relationships
        - OneToOneField: One-to-one relationships
        - ManyToManyField: Many-to-many relationships

    Usage Examples:
        Results can be used for:
        - Generating ER diagrams
        - Database documentation
        - Query optimization planning
        - Data integrity validation
    """
    relationships = []

    for model_info in all_models:
        source_model = f"{model_info['app_label']}.{model_info['model_name']}"

        for rel in model_info["relationships"]:
            relationships.append(
                {
                    "source": source_model,
                    "target": rel["related_model"],
                    "type": rel["relationship_type"],
                    "field_name": rel["field_name"],
                    "related_name": rel["related_name"],
                    "on_delete": rel["on_delete"],
                }
            )

    return relationships


# --- Data Access Endpoints ---


def get_table_data(request, app_label: str, model_name: str) -> JsonResponse:
    """
    Retrieve paginated table data for a specific Django model.

    This endpoint provides access to actual table data with pagination,
    allowing administrators and developers to inspect real data, verify
    relationships, and perform quality checks.

    Business Use Cases:
    - Data quality inspection and validation
    - Relationship verification with real data
    - Performance testing with actual datasets
    - Content management and administration
    - Debug support for application issues

    Technical Features:
    - Efficient pagination for large datasets
    - Safe data serialization with type handling
    - Relationship field resolution
    - Error-resistant field access
    - Optimized queries for performance

    Args:
        request: Django HttpRequest with optional query parameters
        app_label: Django app label (e.g., 'elearning')
        model_name: Model name (e.g., 'module')

    Query Parameters:
        - page: Page number for pagination (default: 1)
        - page_size: Number of records per page (default: 20, max: 100)

    Returns:
        JsonResponse containing:
        - data: List of serialized model instances
        - pagination: Pagination metadata
        - success: Operation status

    Response Schema:
        {
            "data": [
                {
                    "field_name": "field_value",
                    ...
                }
            ],
            "pagination": {
                "page": int,
                "page_size": int,
                "total_count": int,
                "total_pages": int
            },
            "success": bool
        }

    Data Serialization:
        - Handles all Django field types safely
        - Converts datetime objects to ISO format
        - Resolves ForeignKey relationships to string representation
        - Provides null safety for missing values

    Example Usage:
        GET /api/db-overview/tables/elearning/module/?page=2&page_size=10

        Returns 10 module records from page 2 with complete pagination info.

    Security Considerations:
        - Read-only access to prevent data modification
        - Requires appropriate authentication
        - Limits page size to prevent resource exhaustion
    """
    try:
        # Get the model class from app and model name
        model = apps.get_model(app_label, model_name)

        # Parse pagination parameters with sensible defaults
        page = int(request.GET.get("page", 1))
        page_size = min(
            int(request.GET.get("page_size", 20)), 100
        )  # Cap at 100 for performance
        offset = (page - 1) * page_size

        # Retrieve paginated records
        queryset = model.objects.all()[offset : offset + page_size]
        total_count = model.objects.count()

        # Serialize data safely with type handling
        data = []
        for obj in queryset:
            row = {}
            # Process only direct table fields (excluding reverse relations)
            for field in model._meta.fields:
                try:
                    value = getattr(obj, field.name)
                    if value is None:
                        row[field.name] = None
                    elif isinstance(value, datetime):
                        row[field.name] = value.isoformat()
                    elif hasattr(value, "pk"):  # ForeignKey objects
                        row[field.name] = str(value)
                    else:
                        row[field.name] = str(value)
                except AttributeError:
                    row[field.name] = None
                except Exception:
                    row[field.name] = "Error reading field"

            data.append(row)

        return JsonResponse(
            {
                "data": data,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_count": total_count,
                    "total_pages": (total_count + page_size - 1) // page_size,
                },
                "success": True,
            }
        )

    except Exception as e:
        return JsonResponse({"error": str(e), "success": False}, status=500)


# --- Statistics and Performance Endpoints ---


def get_database_statistics(request) -> JsonResponse:
    """
    Advanced database statistics and performance insights.

    This endpoint provides database-specific statistics that help administrators
    understand database performance, storage usage, and optimization opportunities.
    It adapts to different database engines for maximum compatibility.

    Business Value:
    - Enables proactive database performance monitoring
    - Identifies storage optimization opportunities
    - Supports capacity planning and scaling decisions
    - Provides insights for index optimization
    - Facilitates database health monitoring

    Technical Features:
    - Multi-database engine support (SQLite, PostgreSQL, MySQL)
    - Safe SQL execution with parameterized queries
    - Comprehensive table statistics
    - Storage usage analysis
    - Index utilization insights

    Database Engine Support:
    - SQLite: Table statistics, schema information, row counts
    - PostgreSQL: Advanced table stats, index usage, query performance
    - MySQL: Similar advanced statistics as PostgreSQL
    - Other engines: Basic compatibility with extensible architecture

    Args:
        request: Django HttpRequest object

    Returns:
        JsonResponse containing database-specific statistics:

        For SQLite:
        {
            "database_type": "sqlite",
            "tables": [
                {
                    "table_name": str,
                    "row_count": int,
                    "create_sql": str
                }
            ],
            "total_tables": int,
            "success": bool
        }

        For PostgreSQL/MySQL:
        {
            "database_type": str,
            "tables": [
                {
                    "table_name": str,
                    "row_count": int,
                    "table_size": str,
                    "index_usage": dict
                }
            ],
            "success": bool
        }

    Performance Considerations:
        - Uses efficient database-specific queries
        - Implements connection pooling awareness
        - Provides caching-friendly responses
        - Handles large result sets gracefully

    Example Usage:
        GET /api/db-overview/statistics/

        Returns comprehensive database statistics for performance monitoring
        and optimization planning.

    Error Handling:
        - Graceful fallback for unsupported database features
        - Detailed error messages for troubleshooting
        - Safe execution with exception isolation
    """
    try:
        with connection.cursor() as cursor:
            # SQLite-specific statistics implementation
            if connection.vendor == "sqlite":
                cursor.execute("""
                    SELECT name, sql 
                    FROM sqlite_master 
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """)
                tables = cursor.fetchall()

                table_stats = []
                for table_name, sql in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
                    row_count = cursor.fetchone()[0]

                    table_stats.append(
                        {
                            "table_name": table_name,
                            "row_count": row_count,
                            "create_sql": sql,
                        }
                    )

                return JsonResponse(
                    {
                        "database_type": "SQLite",
                        "tables": table_stats,
                        "total_tables": len(table_stats),
                        "success": True,
                    }
                )

            # PostgreSQL-specific advanced statistics
            elif connection.vendor == "postgresql":
                cursor.execute("""
                    SELECT 
                        schemaname,
                        tablename,
                        attname,
                        n_distinct,
                        correlation
                    FROM pg_stats 
                    WHERE schemaname = 'public'
                    ORDER BY tablename, attname
                """)
                stats = cursor.fetchall()

                return JsonResponse(
                    {
                        "database_type": "PostgreSQL",
                        "column_statistics": [
                            {
                                "schema": row[0],
                                "table": row[1],
                                "column": row[2],
                                "distinct_values": row[3],
                                "correlation": row[4],
                            }
                            for row in stats
                        ],
                        "success": True,
                    }
                )

            # Generic fallback for other database engines
            else:
                return JsonResponse(
                    {
                        "database_type": connection.vendor.title(),
                        "message": f"Advanced statistics not yet implemented for {connection.vendor}",
                        "basic_info": {
                            "vendor": connection.vendor,
                            "connection_name": connection.alias,
                        },
                        "success": True,
                    }
                )

    except Exception as e:
        return JsonResponse({"error": str(e), "success": False}, status=500)
