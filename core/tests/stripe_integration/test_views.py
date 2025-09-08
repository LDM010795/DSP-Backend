from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from unittest.mock import patch
from types import SimpleNamespace

User = get_user_model()


class StripeViewsTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="u1", email="u1@example.com", password="pass"
        )
        self.client.force_authenticate(self.user)

    # ------------ 1) CreateSetupIntentView ----------

    @patch("core.stripe_integration.views.Customer.get_or_create")
    @patch("core.stripe_integration.views.stripe.SetupIntent.create")
    def test_create_setup_intent_ok(self, mock_si_create, mock_cust_get_or_create):
        mock_cust_get_or_create.return_value = (SimpleNamespace(id="cus_123"), True)
        mock_si_create.return_value = SimpleNamespace(client_secret="cs_test_123")

        resp = self.client.post("/api/payments/stripe/setup-intent", data={})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["client_secret"], "cs_test_123")

        mock_cust_get_or_create.assert_called_once()
        mock_si_create.assert_called_once_with(
            customer="cus_123",
            usage="off_session",
            payment_method_types=["card"],
        )

    # ------------ 2) CreateCheckoutSessionView ----------
