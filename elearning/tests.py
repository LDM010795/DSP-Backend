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
from django.urls import reverse

from elearning.modules.models import Module, ModuleCategory
from elearning.modules.views import ModuleListViewPublic


# Create your tests here.
# 
# Future tests for:
# - User management and authentication
# - Module system and learning content
# - Examination system and certification
# - API endpoint validation
# - Integration tests for end-to-end workflows


class ModuleViewsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        category = ModuleCategory.objects.create(id=1, name="Python")
        Module.objects.get_or_create(
            title="Privates Modul",
            defaults={
                'is_public': False,
                'category': category,
            }
        )
        Module.objects.get_or_create(
            title="Public Modul",
            defaults={
                'is_public': True,
                'category': category,
            }
        )

        User.objects.get_or_create(
            username="Max",
            password="Musterpassword",
            email="Max@test.com",
            is_staff=False,
            is_superuser=False,
        )

    def setUp(self):
        self.client.login(username="Max", password="Musterpassword")

    def testModuleListIstErreichbar(self):
        response = self.client.get('/api/elearning/')
        print(response.content)
        self.assertEqual(response.status_code, 200)

