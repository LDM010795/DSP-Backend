"""
Stripe Integration Package - DSP
=============================================================

This package centralizes all Stripe-related logic for the DSP backend.
It replaces earlier ad-hoc payment code (e.g. elearning/payments) and
serves as the **core integration point** for billing.

Current Scope
--------------------
- Uses `dj-stripe` to manage Stripe Customers, PaymentMethods, and Events.
- Provides API endpoints (see views.py) for:
  * Creating SetupIntents (save card)
  * Creating Checkout Sessions (one-off course purchases)
  * Listing and updating payment methods
  * Returning publishable config keys
- Provides webhook handlers (see signals.py) to react to Stripe events:
  * Enrollment after successful Checkout or PaymentIntent
  * Setting default payment methods after SetupIntent
  * (Optional) Recording payments and handling refunds

Design Rationale
----------------
- Core placement: Located in `core/stripe_integration` so that billing
  is not tied only to e-learning. This allows reuse for other product
  domains (subscriptions, employee services, etc.).
- dj-stripe bridge: We let dj-stripe persist Stripe objects locally,
  while our handlers act on project-specific models like CourseEnrollment
  or Payment (if present).
- Extensible: New endpoints (subscriptions, invoices, reports) can be
  added here without impacting the rest of the system.

Future Extensions
-----------------
- Subscription management (recurring payments via `Subscription` + `Invoice`).
- Unified Payment model across all apps (not just elearning).
- Analytics/reporting on revenues, refunds, churn.
- Multi-product billing (beyond courses).

Structure
---------
- __init__.py (this file, documentation + default app config)
- apps.py         → App configuration (`StripeIntegrationConfig`)
- views.py        → API endpoints (SetupIntent, Checkout, etc.)
- signals.py      → Webhook handlers (Event post-processing)
- urls.py         → Routes for Stripe endpoints

Author: DSP Development Team
Date: 2025-09-03
"""

default_app_config = "core.stripe_integration.apps.StripeIntegrationConfig"
