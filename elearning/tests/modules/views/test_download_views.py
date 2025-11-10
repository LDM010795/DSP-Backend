"""
Test Suite for Downloadable Resource Views
==========================================

Covers:
-------
- GET /api/modules/<module_id>/resources/
- Optional filtering by ?type=pdf, ?type=code, etc.

Ensure that the view returns only public resources for a module,
supports type filtering, and includes presigned download URLs
(via mocked WasabiService).

Author: DSP Development Team
Date: 11-07-2025
"""

from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

from elearning.modules.models import Module, ModuleCategory
from elearning.modules.models_downloads import DownloadableResource, ResourceType

User = get_user_model()


def reverse_module_resources(module_id: int) -> str:
    """Helper to reverse module resource endpoint"""
    return reverse(
        "elearning:modules:module-resources-list", kwargs={"module_id": module_id}
    )


def setup_module_and_category(cls):
    """Create a shared module and category for tests"""
    cls.category = ModuleCategory.objects.create(name="Python Basics")
    cls.module = Module.objects.create(
        title="Introduction to Python", category=cls.category, is_public=True
    )
    cls.other_module = Module.objects.create(
        title="Advanced Python", category=cls.category, is_public=True
    )


class TestModuleResourcesListView(TestCase):
    """
    Tests the API endpoint that lists downloadable resources per module.
    """

    @classmethod
    def setUpTestData(cls):
        setup_module_and_category(cls)
        cls.url = reverse_module_resources(cls.module.pk)

        # Create test resources
        cls.public_pdf = DownloadableResource.objects.create(
            title="Kapitel 1 Skript",
            description="Grundlagen PDF",
            module=cls.module,
            resource_type=ResourceType.PDF,
            cloud_key="Lerninhalte/Python/PDFs/skript1.pdf",
            is_public=True,
        )
        cls.public_code = DownloadableResource.objects.create(
            title="Beispielcode",
            description="Python Starter Code",
            module=cls.module,
            resource_type=ResourceType.CODE,
            cloud_key="Lerninhalte/Python/Code/intro.zip",
            is_public=True,
        )
        cls.private_doc = DownloadableResource.objects.create(
            title="Internes Dokument",
            description="Nicht öffentlich",
            module=cls.module,
            resource_type=ResourceType.OTHER,
            cloud_key="Lerninhalte/Python/Internal/internal.pdf",
            is_public=False,
        )
        cls.other_module_res = DownloadableResource.objects.create(
            title="Slides Fortgeschritten",
            description="Slides",
            module=cls.other_module,
            resource_type=ResourceType.SLIDES,
            cloud_key="Lerninhalte/Python/Slides/advanced.pdf",
            is_public=True,
        )

    def setUp(self):
        self.client = APIClient()

    @patch(
        "elearning.modules.serializers_downloads.WasabiService.generate_presigned_url"
    )
    def test_returns_only_public_resources_for_module(self, mock_presign):
        """Ensures only public module resources are returned and presigned URLs work."""
        mock_presign.return_value = "https://signed.example.com/file"

        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

        data = resp.json()
        self.assertEqual(len(data), 2)  # only 2 public from main module

        titles = [r["title"] for r in data]
        self.assertIn(self.public_pdf.title, titles)
        self.assertIn(self.public_code.title, titles)
        self.assertNotIn(self.private_doc.title, titles)
        self.assertNotIn(self.other_module_res.title, titles)

        for r in data:
            self.assertIn("download_url", r)
            self.assertEqual(r["download_url"], "https://signed.example.com/file")

    @patch(
        "elearning.modules.serializers_downloads.WasabiService.generate_presigned_url"
    )
    def test_filter_by_resource_type(self, mock_presign):
        """Supports filtering by ?type=pdf"""
        mock_presign.return_value = "https://signed.example.com/pdf"

        resp = self.client.get(f"{self.url}?type=pdf")
        self.assertEqual(resp.status_code, 200)

        data = resp.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["resource_type"], ResourceType.PDF)
        self.assertEqual(data[0]["title"], self.public_pdf.title)
        self.assertEqual(data[0]["download_url"], "https://signed.example.com/pdf")

    def test_empty_list_when_no_resources(self):
        """Returns an empty list for modules without resources"""
        empty_module = Module.objects.create(
            title="Empty Module", category=self.category, is_public=True
        )
        url = reverse_module_resources(empty_module.pk)

        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_invalid_module_id_returns_empty_list(self):
        """Handles nonexistent module_id gracefully"""
        resp = self.client.get(reverse_module_resources(9999))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    @patch(
        "elearning.modules.serializers_downloads.WasabiService.generate_presigned_url",
        side_effect=Exception("boom"),
    )
    def test_presigned_url_failure_returns_none(self, mock_presign):
        """If presigning fails, download_url should be None"""
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        for r in data:
            self.assertIsNone(r.get("download_url"))
