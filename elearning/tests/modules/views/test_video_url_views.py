from django.test import TestCase
from django.urls import reverse
from core.employees.serializers import User
from elearning.modules.models import Content
from rest_framework import status
from unittest.mock import patch

# Helper Functions


def authenticate(self):
    self.client.post(
        reverse("elearning:token_obtain_pair"),
        {"username": "testUser", "password": "testPassword"},
    )


def mock_wasabi_service(self):
    self.patcher = patch("elearning.modules.views.video_url_views.WasabiService")
    self.mock_wasabi_class = self.patcher.start()
    self.mock_instance = self.mock_wasabi_class.return_value
    self.mock_instance.generate_presigned_url.return_value = (
        "https://mocked-wasabi-url.com"
    )


class GetVideoPresignedUrlTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="testUser", password="testPassword"
        )

    def setUp(self):
        authenticate(self)
        mock_wasabi_service(self)

    def tearDown(self):
        self.patcher.stop()

    def send_get_presigned_url_request(self, content_id):
        return self.client.get(
            reverse(
                "elearning:modules:get-video-presigned-url",
                kwargs={"content_id": content_id},
            ),
            {"content_id": content_id},
        )

    def test_not_authenticated(self):
        self.client.cookies.clear()
        response = self.send_get_presigned_url_request(0)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_no_video_url(self):
        content = Content.objects.create(
            title="No URL",
            video_url="",
        )
        response = self.send_get_presigned_url_request(content.pk)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["error"], "Keine gültige Wasabi URL gefunden")

    def test_invalid_video_url(self):
        content = Content.objects.create(
            title="Invalid URL",
            video_url="https://example.com/video.mp4",
        )
        response = self.send_get_presigned_url_request(content.pk)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["error"], "Keine gültige Wasabi URL gefunden")

    def test_path_style_url(self):
        content = Content.objects.create(
            title="Path Style Video",
            video_url="https://s3.wasabisys.com/bucket-name/videos/video.mp4",
        )
        response = self.send_get_presigned_url_request(content.pk)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        json = response.json()
        self.assertEqual(json["presigned_url"], "https://mocked-wasabi-url.com")
        self.assertEqual(json["expires_in"], 7200)
        self.assertEqual(json["content_id"], 1)
        self.assertEqual(json["video_title"], "Path Style Video")

    def test_virtual_host_style_url(self):
        content = Content.objects.create(
            title="Virtual Host Style Video",
            video_url="https://s3.wasabisys.com/videos/video.mp4",
        )
        response = self.send_get_presigned_url_request(content.pk)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        json = response.json()
        self.assertEqual(json["presigned_url"], "https://mocked-wasabi-url.com")
        self.assertEqual(json["expires_in"], 7200)
        self.assertEqual(json["content_id"], 1)
        self.assertEqual(json["video_title"], "Virtual Host Style Video")

    def test_urlparse_exception_400(self):
        content = Content.objects.create(
            title="Video",
            video_url="https://s3.wasabisys.com/videos/video.mp4",
        )

        # Patch urlparse so it raises ValueError
        with patch(
            "elearning.modules.views.video_url_views.urlparse",
            side_effect=ValueError("boom!"),
        ):
            response = self.send_get_presigned_url_request(content.pk)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["error"], "Fehler beim Extrahieren des Video-Keys"
        )

    def test_generate_presigned_url_failed_500(self):
        self.mock_instance.generate_presigned_url.return_value = None

        content = Content.objects.create(
            title="Video",
            video_url="https://s3.wasabisys.com/videos/video.mp4",
        )

        response = self.send_get_presigned_url_request(content.pk)

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(
            response.json()["error"], "Konnte keine presigned URL generieren"
        )

    def test_content_id_invalid_404(self):
        response = self.send_get_presigned_url_request(9999)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["error"], "Content nicht gefunden")

    def test_internal_error(self):
        self.mock_instance.generate_presigned_url.side_effect = Exception(
            "Wasabi Service kaputt"
        )
        content = Content.objects.create(
            title="Video",
            video_url="https://s3.wasabisys.com/videos/video.mp4",
        )
        response = self.send_get_presigned_url_request(content.pk)

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("Server-Fehler: ", response.json()["error"])


class GetVideoPresignedUrlByKeyTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="testUser", password="testPassword"
        )

    def setUp(self):
        authenticate(self)
        mock_wasabi_service(self)

    def tearDown(self):
        self.patcher.stop()

    def send_get_presigned_url_by_key_request(self, key):
        return self.client.get(
            reverse("elearning:modules:get-video-presigned-url-by-key"),
            {"key": key},
        )

    def test_not_authenticated(self):
        self.client.cookies.clear()
        response = self.send_get_presigned_url_by_key_request(0)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_empty_key(self):
        response = self.send_get_presigned_url_by_key_request("")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["error"], "Key Parameter fehlt")

    def test_happy_path(self):
        response = self.send_get_presigned_url_by_key_request("videos/video.mp4")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        json = response.json()
        self.assertEqual(json["presigned_url"], "https://mocked-wasabi-url.com")
        self.assertEqual(json["expires_in"], 7200)
        self.assertEqual(json["key"], "videos/video.mp4")

    def test_generate_presigned_url_failed_500(self):
        self.mock_instance.generate_presigned_url.return_value = None
        response = self.send_get_presigned_url_by_key_request("videos/video.mp4")

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(
            response.json()["error"], "Konnte keine presigned URL generieren"
        )

    def test_internal_error(self):
        self.mock_instance.generate_presigned_url.side_effect = Exception(
            "Wasabi Service kaputt"
        )
        response = self.send_get_presigned_url_by_key_request("videos/video.mp4")

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("Server-Fehler: ", response.json()["error"])

    def test_get_storage_presigned_url_by_key(self):
        response = self.client.get(
            reverse("elearning:modules:get-storage-presigned-url-by-key"),
            {"key": "images/image.png"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        json = response.json()
        self.assertEqual(json["presigned_url"], "https://mocked-wasabi-url.com")
        self.assertEqual(json["expires_in"], 7200)
        self.assertEqual(json["key"], "images/image.png")
