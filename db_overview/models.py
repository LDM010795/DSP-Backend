"""
Database Overview Models

This module provides models for analyzing and storing database schema information
and relationships for the DSP Database Overview tool.

Author: DSP Development Team
Version: 1.0.0
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
import json


class SchemaSnapshot(models.Model):
    """
    Stores periodic snapshots of the database schema for analysis
    """
    created_at = models.DateTimeField(auto_now_add=True)
    total_models = models.IntegerField(default=0)
    total_tables = models.IntegerField(default=0)
    total_relationships = models.IntegerField(default=0)
    schema_hash = models.CharField(max_length=64, unique=True)
    
    class Meta:
        verbose_name = _("Schema Snapshot")
        verbose_name_plural = _("Schema Snapshots")
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Schema Snapshot {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class ModelAnalysis(models.Model):
    """
    Stores analysis data for individual Django models
    """
    snapshot = models.ForeignKey(
        SchemaSnapshot, 
        on_delete=models.CASCADE, 
        related_name='model_analyses'
    )
    app_label = models.CharField(max_length=100)
    model_name = models.CharField(max_length=100)
    table_name = models.CharField(max_length=100)
    field_count = models.IntegerField(default=0)
    relationship_count = models.IntegerField(default=0)
    record_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _("Model Analysis")
        verbose_name_plural = _("Model Analyses")
        unique_together = ['snapshot', 'app_label', 'model_name']
        ordering = ['app_label', 'model_name']
    
    def __str__(self):
        return f"{self.app_label}.{self.model_name}"
