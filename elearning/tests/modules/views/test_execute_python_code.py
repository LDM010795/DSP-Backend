from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status

from elearning.modules.models import Task

User = get_user_model()


class TestExecutePythonCodeView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="testUser", password="testPassword", email="testUser@gmail.com"
        )
        cls.task_without_testcase = Task.objects.create(title="Titel des Tasks")
        cls.task_with_testcase = Task.objects.create(
            title="Titel des Tasks",
            test_file_path="tests\\modules\\views\\test-scripts\\test-case-1.py",
        )

        cls.execute_python_url = reverse("elearning:modules:execute-python-code")

    def setUp(self):
        # authenticate
        self.client.post(
            reverse("elearning:token_obtain_pair"),
            {"username": "testUser", "password": "testPassword"},
        )

    def test_not_authenticated(self):
        self.client.cookies.clear()
        response = self.client.post(self.execute_python_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_task_id_invalid(self):
        response = self.client.post(
            self.execute_python_url, {"code": "print('Hello World')", "task_id": 9999}
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        print(response.json())

    def test_no_test_case_for_task(self):
        response = self.client.post(
            self.execute_python_url,
            {"code": "print('Hello World')", "task_id": self.task_without_testcase.pk},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["error"], "Für diese Aufgabe ist kein Testfall hinterlegt."
        )

    def test_python_test_case_file_not_existing(self):
        response = self.client.post(
            self.execute_python_url,
            {"code": "print('Hello World')", "task_id": self.task_with_testcase.pk},
        )
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(
            response.json()["error"],
            f"Testfall-Datei nicht gefunden unter: {self.task_with_testcase.test_file_path}",
        )
