"""
E-Learning Tests - DSP (Digital Solutions Platform)

Dieses Modul enthält die Test-Suite für das E-Learning-System.
Aktuell als Platzhalter für zukünftige Tests implementiert.

Geplante Tests:
- Benutzerverwaltung und Authentifizierung
- Modul-System und Lerninhalte
- Prüfungssystem und Zertifizierung
- API-Endpoint-Validierung
- Integrationstests für End-to-End-Workflows

Author: DSP Development Team
Created: 10.07.2025
Version: 1.0.0
"""

from django.test import TestCase

from django.contrib.auth.models import User

from elearning.modules.models import Module, ModuleCategory


# Create your tests here.
#
# Future tests for:
# - User management and authentication
# - Module system and learning content
# - Examination system and certification
# - API endpoint validation
# - Integration tests for end-to-end workflows


class ModuleViewsTests(TestCase):
    # This setup is only executed once for the entire testfile
    @classmethod
    def setUpTestData(cls):
        category = ModuleCategory.objects.create(id=1, name="Python")
        Module.objects.get_or_create(
            title="Privates Modul",
            defaults={
                "is_public": False,
                "category": category,
            },
        )
        Module.objects.get_or_create(
            title="Public Modul",
            defaults={
                "is_public": True,
                "category": category,
            },
        )

        testuser = User.objects.create_user(
            username="Max",
            password="Musterpassword",
            email="Max@test.com",
            is_staff=False,
            is_superuser=False,
        )
        testuser.save()

    # This setup is executed before each indivitual test
    # def setUp(self):

    def testPublicModuleListIstErreichbar(self):
        # Route has to be checked at backend/urls combined with elearning/urls
        response = self.client.get("/api/elearning/modules/public/")
        self.assertEqual(response.status_code, 200)

    def testPublicModuleListHatInhalt(self):
        # Check if module in database and model reachable by API are same, in this case by checking if the category name is the same
        response = self.client.get("/api/elearning/modules/public/")
        self.assertEqual(
            Module.objects.get(title="Public Modul").category.name,
            response.json()[0]["category"]["name"],
        )

    def testPrivateModuleListHatInhalt(self):
        # TODO: fix this test
        self.client.login(username="Max", password="Musterpassword")
        response = self.client.get("/api/elearning/modules/user/")
        print(response.content)
