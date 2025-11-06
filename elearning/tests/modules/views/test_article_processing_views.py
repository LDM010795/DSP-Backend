from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from unittest import mock


class ProcessArticleFromCloudTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="max.mustermann",
            password="34gf75!a",
            email="mustermann123@gmail.com",
            first_name="Max",
            last_name="Mustermann",
        )
        cls.url = reverse("elearning:modules:process-article-from-cloud")

    def setUp(self):
        self.client.post(
            reverse("elearning:token_obtain_pair"),
            {"username": "max.mustermann", "password": "34gf75!a"},
        )

    def test_missing_module_id(self):
        response = self.client.post(self.url, {"cloudUrl": "http://valid-url.com", "chapterId": 1})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("moduleId ist erforderlich", response.data["error"])

    def test_missing_chapter_id(self):
        response = self.client.post(self.url, {"cloudUrl": "http://valid-url.com", "moduleId": 1})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("chapterId ist erforderlich", response.data["error"])

    def test_missing_cloud_url(self):
        response = self.client.post(self.url, {"moduleId": 1, "chapterId": 1})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cloudUrl ist erforderlich", response.data["error"])

    def test_invalid_cloud_url(self):
        response = self.client.post(self.url, {"moduleId": 1, "chapterId": 1, "cloudUrl": "bad-url"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Ungültige Cloud-URL", response.data["error"])

    def test_successful_processing(self):
        with mock.patch(
            "elearning.modules.views.article_processing_views.ArticleProcessingService"
        ) as MockService:
            mock_service = MockService.return_value
            mock_service.validate_cloud_url.return_value = {"valid": True}
            mock_result = mock.MagicMock()
            mock_result.success = True
            mock_result.article_title = "Test Title"
            mock_result.article_id = 123
            mock_result.images_found = ["IMG1"]
            mock_result.images_saved = 1
            mock_result.errors = []
            mock_result.warnings = []
            mock_service.process_article_from_cloud_url.return_value = mock_result

            response = self.client.post(
                self.url, {"moduleId": 1, "chapterId": 1, "cloudUrl": "http://valid-url.com"}
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["article_title"], "Test Title")

    def test_failed_processing(self):
        with mock.patch(
            "elearning.modules.views.article_processing_views.ArticleProcessingService"
        ) as MockService:
            mock_service = MockService.return_value
            mock_service.validate_cloud_url.return_value = {"valid": True}
            mock_result = mock.MagicMock()
            mock_result.success = False
            mock_result.article_title = None
            mock_result.article_id = None
            mock_result.images_found = []
            mock_result.images_saved = 0
            mock_result.errors = ["processing error"]
            mock_result.warnings = []
            mock_service.process_article_from_cloud_url.return_value = mock_result

            response = self.client.post(
                self.url, {"moduleId": 1, "chapterId": 1, "cloudUrl": "http://valid-url.com"}
            )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertIn("processing error", response.data["errors"])


class ValidateCloudUrlTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="max.mustermann",
            password="34gf75!a",
            email="mustermann123@gmail.com",
            first_name="Max",
            last_name="Mustermann",
        )
        cls.url = reverse("elearning:modules:process-article-from-cloud")

    def setUp(self):
        self.client.post(
            reverse("elearning:token_obtain_pair"),
            {"username": "max.mustermann", "password": "34gf75!a"},
        )

    def test_missing_cloud_url(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("moduleId ist erforderlich", response.data["error"])

    def test_valid_cloud_url(self):
        with mock.patch(
            "elearning.modules.views.article_processing_views.ArticleProcessingService"
        ) as MockService:
            mock_service = MockService.return_value
            validation_result = {
                "valid": True,
                "parsed_info": {"bucket_name": "bucket"},
            }
            mock_service.validate_cloud_url.return_value = validation_result
            mock_result = mock.MagicMock()
            mock_result.success = True
            mock_result.article_title = "Testartikel"
            mock_result.article_id = 123
            mock_result.images_found = ["img1.png", "img2.png"]
            mock_result.images_saved = 2
            mock_result.errors = []
            mock_result.warnings = []
            mock_service.process_article_from_cloud_url.return_value = mock_result
            response = self.client.post(
                self.url, {"cloudUrl": "http://valid-url.com", "moduleId": "1", "chapterId": "1"}
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["success"], True)
        self.assertEqual(response.data["article_title"], "Testartikel")
        self.assertEqual(response.data["article_id"], 123)
        self.assertEqual(response.data["images_found"], ["img1.png", "img2.png"])
        self.assertEqual(response.data["images_saved"], 2)
        self.assertEqual(response.data["errors"], [])
        self.assertEqual(response.data["warnings"], [])

    def test_exception_handling(self):
        with mock.patch(
            "elearning.modules.views.article_processing_views.ArticleProcessingService"
        ) as MockService:
            MockService.side_effect = Exception("unexpected error")
            response = self.client.post(
                self.url, {"cloudUrl": "http://valid-url.com", "moduleId": "1", "chapterId": "1"}
            )
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
