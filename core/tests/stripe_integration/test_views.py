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

        resp = self.client.post("/api/payments/stripe/setup-intent/", data={})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["client_secret"], "cs_test_123")

        mock_cust_get_or_create.assert_called_once()
        mock_si_create.assert_called_once_with(
            customer="cus_123",
            usage="off_session",
            payment_method_types=["card"],
        )

    # ------------ 2) CreateCheckoutSessionView ----------

    @patch("core.stripe_integration.views.Customer.get_or_create")
    @patch("core.stripe_integration.views.stripe.Customer.retrieve")
    @patch("core.stripe_integration.views.stripe.checkout.Session.create")
    @override_settings(FRONTEND_URL="https://fe.example.com")
    def test_create_checkout_session_ok(
        self, mock_session_create, mock_customer_retrieve, mock_cust_get_or_create
    ):
        mock_cust_get_or_create.return_value = (SimpleNamespace(id="cus_123"), True)
        mock_customer_retrieve.return_value = {"invoice_settings": {"default_payment_method": "pm_def"}}
        mock_session_create.return_value = SimpleNamespace(url="https://chk", id="cs_123")

        payload = {"price_id": "price_abc", "course_id": 42}
        resp = self.client.post("/api/payments/stripe/checkout-session/", data=payload, format="json")

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["checkout_url"], "https://chk")
        self.assertEqual(body["id"], "cs_123")

        # Validate we passed the right params to Stripe
        called_kwargs = mock_session_create.call_args.kwargs
        self.assertEqual(called_kwargs["mode"], "payment")
        self.assertEqual(called_kwargs["customer"], "cus_123")
        self.assertEqual(called_kwargs["line_items"], [{"price": "price_abc", "quantity": 1}])
        self.assertIn("success_url", called_kwargs)
        self.assertTrue(
            called_kwargs["success_url"].startswith("https://fe.example.com/payments/checkout/success")
        )
        self.assertEqual(
            called_kwargs["metadata"],
            {"course_id": "42", "user_id": str(self.user.id)},
        )

    @patch("core.stripe_integration.views.Customer.get_or_create")
    @patch("core.stripe_integration.views.stripe.checkout.Session.create")
    def test_create_checkout_session_stripe_error(self, mock_session_create, mock_cust_get_or_create):
        mock_cust_get_or_create.return_value = (SimpleNamespace(id="cus_123"), True)
        # Raise a Stripe API error
        mock_session_create.side_effect = stripe.error.StripeError(message="boom")

        payload = {"price_id": "price_abc", "course_id": 42}
        resp = self.client.post("/api/payments/stripe/checkout-session/", data=payload, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Stripe Checkout konnte nicht erstellt werden", resp.json()["detail"])

    # ------------ 3) GetStripeConfigView ----------

    @override_settings(STRIPE_LIVE_MODE=False, STRIPE_TEST_PUBLISHABLE_KEY="pk_test_123")
    def test_get_config_returns_test_key_when_not_live(self):
        anon = APIClient() # public endpoint, no auth
        resp = anon.get("/api/payments/stripe/config/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["publishableKey"], "pk_test_123")

    @override_settings(STRIPE_LIVE_MODE=True, STRIPE_LIVE_PUBLISHABLE_KEY="pk_live_999")
    def test_get_config_returns_live_key_when_live(self):
        anon = APIClient()
        resp = anon.get("/api/payments/stripe/config/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["publishableKey"], "pk_live_999")

    # ------------ 4) ListPaymentMethodView ----------

    @patch("core.stripe_integration.views.Customer.get_or_create")
    @patch("core.stripe_integration.views.stripe.PaymentMethod.list")
    @patch("core.stripe_integration.views.stripe.Customer.retrieve")
    def test_list_payment_methods_marks_default(
            self, mock_customer_retrieve, mock_pm_list, mock_cust_get_or_create
    ):
        mock_cust_get_or_create.return_value = (SimpleNamespace(id="cus_123"), True)
        mock_pm_list.return_value = {
            "data": [
                {"id": "pm_1", "card": {"brand": "visa", "last4": "1111", "exp_month": 1, "exp_year": 2030}},
                {"id": "pm_2", "card": {"brand": "mc", "last4": "2222", "exp_month": 2, "exp_year": 2031}},
            ]
        }
        mock_customer_retrieve.return_value = SimpleNamespace(
            invoice_settings={"default_payment_method": "pm_2"}
        )

        resp = self.client.get("/api/payments/stripe/payment-methods/")
        self.assertEqual(resp.status_code, 200)
        pm = resp.json()["payment_methods"]
        self.assertEqual(len(pm), 2)
        self.assertFalse(pm[0]["is_default"])
        self.assertTrue(pm[1]["is_default"])
        self.assertEqual(resp["Cache-Control"], "no-store")

    # ------------ 5) SetDefaultPaymentMethodView ----------

    @patch("core.stripe_integration.views.Customer.get_or_create")
    def test_set_default_payment_method_missing_param(self, mock_cust_get_or_create):
        resp = self.client.post("/api/payments/stripe/payment-methods/default/", data={}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("payment_method_id", resp.json()["detail"])

    @patch("core.stripe_integration.views.Customer.get_or_create")
    @patch("core.stripe_integration.views.stripe.Customer.modify")
    @patch("core.stripe_integration.views.stripe.PaymentMethod.attach")
    def test_set_default_payment_method_ok(
            self, mock_attach, mock_modify, mock_cust_get_or_create
    ):
        mock_cust_get_or_create.return_value = (SimpleNamespace(id="cus_123"), True)
        payload = {"payment_method_id": "pm_123"}
        resp = self.client.post("/api/payments/stripe/payment-methods/default/", data=payload, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Default payment method set", resp.json()["detail"])
        mock_attach.assert_called_once_with("pm_123", customer="cus_123")
        mock_modify.assert_called_once_with("cus_123", invoice_settings={"default_payment_method": "pm_123"})

    @patch("core.stripe_integration.views.Customer.get_or_create")
    @patch("core.stripe_integration.views.stripe.Customer.modify")
    @patch("core.stripe_integration.views.stripe.PaymentMethod.attach")
    def test_set_default_payment_method_already_attached_is_ok(
            self, mock_attach, mock_modify, mock_cust_get_or_create
    ):
        mock_cust_get_or_create.return_value = (SimpleNamespace(id="cus_123"), True)

        # Simulate Stripe saying the PM is already attached to this customer.
        mock_attach.side_effect = stripe.error.InvalidRequestError(
            message="Payment method already exists",
            param="payment_method",
        )

        payload = {"payment_method_id": "pm_123"}
        resp = self.client.post("/api/payments/stripe/payment-methods/default/", data=payload, format="json")
        self.assertEqual(resp.status_code, 200)
        mock_modify.assert_called_once_with("cus_123", invoice_settings={"default_payment_method": "pm_123"})


