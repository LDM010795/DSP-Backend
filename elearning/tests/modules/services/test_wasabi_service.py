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

    def test_empty_key(self):
        with self.assertRaises(ValueError):
            self.service.generate_presigned_url("")

        with self.assertRaises(ValueError):
            self.service.generate_presigned_url(None)

    def test_normalize_key(self):
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
            ("", ""),
        ]
        for input_key, expected in cases:
            self.assertEqual(self.service._normalize_key(input_key), expected)

    @patch("boto3.client")
    def test_get_s3_client(self, mock_boto_client):
        # Methode aufrufen
        client = self.service.get_s3_client()

        # Prüfen, ob boto3.client korrekt aufgerufen wurde
        mock_boto_client.assert_called_once_with(
            "s3",
            endpoint_url="https://s3.eu-central-2.wasabisys.com",
            region_name="eu-central-2",
            aws_access_key_id="fakekey",
            aws_secret_access_key="fakesecret",
            config=ANY,
        )

        # Prüfen, dass die Methode das Mock zurückgibt
        self.assertEqual(client, mock_boto_client.return_value)

    @patch("boto3.client")
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

    @patch("boto3.client")
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
