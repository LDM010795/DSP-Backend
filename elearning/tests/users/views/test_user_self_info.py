from django.test import TestCase

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status


class TestCurrentUserView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="max.mustermann",
            password="34gf75!a",
            email="mustermann123@gmail.com",
            first_name="Max",
            last_name="Mustermann",
        )

        cls.url_current_user = reverse("elearning:users:current_user")

    def setUp(self):
        # authenticate
        self.client.post(
            reverse("elearning:token_obtain_pair"),
            {"username": "max.mustermann", "password": "34gf75!a"},
        )

    def test_happy_path(self):
        response = self.client.get(self.url_current_user)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["username"], "max.mustermann")
        self.assertEqual(response.json()["email"], "mustermann123@gmail.com")
        self.assertEqual(response.json()["first_name"], "Max")
        self.assertEqual(response.json()["last_name"], "Mustermann")
        self.assertEqual(response.json()["full_name"], "Max Mustermann")

    def test_not_authenticated(self):
        self.client.cookies.pop("access_token")
        self.client.cookies.pop("refresh_token")
        response = self.client.get(self.url_current_user)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_multiple_users(self):
        User.objects.create_user(
            username="jane.doe", password="abc123!A", email="jane.doe@gmail.com"
        )
        response = self.client.get(self.url_current_user)

        self.assertEqual(response.json()["username"], self.user.username)
        self.assertEqual(response.json()["email"], self.user.email)

    def test_response_fields(self):
        response = self.client.get(self.url_current_user)
        expected_fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "is_staff",
            "is_superuser",
            "is_active",
            "date_joined",
            "last_login",
            "force_password_change",
        ]
        for field in expected_fields:
            self.assertIn(field, response.json())
