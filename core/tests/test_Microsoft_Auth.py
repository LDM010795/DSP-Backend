import secrets

from django.test import TestCase
from unittest import mock
from django.core.cache import cache
from rest_framework import status
from django.http import HttpResponseRedirect
from core.employees.models import Tool


class TestMicrosoftLoginRedirectView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tool = Tool.objects.create(
            slug="elearning",
            is_active=True,
            frontend_url="https://frontend.example.com",
        )

    def test_redirect_for_valid_tool(self):
        with (
            mock.patch(
                "core.microsoft_services.authentications.views.MicrosoftAuthClient"
            ) as mock_client_class,
        ):
            mock_client = mock_client_class.return_value
            mock_client.exchange_code_for_token.return_value = {
                "access_token": "access123"
            }
            mock_client.get_user_info.return_value = {"email": "user@example.com"}

            response = self.client.get(f"/api/microsoft/auth/login/{self.tool.slug}/")
            self.assertIsInstance(response, HttpResponseRedirect)

            # Parse state from redirect URL
            redirect_url = response.url
            from urllib.parse import urlparse, parse_qs

            query = parse_qs(urlparse(redirect_url).query)
            state = query["state"][0]

            # Now check cache
            cached_tool = cache.get(f"oauth_state_{state}")
            self.assertEqual(cached_tool, self.tool.slug)

    def test_invalid_tool_returns_404(self):
        response = self.client.get("/api/microsoft/auth/login/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TestMicrosoftCallbackView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tool = Tool.objects.create(
            slug="elearning",
            is_active=True,
            frontend_url="https://frontend.example.com",
        )

    def test_get_with_valid_state_redirects_to_frontend(self):
        state = "teststate123"
        cache.set(f"oauth_state_{state}", self.tool.slug, timeout=600)
        response = self.client.get(
            "/api/microsoft/auth/callback/", {"state": state, "code": "abc"}
        )
        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertIn(self.tool.frontend_url, response.url)
        self.assertIn("state=teststate123", response.url)

    def test_get_without_state_returns_400(self):
        response = self.client.get("/api/microsoft/auth/callback/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_with_invalid_state_returns_400(self):
        cache.clear()
        response = self.client.get(
            "/api/microsoft/auth/callback/", {"state": "invalidstate"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_successful_authentication_sets_cookies(self):
        state = secrets.token_urlsafe(32)
        cache.set(f"oauth_state_{state}", self.tool.slug, timeout=600)

        # Mock takes the MicrosoftAuthclient used inside the callback view and tells it what to return
        with (
            mock.patch(
                "core.microsoft_services.authentications.views.MicrosoftAuthClient"
            ) as mock_client_class,
            mock.patch(
                "core.microsoft_services.authentications.views.EmployeeAuthHandler"
            ) as mock_handler_class,
        ):
            mock_client = mock_client_class.return_value
            mock_client.exchange_code_for_token.return_value = {
                "access_token": "access123"
            }
            mock_client.get_user_info.return_value = {"email": "user@example.com"}

            mock_handler = mock_handler_class.return_value
            mock_handler.handle_authentication.return_value = {
                "user": {"email": "user@example.com"},
                "tokens": {"access": "jwt_access", "refresh": "jwt_refresh"},
            }

            response = self.client.post(
                "/api/microsoft/auth/callback/" + self.tool.slug + "/",
                {"code": "authcode", "state": state},
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.cookies["access_token"].value, "jwt_access")
            self.assertEqual(response.cookies["refresh_token"].value, "jwt_refresh")

    def test_post_missing_code_or_state_returns_400(self):
        response = self.client.post(
            "/api/microsoft/auth/callback/" + self.tool.slug + "/",
            {"code": "authcode"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.post(
            "/api/microsoft/auth/callback/" + self.tool.slug + "/",
            {"state": "abc"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_state_tool_mismatch_returns_400(self):
        cache.set("oauth_state_wrong", "other-tool", timeout=600)
        response = self.client.post(
            "/api/microsoft/auth/callback/" + self.tool.slug + "/",
            {"code": "authcode", "state": "wrong"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TestMicrosoftLogoutView(TestCase):
    def test_logout_success(self):
        url = "/api/microsoft/auth/logout/"
        refresh_token = "dummy_refresh_token"
        with mock.patch(
            "core.microsoft_services.authentications.views.RefreshToken"
        ) as mock_refresh:
            mock_token = mock_refresh.return_value
            mock_token.blacklist.return_value = None
            response = self.client.post(
                url, {"refresh": refresh_token}, content_type="application/json"
            )
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()["success"])

    def test_logout_missing_refresh_token_returns_400(self):
        url = "/api/microsoft/auth/logout/"
        response = self.client.post(url, {}, content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.json())

    def test_logout_invalid_token_returns_400(self):
        url = "/api/microsoft/auth/logout/"
        with mock.patch(
            "core.microsoft_services.authentications.views.RefreshToken"
        ) as mock_refresh:
            mock_refresh.side_effect = Exception("Invalid token")
            response = self.client.post(
                url, {"refresh": "badtoken"}, content_type="application/json"
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("error", response.json())
