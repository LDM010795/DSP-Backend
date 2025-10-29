"""
Serializers for the Dashboard API.

Purpose: Defines the structure and validation for the data returned by the
         `DashboardView`. These serializers ensure that all fields in the dashboard
         payload have consistent types and formats before being sent to the frontend.

Structure: The serialization hierarchy mirrors the frontend dashboard layout:

           1. **DashboardModuleSer**
              Represents a single active learning module with its progress and study time.
              Used within `DashboardSer.active_modules`.

           2. **DashboardEventSer**
              Represents a single upcoming event (e.g., milestone, exam, assignment).
              Used within `DashboardSer.upcoming_events`.

           3. **DashboardSer**
              The top-level serializer aggregating the user’s overall statistics and
              lists of modules and events.

Implementation Notes:
    - These are simple `Serializer` classes (not `ModelSerializer`) because the
      data currently comes from stub functions and not directly from ORM models.
    - When replacing stubs with ORM queries, we can switch to `ModelSerializer`
      or continue using these for custom payloads.
    - The `date_iso` field is formatted as `YYYY-MM-DD` for frontend parsing.

TODOs:
    - Link `DashboardModuleSer` to actual `Module` and progress models.
    - Link `DashboardEventSer` to upcoming `Exam`, `Assignment`, or `Milestone` models.
    - Add optional fields (e.g., “status”, “deadline urgency”) once real data is available.

Author: DSP development team
Date: 29-09-2025
"""

from rest_framework import serializers


class DashboardModuleSer(serializers.Serializer):
    """Serializer for a single active learning module shown on the dashboard."""

    id = serializers.CharField()
    title = serializers.CharField()
    study_time_hours = serializers.FloatField()
    lessons_done = serializers.IntegerField()
    lessons_total = serializers.IntegerField()
    progress_percent = serializers.IntegerField()


class DashboardEventSer(serializers.Serializer):
    """Serializer for a single upcoming event (e.g., milestone, exam, or task)."""

    id = serializers.CharField()
    title = serializers.CharField()
    date_iso = serializers.DateField(format="%Y-%m-%d")
    type = serializers.ChoiceField(choices=["Meilenstein", "Prüfung", "Aufgabe"])


class DashboardSer(serializers.Serializer):
    """Top-level dashboard serializer combining stats, modules, and events."""

    greeting_name = serializers.CharField()
    week_streak_days = serializers.IntegerField()
    weekly_learning_hours = serializers.FloatField()
    modules_completed = serializers.IntegerField()
    current_goal_percent = serializers.IntegerField()
    active_modules = DashboardModuleSer(many=True)
    upcoming_events = DashboardEventSer(many=True)
