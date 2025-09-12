from django.db import IntegrityError
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status

from elearning.final_exam.models import CertificationPath, Exam


class CertificationPathViewSetTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="testUser", password="password123")

        cls.cert_path_1 = CertificationPath.objects.create(
            title="Pfad A",
            description="Beschreibung für Pfad A",
            order=2,
            icon_name="IoCodeSlashOutline",
        )
        cls.cert_path_1.exams.add(Exam.objects.create(title="Exam 1", duration_weeks=3))

        cls.cert_path_2 = CertificationPath.objects.create(
            title="Pfad B",
            description="Beschreibung für Pfad B",
            order=3,
            icon_name="IoRocketOutline",
        )
        cls.cert_path_2.exams.add(
            Exam.objects.create(title="Exam 2", duration_weeks=5),
            Exam.objects.create(title="Exam 3", duration_weeks=1),
        )

        cls.cert_path_url = reverse("elearning:exams:certification-path-list")

    def setUp(self):
        self.client.post(
            reverse("elearning:token_obtain_pair"),
            {"username": "testUser", "password": "password123"},
        )

    # --- Berechtigungen --------------------------------------------------------

    def test_list_requires_authentication(self):
        self.client.cookies.clear()
        response = self.client.get(self.cert_path_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_can_access_list(self):
        response = self.client.get(self.cert_path_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 2)

    # --- LIST Endpoint ---------------------------------------------------------

    def test_list_returns_empty_when_no_paths(self):
        CertificationPath.objects.all().delete()
        response = self.client.get(self.cert_path_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_list_includes_serializer_fields(self):
        response = self.client.get(self.cert_path_url)

        path_a = next(item for item in response.json() if item["title"] == "Pfad A")
        path_b = next(item for item in response.json() if item["title"] == "Pfad B")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Pfad A prüfen
        self.assertEqual(path_a["description"], "Beschreibung für Pfad A")
        self.assertEqual(path_a["icon"], "IoCodeSlashOutline")
        self.assertEqual(path_a["order"], 2)
        self.assertEqual(len(path_a["exams"]), 1)
        self.assertEqual(path_a["exams"][0]["exam_title"], "Exam 1")

        # Pfad B prüfen
        self.assertEqual(path_b["description"], "Beschreibung für Pfad B")
        self.assertEqual(path_b["icon"], "IoRocketOutline")
        self.assertEqual(path_b["order"], 3)
        self.assertEqual(len(path_b["exams"]), 2)
        self.assertEqual(path_b["exams"][0]["exam_title"], "Exam 2")
        self.assertEqual(path_b["exams"][1]["exam_title"], "Exam 3")

    def test_list_returns_ordered_paths(self):
        CertificationPath.objects.create(
            title="Pfad C",
            order=1,
        )

        response = self.client.get(self.cert_path_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [p["title"] for p in response.json()]
        self.assertEqual(
            titles,
            [
                "Pfad C",
                "Pfad A",
                "Pfad B",
            ],
        )  # nach order sortiert

    # --- Extras ----------------------------------------------------------------
    def test_unique_title_constraint(self):
        CertificationPath.objects.create(title="Unique Title")

        with self.assertRaises(IntegrityError):
            CertificationPath.objects.create(title="Unique Title")
