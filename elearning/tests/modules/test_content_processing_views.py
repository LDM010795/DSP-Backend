"""
Content Processing Views – Test Suite

Covers:
- process_module_content (auth-only; validates input; delegates to orchestration; 200/400)
- validate_video_url (auth-only; prefix & extension checks; existence via CloudStorageService; 200/400/404)
- get_available_modules (auth-only; 200)
- get_module_statistics (auth-only; requires module_name; 200/400/404)
- test_all_services (admin-only; aggregates booleans; 200)
- process_multiple_modules (auth-only; requires array; aggregates results; 200/400)
- cleanup_module_content (admin-only; requires name; 200/400)

Author: DSP Development Team
Date: 2025-09-15
"""

from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

User = get_user_model()

# urls
BASE = "/api/elearning/modules/content/"

URL_PROCESS_ONE = BASE + "process-module/"
URL_VALIDATE_VIDEO = BASE + "validate-video-url/"
URL_AVAILABLE = BASE + "available-modules/"
URL_STATS = BASE + "module-statistics/"
URL_TEST_SERVICES = BASE + "test-services/"
URL_PROCESS_MULTI = BASE + "process-multiple-modules/"
URL_CLEANUP = BASE + "cleanup-module/"


# patch where the symbols are *used* (the views module)
PATCH_BASE = "elearning.modules.views.content_processing_views"


class ContentProcessingViewsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="user", email="user@example.com", password="pass"
        )
        cls.admin = User.objects.create_user(
            username="admin", email="admin@example.com", password="pass"
        )
        cls.admin.is_staff = True
        cls.admin.is_superuser = True
        cls.admin.save()

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    # --- small helpers to keep tests tidy ---
    def api_get(self, url, **kwargs):
        return self.client.get(url, **kwargs)

    def api_post(self, url, data=None, **kwargs):
        if "format" not in kwargs:
            kwargs["format"] = "json"
        return self.client.post(url, data=(data or {}), **kwargs)

    # ----------- Auth basics -----------

    def test_requires_auth_for_all_user_endpoints(self):
        anon = APIClient()
        self.assertEqual(
            anon.post(URL_PROCESS_ONE, data={}, format="json").status_code, 401
        )
        self.assertEqual(
            anon.post(URL_VALIDATE_VIDEO, data={}, format="json").status_code, 401
        )
        self.assertEqual(anon.get(URL_AVAILABLE).status_code, 401)
        self.assertEqual(anon.get(f"{URL_STATS}?module_name=SQL").status_code, 401)
        self.assertEqual(
            anon.post(URL_PROCESS_MULTI, data={}, format="json").status_code, 401
        )

    def test_admin_only_endpoints_permissions(self):
        # anon -> 401
        self.client.force_authenticate(user=None)
        self.assertEqual(self.api_post(URL_TEST_SERVICES).status_code, 401)
        self.assertEqual(self.api_post(URL_CLEANUP).status_code, 401)

        # authed non-admin -> 403
        self.client.force_authenticate(self.user)
        self.assertEqual(self.api_post(URL_TEST_SERVICES).status_code, 403)
        self.assertEqual(
            self.api_post(URL_CLEANUP, data={"module_name": "SQL"}).status_code, 403
        )

    # ----------- process_module_content -----------

    def test_process_module_content_400_when_missing_module_name(self):
        resp = self.api_post(URL_PROCESS_ONE)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("module_name", resp.json()["error"].lower())

    @patch(f"{PATCH_BASE}.ContentOrchestrationService")
    def test_process_module_content_success(self, MockOrch):
        # Build a fake result obj with attributes used by view
        fake_result = SimpleNamespace(
            success=True,
            module_name="SQL",
            images_processed=5,
            articles_processed=2,
            images_saved=5,
            articles_saved=2,
            errors=[],
            warnings=[],
        )
        MockOrch.return_value.process_module_content.return_value = fake_result

        resp = self.api_post(URL_PROCESS_ONE, data={"module_name": "SQL"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["module_name"], "SQL")
        self.assertEqual(data["images_processed"], 5)

    # ------------- validate_video_url -----------

    def test_validate_video_url_400_when_missing(self):
        resp = self.api_post(URL_VALIDATE_VIDEO)
        self.assertEqual(resp.status_code, 400)

    def test_validate_video_url_400_when_wrong_prefix(self):
        resp = self.api_post(
            URL_VALIDATE_VIDEO, data={"video_url": "https://example.com/foo.mp4"}
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("ungültige", resp.json()["error"].lower())

    def test_validate_video_url_400_when_not_video_extension(self):
        bad = "https://s3.eu-central-2.wasabisys.com/dsp-e-learning/Lerninhalte/SQL/Videos/readme.txt"
        resp = self.api_post(URL_VALIDATE_VIDEO, data={"video_url": bad})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("keine gültige video-datei", resp.json()["error"].lower())

    @patch(f"{PATCH_BASE}.CloudStorageService")
    def test_validate_video_url_404_when_head_object_missing(self, MockCloud):
        good = "https://s3.eu-central-2.wasabisys.com/dsp-e-learning/Lerninhalte/SQL/Videos/1.1%20Einführung.mp4"

        # CloudStorageService().client.head_object should raise to simulate "not found"
        instance = MockCloud.return_value
        instance.client.head_object.side_effect = Exception("NotFound")

        resp = self.api_post(URL_VALIDATE_VIDEO, data={"video_url": good})
        self.assertEqual(resp.status_code, 404)

    @patch(f"{PATCH_BASE}.CloudStorageService")
    def test_validate_video_url_success(self, MockCloud):
        good = "https://s3.eu-central-2.wasabisys.com/dsp-e-learning/Lerninhalte/SQL/Videos/1.1%20Einführung.mp4"

        # Simulate existing object
        instance = MockCloud.return_value
        instance.client.head_object.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200}
        }

        resp = self.api_post(URL_VALIDATE_VIDEO, data={"video_url": good})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["is_valid"])
        self.assertEqual(data["filename"], "1.1%20Einführung.mp4")
        self.assertEqual(
            data["title"], "1.1%20Einführung"
        )  # view uses os.path.splitext on the raw last segment

    # ---------- get_available_modules ----------

    @patch(f"{PATCH_BASE}.ContentOrchestrationService")
    def test_available_modules_success(self, MockOrch):
        MockOrch.return_value.get_available_modules.return_value = [
            "SQL",
            "Python Grundlagen",
        ]

        resp = self.api_get(URL_AVAILABLE)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["success"])
        self.assertEqual(resp.json()["modules"], ["SQL", "Python Grundlagen"])

    # ---------- get_module_statistics ----------

    def test_module_statistics_400_when_missing_param(self):
        resp = self.api_get(URL_STATS)
        self.assertEqual(resp.status_code, 400)

    @patch(f"{PATCH_BASE}.ContentOrchestrationService")
    def test_module_statistics_404_when_service_returns_error(self, MockOrch):
        MockOrch.return_value.get_module_statistics.return_value = {
            "error": "not found"
        }
        resp = self.api_get(f"{URL_STATS}?module_name=Nope")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["success"], False)
        self.assertEqual(resp.json()["error"], "not found")

    @patch(f"{PATCH_BASE}.ContentOrchestrationService")
    def test_module_statistics_success(self, MockOrch):
        MockOrch.return_value.get_module_statistics.return_value = {
            "module_name": "SQL",
            "module_id": 1,
            "is_public": True,
            "category": "Standard",
            "images_count": 5,
            "articles_count": 2,
            "content_count": 0,
            "tasks_count": 0,
        }
        resp = self.api_get(f"{URL_STATS}?module_name=SQL")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["module_name"], "SQL")
        self.assertEqual(body["images_count"], 5)

    # ---------- test_all_services (admin only) ----------

    @patch(f"{PATCH_BASE}.ContentOrchestrationService")
    def test_test_all_services_admin_success(self, MockOrch):
        self.client.force_authenticate(self.admin)
        MockOrch.return_value.test_all_services.return_value = {
            "cloud_storage": True,
            "word_processing": True,
            "database": True,
        }
        resp = self.api_post(URL_TEST_SERVICES)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertTrue(data["cloud_storage"])
        self.assertTrue(data["word_processing"])
        self.assertTrue(data["database"])

    @patch(f"{PATCH_BASE}.ContentOrchestrationService")
    def test_test_all_services_admin_partial_failure(self, MockOrch):
        self.client.force_authenticate(self.admin)
        MockOrch.return_value.test_all_services.return_value = {
            "cloud_storage": True,
            "word_processing": False,
            "database": True,
        }
        resp = self.api_post(URL_TEST_SERVICES)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["success"])
        self.assertIn("word_processing", data)
        self.assertIs(data["word_processing"], False)

    # ---------- process_multiple_modules ----------

    def test_process_multiple_modules_400_when_missing_array(self):
        resp = self.api_post(URL_PROCESS_MULTI)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("module_names", resp.json()["error"].lower())

    @patch(f"{PATCH_BASE}.ContentOrchestrationService")
    def test_process_multiple_modules_success(self, MockOrch):
        results = [
            SimpleNamespace(
                success=True,
                module_name="SQL",
                images_processed=5,
                articles_processed=2,
                images_saved=5,
                articles_saved=2,
                errors=[],
                warnings=[],
            ),
            SimpleNamespace(
                success=True,
                module_name="Python Grundlagen",
                images_processed=3,
                articles_processed=1,
                images_saved=3,
                articles_saved=1,
                errors=[],
                warnings=[],
            ),
        ]
        MockOrch.return_value.process_multiple_modules.return_value = results

        resp = self.api_post(
            URL_PROCESS_MULTI, data={"module_names": ["SQL", "Python Grundlagen"]}
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["success"])
        self.assertEqual(len(body["results"]), 2)
        self.assertEqual(body["results"][0]["module_name"], "SQL")
        self.assertTrue(body["results"][0]["success"])
        self.assertTrue(body["results"][1]["success"])

    @patch(f"{PATCH_BASE}.ContentOrchestrationService")
    def test_process_multiple_modules_partial_failure(self, MockOrch):
        results = [
            SimpleNamespace(
                success=True,
                module_name="SQL",
                images_processed=5,
                articles_processed=2,
                images_saved=5,
                articles_saved=2,
                errors=[],
                warnings=[],
            ),
            SimpleNamespace(
                success=False,
                module_name="DS",
                images_processed=0,
                articles_processed=0,
                images_saved=0,
                articles_saved=0,
                errors=["x"],
                warnings=[],
            ),
        ]
        MockOrch.return_value.process_multiple_modules.return_value = results

        resp = self.api_post(URL_PROCESS_MULTI, data={"module_names": ["SQL", "DS"]})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["success"])
        self.assertTrue(data["results"][0]["success"])
        self.assertFalse(data["results"][1]["success"])
        self.assertGreaterEqual(len(data["results"][1]["errors"]), 1)

    # ---------- cleanup_module_content (admin only) ----------

    def test_cleanup_module_content_400_when_missing_name(self):
        self.client.force_authenticate(self.admin)
        resp = self.api_post(URL_CLEANUP)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("module_name", resp.json()["error"].lower())

    @patch(f"{PATCH_BASE}.ContentOrchestrationService")
    def test_cleanup_module_content_success(self, MockOrch):
        self.client.force_authenticate(self.admin)
        MockOrch.return_value.cleanup_old_content.return_value = {
            "success": True,
            "module_name": "SQL",
            "cleaned_images": 2,
            "current_images_count": 5,
            "current_articles_count": 2,
        }
        resp = self.api_post(URL_CLEANUP, data={"module_name": "SQL"})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["cleaned_images"], 2)

    @patch(f"{PATCH_BASE}.ContentOrchestrationService")
    def test_cleanup_module_content_failure_400(self, MockOrch):
        self.client.force_authenticate(self.admin)
        MockOrch.return_value.cleanup_old_content.return_value = {
            "success": False,
            "module_name": "SQL",
            "error": "Something went wrong",
        }
        resp = self.api_post(URL_CLEANUP, data={"module_name": "SQL"})
        self.assertEqual(resp.status_code, 400)
        body = resp.json()
        self.assertFalse(body["success"])
        self.assertEqual(body["error"], "Something went wrong")
