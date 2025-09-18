from pathlib import Path
from urllib.parse import urlparse
from botocore.exceptions import ClientError
from unittest.mock import ANY, Mock, patch
from django.test import TestCase

from elearning.modules.services.wasabi_service import WasabiService


class WasabiServiceTests(TestCase):
    def setUp(self):
        self.service = WasabiService.__new__(WasabiService)
        self.service.bucket = "dsp-e-learning"
        self.service.endpoint_url = "https://s3.eu-central-2.wasabisys.com"
        self.service.region = "eu-central-2"
        self.service.access_key = "fakekey"
        self.service.secret_key = "fakesecret"

    @patch("elearning.modules.services.wasabi_service.boto3.client")
    def test_normalize_key(self, mock_boto_client):
        s3_client_mock = self.service.get_s3_client()
        cases = [
            (
                "dsp-e-learning/Lerninhalte/SQL/Videos/Einführung.mp4",
                "Lerninhalte/SQL/Videos/Einführung.mp4",
            ),
            (
                "dsp-e-learning/dsp-e-learning/Lerninhalte/SQL/Videos/Einführung.mp4",
                "Lerninhalte/SQL/Videos/Einführung.mp4",
            ),
            (
                "/Lerninhalte/SQL/Videos/Einführung.mp4",
                "Lerninhalte/SQL/Videos/Einführung.mp4",
            ),
            (
                "Lerninhalte%20Modul%201/SQL/Videos/Einf%C3%BChrung.mp4",
                "Lerninhalte Modul 1/SQL/Videos/Einführung.mp4",
            ),
        ]

        for input_key, expected in cases:
            self.service.generate_presigned_url(input_key)
            s3_client_mock.generate_presigned_url.assert_called_with(
                ClientMethod="get_object",
                Params={"Bucket": self.service.bucket, "Key": expected},
                ExpiresIn=7200,
            )

    @patch("elearning.modules.services.wasabi_service.boto3.client")
    def test_expires_in(self, mock_boto_client):
        key = "Lerninhalte/SQL/Videos/Einführung.mp4"

        s3_client_mock = self.service.get_s3_client()
        self.service.generate_presigned_url(key, expires_seconds=1000)
        s3_client_mock.generate_presigned_url.assert_called_with(
            ClientMethod="get_object",
            Params={"Bucket": self.service.bucket, "Key": key},
            ExpiresIn=1000,
        )

    @patch("elearning.modules.services.wasabi_service.boto3.client")
    def test_get_s3_client(self, mock_boto_client):
        client = self.service.get_s3_client()
        mock_boto_client.assert_called_once_with(
            "s3",
            endpoint_url="https://s3.eu-central-2.wasabisys.com",
            region_name="eu-central-2",
            aws_access_key_id="fakekey",
            aws_secret_access_key="fakesecret",
            config=ANY,
        )

        self.assertEqual(client, mock_boto_client.return_value)

    @patch("elearning.modules.services.wasabi_service.boto3.client")
    def test_generate_presigned_url(self, mock_boto_client):
        mock_client_instance = Mock()
        mock_boto_client.return_value = mock_client_instance

        key = "Lerninhalte/SQL/Videos/Einführung.mp4"
        expected_url = (
            f"https://dsp-e-learning.s3.wasabisys.com/{key}?fake-signature=123"
        )
        mock_client_instance.generate_presigned_url.return_value = expected_url

        result = self.service.generate_presigned_url(key)

        self.assertEqual(result, expected_url)
        mock_client_instance.generate_presigned_url.assert_called_once_with(
            ClientMethod="get_object",
            Params={"Bucket": self.service.bucket, "Key": key},
            ExpiresIn=7200,
        )

    @patch("elearning.modules.services.wasabi_service.boto3.client")
    def test_exception_generate_presigned_url(self, mock_boto_client):
        key = "Lerninhalte/SQL/Videos/Einführung.mp4"

        mock_client_instance = Mock()
        mock_boto_client.return_value = mock_client_instance
        mock_client_instance.generate_presigned_url.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Fake error"}},
            "GeneratePresignedUrl",
        )

        result = self.service.generate_presigned_url(key)
        self.assertIsNone(result)

    def test_non_string_values_error(self):
        invalid_keys = [
            None,
            "",
            2,
            ["Lerninhalte/SQL/Videos/Einführung.mp4"],
            {"url": "Lerninhalte/SQL/Videos/Einführung.mp4"},
            b"Lerninhalte/SQL/Videos/Einf%C3%BChrung.mp4",
            Path("Lerninhalte/SQL/Videos/Einführung.mp4"),
            urlparse("Lerninhalte/SQL/Videos/Einführung.mp4"),
        ]

        for key in invalid_keys:
            with self.assertRaises(ValueError):
                result = self.service.generate_presigned_url(key)
                self.assertIsNone(result)
