"""

Payments Views for Stripe Integration
=====================================

This module provides API endpoints for handling payments through Stripe.
It contains endpoints for both saving a customer’s payment method (via SetupIntent)
and creating a Checkout Session for purchasing courses.

Endpoints:
----------

1. CreateSetupIntentView
   - URL: /api/payments/stripe/setup-intent/
   - Method: POST
   - Auth: Required (user must be logged in)
   - Purpose:
       Creates a Stripe SetupIntent so that the frontend can securely collect
       and save a payment method (e.g., a credit card) for future use.
   - Typical Flow:
       1. Frontend calls this endpoint to get a client secret.
       2. Frontend uses Stripe.js to collect card details.
       3. Payment method is attached to the Stripe customer for later charges.

2. CreateCheckoutSessionView
   - URL: /api/payments/stripe/checkout-session/
   - Method: POST
   - Auth: Required (user must be logged in)
   - Expected Body:
       {
           "price_id": "price_123",
           "course_id": 42
       }
   - Purpose:
       Creates a Stripe Checkout Session that allows the user to pay for
       a specific course. After successful payment, the user will be redirected
       back to the frontend with course and session details.
   - Typical Flow:
       1. Frontend sends `price_id` (from Stripe) and `course_id` (internal ID).
       2. Backend creates a Stripe Checkout Session with this info.
       3. Stripe redirects the user to success or cancel URLs depending on outcome.
       4. Payment metadata ensures we can associate the payment with the course/user.

3. GetStripeConfigView
   - URL: /api/payments/stripe/config/
   - Method: GET
   - Auth: Public (AllowAny)
   - Purpose:
       Returns the correct publishable key (test/live) so the frontend
       can safely initialize Stripe.js without exposing secret keys.

4. ListPaymentMethodsView
   - URL: /api/payments/stripe/payment-methods/
   - Method: GET
   - Auth: Required
   - Purpose:
       Returns a list of the user’s saved card payment methods,
       including brand, last4 digits, expiry, and whether each is
       the default method.

5. SetDefaultPaymentMethodView
   - URL: /api/payments/stripe/payment-methods/default/
   - Method: POST
   - Auth: Required
   - Expected Body:
       {
           "payment_method_id": "pm_abc123"
       }
   - Purpose:
       Attaches a given card (if not already attached) and sets it as
       the default payment method for the user’s Stripe Customer record.

Features:
---------
- Ensures every user has a Stripe `Customer` object.
- Secure handling of payment methods and sessions.
- Redirect integration with frontend URLs for success and cancel flows.
- Designed for extensibility (additional endpoints like invoices, subscriptions
  can be added later).

Security:
---------
- Requires authentication: Only logged-in users can initiate a SetupIntent.
- Sensitive data (e.g., card details) is **never** handled by our backend.
  Instead, it is collected directly by Stripe via the client_secret returned here.

Dependencies:
-------------
- Django REST Framework for API endpoints.
- dj-stripe for managing Customer and syncing Stripe objects into the database.
- stripe (official Stripe Python library) for creating SetupIntents.

Author: DSP Development Team
Date: [2025-08-21]
"""


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
import stripe
from django.conf import settings
from djstripe.models import Customer, PaymentMethod

stripe.api_key = settings.STRIPE_SECRET_KEY

class CreateSetupIntentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Ensure a Stripe Customer exists for this user
        customer, _ = Customer.get_or_create(subscriber=request.user)
        # Create SetupIntent so frontend can collect and attach a payment method
        si = stripe.SetupIntent.create(
            customer=customer.id,
            usage="off_session",  # ensure future automatic charges work
            payment_method_types=["card"]
        )
        return Response({"client_secret": si.client_secret}, status=status.HTTP_200_OK)


class CreateCheckoutSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Expect { "price_id": "price_123", "course_id": 42 }
        price_id = request.data.get("price_id")
        course_id = request.data.get("course_id")

        if not price_id or not course_id:
            return Response({"detail": "price_id and course_id are required."}, status=400)

        customer, _ = Customer.get_or_create(subscriber=request.user)

        session = stripe.checkout.Session.create(
            mode="payment",
            customer=customer.id,
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=f"{settings.FRONTEND_URL}/payments/checkout/success?session_id={{CHECKOUT_SESSION_ID}}&course={course_id}",
            cancel_url = f"{settings.FRONTEND_URL}/payments/cancel?course={course_id}",
            allow_promotion_codes=True,
            metadata={"course_id": str(course_id), "user_id": str(request.user.id)},
        )
        return Response({"checkout_url": session.url, "id": session.id}, status=200)


class GetStripeConfigView(APIView):
    """
    endpoint so the frontend can initialize Stripe.js
    """
    permission_classes = [AllowAny]

    def get(self, request):
        publishable_key = (
            settings.STRIPE_LIVE_PUBLISHABLE_KEY
            if settings.STRIPE_LIVE_MODE
            else settings.STRIPE_TEST_PUBLISHABLE_KEY
        )
        return Response({"publishableKey": publishable_key}, status=200)


class ListPaymentMethodsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        customer, _= Customer.get_or_create(subscriber=request.user)
        pms = PaymentMethod.objects.filter(customer=customer, type="card")
        data = [
            {
                "id": pm.id,
                "brand": pm.card.get("brand"),
                "last4": pm.card.get("last4"),
                "exp_month": pm.card.get("exp_month"),
                "exp_year": pm.card.get("exp_year"),
                "is_default": (
                    customer.default_payment_method
                    and customer.default_payment_method.id == pm.id
                ),
            }
            for pm in pms
        ]
        return Response({"payment_methods": data}, status=200)


class SetDefaultPaymentMethodView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        pm_id = request.data.get("payment_method_id")
        if not pm_id:
            return Response({"detail": "payment_method_id required."}, status=400)

        customer, _ = Customer.get_or_create(subscriber=request.user)

        # Attach & set default on Stripe (idempotent if already attached)
        stripe.PaymentMethod.attach(pm_id, customer=customer.id)
        stripe.Customer.modify(
            customer.id,
            invoice_settings={"default_payment_method": pm_id},
        )

        # (Optional) Let dj-stripe catch up via webhooks; or refresh later.
        return Response({"detail": "Default payment method set."}, status=200)



