from datetime import datetime, timezone, timedelta

from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from elearning.users.models import Profile

"""
    Test Script für die Token generierung, richtige Formatierung und für das neue Ausstellen von Access Tokens
    Token werden für den Login benötigt.
"""


class TokenTests(TestCase):
    # can't be classmethod, client is only available if it runs every time
    def setUp(self):
        self.user = User.objects.create_user(
            username="testUser", password="testPassword"
        )
        response = self.client.post(
            "/api/elearning/token/",
            {"username": "testUser", "password": "testPassword"},
        )
        self.access_token = response.cookies["access_token"].value
        self.refresh_token = response.cookies["refresh_token"].value
        self.body = response.json()

        if response.status_code != status.HTTP_200_OK:
            raise Exception(response.json())

    def test_no_JWT(self):
        # wir haben keine JWT mehr
        self.assertEqual(self.body, {})

    def test_refresh_token_success(self):
        self.client.cookies["refresh_token"] = self.refresh_token
        response = self.client.post("/api/elearning/token/refresh/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.cookies["access_token"])

    def test_refresh_token_failure(self):
        self.client.cookies["refresh_token"] = "bad token"
        response = self.client.post("/api/elearning/token/refresh/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_refresh_token_missing(self):
        del self.client.cookies["refresh_token"]
        response = self.client.post("/api/elearning/token/refresh/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logout_clears_cookies(self):
        response = self.client.post("/api/elearning/users/logout/")
        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)
        # fmt: off
        # this might be broken by auto formating
        self.assertEqual("", response.cookies["access_token"].value)
        self.assertEqual("", response.cookies["refresh_token"].value)
        # fmt:on

    def test_refresh_token_expired_manual(self):
        token = RefreshToken.for_user(self.user) #generate a new refresh token, since the expiration date set inside the token is checked
        # Force expiration in the past
        token.payload["exp"] = datetime(1970, 1, 1)

        self.client.cookies["refresh_token"] = str(token)
        response = self.client.post("/api/elearning/token/refresh/")
        self.assertEqual(response.status_code, 400)

    def test_wrong_login_rejected(self):
        response = self.client.post(
            "/api/elearning/token/",
            {"username": "testUser", "password": "wrongPassword"},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn("access_token", response.cookies)
        self.assertNotIn("refresh_token", response.cookies)
class PasswordTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testUser", password="testPassword"
        )
        response = self.client.post(
            "/api/elearning/token/",
            {"username": "testUser", "password": "testPassword"},
        )
        self.access_token = response.cookies["access_token"].value
        self.refresh_token = response.cookies["refresh_token"].value
        self.body = response.json()

    def test_weak_password_rejected(self):
        payload = {"password": "123", "password_confirm": "123"}  # too weak
        response = self.client.post("/api/elearning/users/set-initial-password/", payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_set_initial_password_success(self):
        payload = {"password": "NewPass456!", "password_confirm": "NewPass456!"}
        response = self.client.post("/api/elearning/users/set-initial-password/", payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["detail"], "Password successfully set.")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPass456!"))

    def test_set_initial_password_already_set(self):
        profile = Profile.objects.get(user=self.user)
        profile.force_password_change = False
        profile.save()
        payload = {"password": "whatever123!", "password_confirm": "whatever123!"}
        response = self.client.post("/api/elearning/users/set-initial-password/", payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Password has already been set.", response.json()["detail"])

    def test_set_initial_password_mismatch(self):
        payload = {"password": "OnePass123!", "password_confirm": "OtherPass123!"}
        response = self.client.post("/api/elearning/users/set-initial-password/", payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password_confirm", response.json())

class ExternalRegistrationTests(TestCase):
    def test_registration_success(self):
        payload = {
            "username": "newuser",
            "email": "new@example.com",
            "first_name": "New",
            "last_name": "User",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
        }
        response = self.client.post("/api/elearning/users/register/", payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_registration_failure(self):
        User.objects.create_user(username="dup", email="dup@example.com", password="abc123!")
        payload = {
            "username": "dup",
            "email": "dup@example.com",
            "password": "StrongPass123!",
            "password_confirm": "WrongConfirm123!",
        }
        response = self.client.post("/api/elearning/users/register/", payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)