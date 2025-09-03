"""
Stripe Integration Views (core.stripe_integration)
==================================================

This module exposes REST API endpoints for handling payments with Stripe.
It is now located in the core/stripe_integration package for easier extension to other products
beyond courses.

Endpoints
---------

1. CreateSetupIntentView
   - URL: /api/payments/stripe/setup-intent/
   - Method: POST
   - Auth: Required
   - Purpose:
       Creates a Stripe SetupIntent so the frontend can securely collect
       and save a card payment method for future use.

2. CreateCheckoutSessionView
   - URL: /api/payments/stripe/checkout-session/
   - Method: POST
   - Body: {"price_id": "...", "course_id": 42}
   - Purpose:
       Creates a Stripe Checkout Session for one-off course purchases.
       Metadata ensures that we can associate payments with courses/users.

3. GetStripeConfigView
   - URL: /api/payments/stripe/config/
   - Method: GET
   - Auth: None
   - Purpose:
       Returns the correct publishable key so the frontend can
       initialize Stripe.js safely.

4. ListPaymentMethodsView
   - URL: /api/payments/stripe/payment-methods/
   - Method: GET
   - Auth: Required
   - Purpose:
       Lists all saved card payment methods of the authenticated user.

5. SetDefaultPaymentMethodView
   - URL: /api/payments/stripe/payment-methods/default/
   - Method: POST
   - Body: {"payment_method_id": "pm_123"}
   - Purpose:
       Attaches a given card (if needed) and marks it as the default.

Features
--------
- Ensures each user has a Stripe Customer object (via dj-stripe).
- Safe handling of payment methods (card details never touch our backend).
- Redirect integration with frontend success/cancel flows.
- Designed for extensibility: subscriptions, invoices, refunds can be added.

Security
--------
- Only authenticated users can save or charge cards.
- Card data is handled exclusively by Stripe; backend only stores metadata.

Dependencies
------------
- Django REST Framework (API endpoints)
- dj-stripe (customer syncing, event persistence)
- stripe (official Python SDK)

Author: DSP Development Team
Date: 2025-08-21
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
        price_id = request.data.get("price_id")
        course_id = request.data.get("course_id")

        if not price_id or not course_id:
            return Response({"detail": "price_id and course_id are required."}, status=400)

        customer, _ = Customer.get_or_create(subscriber=request.user)

        # (Optional) fetch default PM for diagnostics/logging; not pushed into params for mode="payment"
        try:
            cust = stripe.Customer.retrieve(customer.id)
            inv = cust.get("invoice_settings") or {}
            default_pm_id = inv.get("default_payment_method") or None
        except Exception:
            default_pm_id = None

        params = dict(
            mode="payment",
            customer=customer.id,
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=(
                f"{settings.FRONTEND_URL}"
                f"/payments/checkout/success?session_id={{CHECKOUT_SESSION_ID}}&course={course_id}"
            ),
            cancel_url=f"{settings.FRONTEND_URL}/payments/cancel?course={course_id}",
            allow_promotion_codes=True,
            metadata={"course_id": str(course_id), "user_id": str(request.user.id)},
        )

        try:
            session = stripe.checkout.Session.create(**params)
            return Response({"checkout_url": session.url, "id": session.id}, status=200)
        except stripe.error.StripeError as e:
            return Response(
                {
                    "detail": "Stripe Checkout konnte nicht erstellt werden.",
                    "stripe_error": getattr(e, "user_message", str(e)),
                },
                status=400,
            )





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
        customer, _ = Customer.get_or_create(subscriber=request.user)

        # Read directly from Stripe (fast, no dj-stripe lag)
        stripe_pms = stripe.PaymentMethod.list(customer=customer.id, type="card")
        cust = stripe.Customer.retrieve(customer.id)

        inv = getattr(cust, "invoice_settings", None) or {}
        default_pm_id = inv.get("default_payment_method")

        data = []
        for pm in stripe_pms.get("data", []):
            card = pm.get("card") or {}
            data.append({
                "id": pm.get("id"),
                "brand": card.get("brand"),
                "last4": card.get("last4"),
                "exp_month": card.get("exp_month"),
                "exp_year": card.get("exp_year"),
                "is_default": (pm.get("id") == default_pm_id),
            })

        resp = Response({"payment_methods": data}, status=200)
        resp["Cache-Control"] = "no-store"  # avoid any caching confusion
        return resp



class SetDefaultPaymentMethodView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        pm_id = request.data.get("payment_method_id")
        if not pm_id:
            return Response({"detail": "payment_method_id required."}, status=400)

        customer, _ = Customer.get_or_create(subscriber=request.user)

        # Attach safely (idempotent)
        try:
            stripe.PaymentMethod.attach(pm_id, customer=customer.id)
        except stripe.error.InvalidRequestError as e:
            # if it's already attached to this customer, ignore
            if "already exists" not in str(e).lower():
                raise

        # Set as default for invoices (prevents “enter card again”)
        stripe.Customer.modify(
            customer.id,
            invoice_settings={"default_payment_method": pm_id},
        )

        return Response({"detail": "Default payment method set."}, status=200)




