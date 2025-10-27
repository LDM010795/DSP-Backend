# elearning/dashboard/views.py
from datetime import timedelta
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from elearning.dashboard.serializers import DashboardSer


# --------- Stubs: replace with real ORM queries when ready ---------

def compute_week_streak_days(user) -> int:
    # TODO: use your activity table
    return 5

def compute_weekly_learning_hours(user) -> float:
    # TODO: sum minutes this ISO week / 60.0
    return 12.5

def compute_modules_completed(user) -> int:
    # TODO: count fully completed modules for user
    return 8

def compute_current_goal_percent(user) -> int:
    # TODO: read from user profile/goal if you have it
    return 85

def list_active_modules(user):
    # TODO: join your Module + user progress + activity
    return [
        {
            "id": "mod_api_design",
            "title": "API Design Principles",
            "study_time_hours": 2.5,
            "lessons_done": 3,
            "lessons_total": 5,
            "progress_percent": 65,
        },
        {
            "id": "mod_async_js",
            "title": "Asynchrones JavaScript (Promises, async/await)",
            "study_time_hours": 1.8,
            "lessons_done": 2,
            "lessons_total": 5,
            "progress_percent": 40,
        },
        {
            "id": "mod_css_layout",
            "title": "CSS Flexbox & Grid",
            "study_time_hours": 3.2,
            "lessons_done": 4,
            "lessons_total": 5,
            "progress_percent": 80,
        },
    ]

def list_upcoming_events(user):
    # TODO: fetch upcoming assessments/deadlines for this user
    return [
        {
            "id": "evt_quiz_api",
            "title": "API Design Principles - Quiz",
            "date_iso": "2025-11-28",
            "type": "Meilenstein",
        },
        {
            "id": "evt_exam_js",
            "title": "JavaScript Fundamentals - Abschlussprüfung",
            "date_iso": "2025-11-30",
            "type": "Prüfung",
        },
        {
            "id": "evt_project_react",
            "title": "React Projekt Abgabe",
            "date_iso": "2025-12-05",
            "type": "Aufgabe",
        },
    ]


# ----------------------------- View ------------------------------

class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        payload = {
            "greeting_name": user.first_name or user.username,
            "week_streak_days": compute_week_streak_days(user),
            "weekly_learning_hours": compute_weekly_learning_hours(user),
            "modules_completed": compute_modules_completed(user),
            "current_goal_percent": compute_current_goal_percent(user),
            "active_modules": list_active_modules(user),
            "upcoming_events": list_upcoming_events(user),
        }
        data = DashboardSer(payload).data
        return Response(data)
