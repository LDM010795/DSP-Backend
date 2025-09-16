from types import SimpleNamespace
from unittest import mock

from django.test import TestCase
from unittest.mock import MagicMock

from elearning.services.content_processing import article_processing_service


class ArticleProcessingServiceTests(TestCase):
    def setUp(self):
        self.service = article_processing_service.ArticleProcessingService()

    def test_parse_cloud_url_valid(self):
        url = "https://s3.eu-central-2.wasabisys.com/dsp-e-learning/Lerninhalte/SQL/Artikel/test.docx"
        result = self.service._parse_cloud_url(url)
        self.assertIsNotNone(result)
        self.assertEqual(result["file_name"], "test.docx")
        self.assertEqual(result["module_name"], "SQL")

    def test_parse_cloud_url_invalid(self):
        url = "https://s3.eu-central-2.wasabisys.com/invalid"
        result = self.service._parse_cloud_url(url)
        self.assertIsNone(result)

    def test_extract_images_from_json(self):
        json_content = {
            "content": [
                {"type": "image", "src": "image1.png"},
                {"type": "text", "value": "Hello"},
                {"type": "image", "src": "image2.jpg"},
            ]
        }
        images = self.service._extract_images_from_json(json_content)
        self.assertEqual(images, ["image1", "image2"])

    def test_process_article_from_cloud_url_success(self):
        with (
            mock.patch(
                "elearning.services.content_processing.article_processing_service.CloudStorageService"
            ) as mock_cloud,
            mock.patch(
                "elearning.services.content_processing.article_processing_service.WordProcessingService"
            ) as mock_word,
            mock.patch(
                "elearning.services.content_processing.article_processing_service.DatabaseService"
            ) as mock_db,
        ):
            self.service = article_processing_service.ArticleProcessingService()
            # Mock cloud download
            mock_cloud.download_file_content.return_value = b"fake-docx-content"

            # Mock word processing result
            mock_article = MagicMock()
            mock_article.title = "Test Article"
            mock_article.json_content = {
                "content": [{"type": "image", "src": "img1.png"}]
            }
            mock_word.return_value.process_word_document.return_value = mock_article

            # Mock DB module and save
            mock_module = MagicMock()
            mock_module.title = "ModuleTitle"
            mock_db.return_value.get_module_by_id.return_value = mock_module
            fake_image = SimpleNamespace(images=[SimpleNamespace(name="img1", url="img.com"),])
            mock_cloud.return_value.get_module_content.return_value = fake_image
            saved_article = MagicMock()
            saved_article.id = 123
            mock_db.return_value.save_processed_articles.return_value = [saved_article]
            mock_db.return_value.save_article_images.return_value = "1" #self.logger.info(f"{len(saved_images)} Bilder für Artikel gespeichert")

            result = self.service.process_article_from_cloud_url(
                module_id=1,
                cloud_url="https://s3.eu-central-2.wasabisys.com/dsp-e-learning/Lerninhalte/SQL/Artikel/test.docx",
            )

            print(result)
            self.assertTrue(result.success)
            self.assertEqual(result.article_title, "Test Article")
            self.assertEqual(result.article_id, 123)
            self.assertEqual(result.images_found, ["img1"])
            self.assertEqual(result.images_saved, 1)


    def test_process_article_download_fail(self):
        with (
            mock.patch(
                "elearning.services.content_processing.article_processing_service.CloudStorageService"
            ) as mock_cloud,
        ):
            self.service = article_processing_service.ArticleProcessingService()
            mock_cloud.return_value.download_file_content.return_value = None

            result = self.service.process_article_from_cloud_url(
                1,
                "https://s3.eu-central-2.wasabisys.com/dsp-e-learning/Lerninhalte/SQL/Artikel/test.docx",
            )
            self.assertFalse(result.success)
            self.assertIn("Konnte Word-Dokument nicht herunterladen", result.errors)


    def test_process_article_word_processing_fail(self):
        with (
            mock.patch(
                "elearning.services.content_processing.article_processing_service.CloudStorageService"
            ) as mock_cloud,
            mock.patch(
                "elearning.services.content_processing.article_processing_service.WordProcessingService"
            ) as mock_word,
        ):
            self.service = article_processing_service.ArticleProcessingService()
            mock_cloud.return_value.download_file_content.return_value = b"data"

            mock_word.return_value.process_word_document.return_value = None
            result = self.service.process_article_from_cloud_url(
                1,
                "https://s3.eu-central-2.wasabisys.com/dsp-e-learning/Lerninhalte/SQL/Artikel/test.docx",
            )
            self.assertFalse(result.success)
            self.assertIn("Fehler bei der Word-Dokument-Verarbeitung", result.errors)

    def test_process_article_module_not_found(self):
        with (
            mock.patch(
                "elearning.services.content_processing.article_processing_service.CloudStorageService"
            ) as mock_cloud,
            mock.patch(
                "elearning.services.content_processing.article_processing_service.WordProcessingService"
            ) as mock_word,
            mock.patch(
                "elearning.services.content_processing.article_processing_service.DatabaseService"
            ) as mock_db,
        ):
            self.service = article_processing_service.ArticleProcessingService()
            mock_cloud.return_value.download_file_content.return_value = b"data"

            mock_article = MagicMock()
            mock_article.title = "Title"
            mock_article.json_content = {"content": []}
            mock_word.return_value.process_word_document.return_value = mock_article
            mock_db.return_value.get_module_by_id.return_value = None

            result = self.service.process_article_from_cloud_url(
                99,
                "https://s3.eu-central-2.wasabisys.com/dsp-e-learning/Lerninhalte/SQL/Artikel/test.docx",
            )
            self.assertFalse(result.success)
            self.assertIn("Modul mit ID 99 nicht gefunden", result.errors)

    def test_validate_cloud_url_valid(self):
        url = "https://s3.eu-central-2.wasabisys.com/dsp-e-learning/Lerninhalte/SQL/Artikel/test.docx"
        result = self.service.validate_cloud_url(url)
        self.assertTrue(result["valid"])
        self.assertEqual(result["parsed_info"]["file_name"], "test.docx")

    def test_validate_cloud_url_invalid(self):
        url = "http://example.com/file.txt"
        result = self.service.validate_cloud_url(url)
        self.assertFalse(result["valid"])
        self.assertIn("errors", result)
