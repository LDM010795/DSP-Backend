from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework import status

"""
    Test Script für die Token generierung, richtige Formatierung und für das neue Ausstellen von Access Tokens
    Token werden für den Login benötigt.
"""

class TokenTests(TestCase):
    @classmethod
    def setUp(cls):
        cls.user = User.objects.create_user(username='testUser', password='testPassword')
        response = cls.client.post("/api/elearning/token/", {"username": "testUser", "password": "testPassword"})
        cls.access_token = response.cookies.get("access_token")
        cls.refresh_token = response.cookies.get("refresh_token")
        cls.body = response.json()


    def test_no_JWT(self):
        self.assertIsNone(self.body)

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