from datetime import datetime
from unittest.mock import patch

from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from elearning.users.models import Profile
from elearning.users.serializers import SetInitialPasswordSerializer

"""
    Test Script für die Token generierung, richtige Formatierung und für das neue Ausstellen von Access Tokens
    Token werden für den Login benötigt.
"""


class TestLogoutView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="testUser", password="testPassword", email="testUser@gmail.com"
        )
        cls.logout_url = reverse("elearning:users:logout")

    def setUp(self):
        response = self.client.post(
            reverse("elearning:token_obtain_pair"),
            {"username": "testUser", "password": "testPassword"},
        )
        self.access_token = response.cookies.get("access_token")
        self.refresh_token = response.cookies.get("refresh_token")

    def test_logout_invalidates_refresh_token(self):
        self.client.cookies["access_token"] = self.access_token
        self.client.cookies["refresh_token"] = self.refresh_token
        response = self.client.post(self.logout_url)

        # access token and refresh token deleted?
        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)
        self.assertEqual(response.cookies.get("access_token").value, "")
        self.assertEqual(response.cookies.get("refresh_token").value, "")
        self.assertEqual(response.json()["detail"], "Successfully logged out.")

        # refresh token invalid?
        self.client.cookies["refresh_token"] = self.refresh_token
        try_refresh_response = self.client.post(reverse("elearning:token_refresh"))

        self.assertEqual(try_refresh_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", try_refresh_response.json())
        self.assertEqual(
            try_refresh_response.json()["detail"], "Token steht auf der Blacklist"
        )

    def test_logout_without_tokens(self):
        self.client.cookies.clear()
        response = self.client.post(self.logout_url)

        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)
        self.assertEqual(response.json()["detail"], "Successfully logged out.")
        self.assertEqual(response.cookies.get("access_token").value, "")
        self.assertEqual(response.cookies.get("refresh_token").value, "")

    def test_logout_only_invalidates_one_token(self):
        # Tokens aus dem TestSetup
        access_token_1 = self.access_token
        refresh_token_1 = self.refresh_token

        # Zweites access- und refresh-Token holen
        second_token_response = self.client.post(
            reverse("elearning:token_obtain_pair"),
            {"username": "testUser", "password": "testPassword"},
        )
        refresh_token_2 = second_token_response.cookies.get("refresh_token")

        # logout mit access_token_2 und refresh_token_2
        response_logout = self.client.post(self.logout_url)
        self.assertEqual(response_logout.status_code, status.HTTP_205_RESET_CONTENT)
        self.assertEqual(response_logout.json()["detail"], "Successfully logged out.")
        self.assertEqual(response_logout.cookies["refresh_token"].value, "")
        self.assertEqual(response_logout.cookies["access_token"].value, "")

        # prüfen, dass refresh_token_2 invalidiert wurde
        self.client.cookies["refresh_token"] = refresh_token_2
        response_token_refresh = self.client.post(reverse("elearning:token_refresh"))

        self.assertEqual(
            response_token_refresh.status_code, status.HTTP_400_BAD_REQUEST
        )
        self.assertIn("detail", response_token_refresh.json())
        self.assertEqual(
            response_token_refresh.json()["detail"], "Token steht auf der Blacklist"
        )

        # prüfen, dass access_token_1 noch gültig ist
        self.client.cookies["access_token"] = access_token_1
        response_users_me = self.client.get(reverse("elearning:users:current_user"))
        self.assertEqual(response_users_me.status_code, status.HTTP_200_OK)

        # prüfen, dass refresh_token_1 noch gültig ist
        self.client.cookies["refresh_token"] = refresh_token_1
        response_token_refresh = self.client.post(reverse("elearning:token_refresh"))
        self.assertEqual(response_token_refresh.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response_token_refresh.cookies["access_token"])

    def test_logout_sets_httponly_cookie_flags(self):
        # logout needs to specify the same httponly flags, otherwise the cookies won't be deleted
        self.client.cookies["access_token"] = self.access_token
        self.client.cookies["refresh_token"] = self.refresh_token

        response = self.client.post(self.logout_url)

        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)
        cookies = response.cookies

        # ---- Access Token ----
        self.assertIn("access_token", cookies)
        self.assertIn(cookies["access_token"].value, ("", None))
        self.assertTrue(cookies["access_token"]["httponly"])
        self.assertTrue(cookies["access_token"]["secure"])
        self.assertEqual(cookies["access_token"]["samesite"], "None")

        # ---- Refresh Token ----
        self.assertIn("refresh_token", cookies)
        self.assertIn(cookies["refresh_token"].value, ("", None))
        self.assertTrue(cookies["refresh_token"]["httponly"])
        self.assertTrue(cookies["refresh_token"]["secure"])
        self.assertEqual(cookies["refresh_token"]["samesite"], "None")

        # zusätzlich Detail-Message prüfen
        self.assertEqual(response.json()["detail"], "Successfully logged out.")

    def test_logout_method_not_allowed(self):
        # nur POST ist auf /logout/ erlaubt

        response_get = self.client.get(self.logout_url)
        response_put = self.client.put(self.logout_url)
        response_delete = self.client.delete(self.logout_url)

        self.assertEqual(response_get.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(response_put.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(
            response_delete.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )


class TestSetInitialPasswordView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="testUser",
            password="testPassword",
            email="max.mustermann@example.com",
        )

    def setUp(self):
        # cookies setzen
        self.client.post(
            reverse("elearning:token_obtain_pair"),
            {"username": "testUser", "password": "testPassword"},
        )

    def post_initial_password_request(self, password, password_confirm):
        response = self.client.post(
            reverse("elearning:users:set_initial_password"),
            {"password": password, "password_confirm": password_confirm},
        )
        return response

    def test_happy_path(self):
        response = self.post_initial_password_request("NewPass456!", "NewPass456!")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["detail"], "Password successfully set.")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPass456!"))

    def test_not_authenticated(self):
        self.client.cookies.clear()
        response = self.post_initial_password_request("n59bfdsÜ!c", "n59bfdsÜ!c")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_empty_passwords(self):
        response = self.post_initial_password_request("", "")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_weak_password_rejected(self):
        response = self.post_initial_password_request("123", "123")  # too weak
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_passwords_dont_match(self):
        response = self.post_initial_password_request("n59bfdsÜ!c", "N38jZ7#!aAC")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password_confirm", response.json())

    def test_password_case_mismatch(self):
        response = self.post_initial_password_request("n59bfdsÜ!c", "N59BFDSÜ!C")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password_confirm", response.json())

    def test_validate_username_similarity(self):
        # Passwort ähnlich zu Username → 400
        response = self.post_initial_password_request("userTest", "userTest")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_validate_email_similarity(self):
        # Email ähnlich zu Username → 400
        response = self.post_initial_password_request(
            password="mustermann123", password_confirm="mustermann123"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_validate_minimum_length(self):
        # Passwort < 8 Zeichen → 400
        response = self.post_initial_password_request("Ab1$534", "Ab1$534")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_validate_common_password(self):
        # Passwort aus Common-Password-Liste → 400
        response = self.post_initial_password_request("password", "password")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_validate_numeric_password(self):
        # Nur Zahlen → 400
        response = self.post_initial_password_request("564832908964", "564832908964")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_set_initial_password_already_set(self):
        profile = Profile.objects.get(user=self.user)
        profile.force_password_change = False
        profile.save()
        response = self.post_initial_password_request("whatever123!", "whatever123!")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Password has already been set.", response.json()["detail"])

    def test_serializer_save_exception(self):
        # Mock Exception bei SetInitialPasswordSerializer.save()
        serializer = SetInitialPasswordSerializer
        serializer_save_method = f"{serializer.__module__}.{serializer.__name__}.save"
        with patch(serializer_save_method, side_effect=Exception):
            response = self.post_initial_password_request("X7!kLp9$zR", "X7!kLp9$zR")
            self.assertEqual(
                response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def test_missing_profile_creation(self):
        # self.user.profile.delete()  # Profil löschen, falls vorhanden
        response = self.post_initial_password_request("X7!kLp9$zR", "X7!kLp9$zR")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unicode_password(self):
        response = self.post_initial_password_request(
            "PaßwördÜñîçødë7!", "PaßwördÜñîçødë7!"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TestExternalUserRegistrationView(TestCase):
    def post_register_request(
        self,
        username="testUser",
        email="testUser@gmail.com",
        first_name="Max",
        last_name="Mustermann",
        password="X7!kLp9$zR",
        password_confirm="X7!kLp9$zR",
    ):
        response = self.client.post(
            reverse("elearning:users:external-register"),
            {
                "username": username,
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "password": password,
                "password_confirm": password_confirm,
            },
        )
        return response

    def test_happy_path(self):
        response = self.post_register_request()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["detail"], "Registration successful.")

    def test_username_already_exists(self):
        # User registrieren
        self.post_register_request()

        # 2. User mit gleichem Username registrieren
        response = self.post_register_request(email="testUserNeu@gmail.com")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Dieser Benutzername ist bereits vergeben.", response.json()["username"]
        )

    def test_email_already_exists(self):
        # User registrieren
        self.post_register_request()

        # 2. User mit gleicher E-Mail registrieren
        response = self.post_register_request(username="testUser2")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "A user with this email already exists.", response.json()["email"]
        )

    def test_invalid_email_format(self):
        response = self.post_register_request(email="not-an-email")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Gib eine gültige E-Mail Adresse an.", response.json()["email"])

    def test_empty_passwords(self):
        response = self.post_register_request(password="", password_confirm="")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Dieses Feld darf nicht leer sein.", response.json()["password"])
        self.assertIn(
            "Dieses Feld darf nicht leer sein.", response.json()["password_confirm"]
        )

    def test_passwords_dont_match(self):
        response = self.post_register_request(
            password="X7!kLp9$zR", password_confirm="g&2ah(8g2"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_case_mismatch(self):
        response = self.post_register_request(
            password="n59bfdsÜ!c", password_confirm="N59BFDSÜ!C"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Passwords do not match", response.json()["password_confirm"])

    def test_validate_username_similarity(self):
        # Passwort ähnlich zu Username → 400
        response = self.post_register_request(
            username="testUser", password="userTest", password_confirm="userTest"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_validate_email_similarity(self):
        # Passwort ähnlich zu Email → 400
        response = self.post_register_request(
            email="max.mustermann@example.com",
            password="mustermann123",
            password_confirm="mustermann123",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_validate_minimum_length(self):
        # Passwort < 8 Zeichen → 400
        response = self.post_register_request(
            password="Ab1$534", password_confirm="Ab1$534"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Stelle sicher, dass dieses Feld mindestens 8 Zeichen lang ist.",
            response.json()["password"],
        )
        self.assertIn(
            "Stelle sicher, dass dieses Feld mindestens 8 Zeichen lang ist.",
            response.json()["password_confirm"],
        )

    def test_validate_common_password(self):
        # Passwort aus Common-Password-Liste → 400
        response = self.post_register_request(
            password="password", password_confirm="password"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_validate_numeric_password(self):
        # Nur Zahlen → 400
        response = self.post_register_request(
            password="564832908964", password_confirm="564832908964"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TokenTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="testUser", password="testPassword"
        )
        cls.obtain_token_url = reverse("elearning:token_obtain_pair")
        cls.refresh_token_url = reverse("elearning:token_refresh")

    # can't be classmethod, client is only available if it runs every time
    def setUp(self):
        response = self.client.post(
            self.obtain_token_url,
            {"username": "testUser", "password": "testPassword"},
        )
        self.cookies = response.cookies
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
        response = self.client.post(self.refresh_token_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.cookies["access_token"])

    def test_refresh_token_failure(self):
        self.client.cookies["refresh_token"] = "bad token"
        response = self.client.post(self.refresh_token_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_refresh_token_missing(self):
        del self.client.cookies["refresh_token"]
        response = self.client.post(self.refresh_token_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logout_clears_cookies(self):
        response = self.client.post(reverse("elearning:users:logout"))
        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)
        # fmt: off
        # this might be broken by auto formating
        self.assertEqual("", response.cookies["access_token"].value)
        self.assertEqual("", response.cookies["refresh_token"].value)
        # fmt:on

    def test_refresh_token_expired_manual(self):
        token = RefreshToken.for_user(
            self.user
        )  # generate a new refresh token, since the expiration date set inside the token is checked
        # Force expiration in the past
        token.payload["exp"] = datetime(1970, 1, 1)

        self.client.cookies["refresh_token"] = str(token)
        response = self.client.post(self.refresh_token_url)
        self.assertEqual(response.status_code, 400)

    def test_wrong_login_rejected(self):
        response = self.client.post(
            self.obtain_token_url,
            {"username": "testUser", "password": "wrongPassword"},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn("access_token", response.cookies)
        self.assertNotIn("refresh_token", response.cookies)

    def test_tokens_have_correct_flags_on_login(self):
        self.assertTrue(self.cookies["access_token"]["httponly"])
        self.assertTrue(self.cookies["access_token"]["secure"])
        self.assertTrue(self.cookies["refresh_token"]["httponly"])
        self.assertTrue(self.cookies["refresh_token"]["secure"])

    def test_tokens_have_correct_flags_on_refresh(self):
        self.client.cookies["refresh_token"] = self.refresh_token
        response = self.client.post(self.refresh_token_url)
        self.assertTrue(response.cookies["access_token"]["httponly"])
        self.assertTrue(response.cookies["access_token"]["secure"])
        self.assertTrue(response.cookies["refresh_token"]["httponly"])
        self.assertTrue(response.cookies["refresh_token"]["secure"])
