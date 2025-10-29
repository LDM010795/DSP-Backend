"""
Tests for the Dashboard API view.

Covers:
- Authentication requirement
- Response status and structure
- Field type validation (basic serializer conformity)
"""

from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from rest_framework import status

User = get_user_model()


class DashboardViewTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="hamza", password="testpass123")
        self.url = "/api/elearning/dashboard/"

    def test_auth_required(self):
        """Anonymous users should not have access to the dashboard."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_dashboard_response_structure(self):
        """Authenticated users should receive valid dashboard data."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        # Check main keys
        expected_keys = {
            "greeting_name",
            "week_streak_days",
            "weekly_learning_hours",
            "modules_completed",
            "current_goal_percent",
            "active_modules",
            "upcoming_events",
        }
        self.assertTrue(expected_keys.issubset(data.keys()))

        # Check types
        self.assertIsInstance(data["week_streak_days"], int)
        self.assertIsInstance(data["weekly_learning_hours"], float)
        self.assertIsInstance(data["modules_completed"], int)
        self.assertIsInstance(data["current_goal_percent"], int)
        self.assertIsInstance(data["active_modules"], list)
        self.assertIsInstance(data["upcoming_events"], list)
