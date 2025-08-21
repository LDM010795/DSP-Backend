"""
Stripe Webhook Signal Handlers for E‑Learning Payments
=====================================================

Overview
--------
This module contains **post‑processing handlers** for Stripe webhooks using
`dj-stripe`. It listens to the `webhook_event_processed` signal, which fires
**after** dj‑stripe has verified the signature, de‑duplicated the event, and
stored it in the database. This means the handlers here only receive **trusted
and idempotent** events.

What this module does
---------------------
1) **One‑off Purchases (Checkout)**
   - On `checkout.session.completed`, the user is enrolled into the purchased
     course (using metadata `{ "user_id": ..., "course_id": ... }` set by the
     backend when creating the Checkout Session).
   - An optional local `Payment` record is created for reporting/analytics.

2) **Direct Charges / Saved Cards**
   - On `payment_intent.succeeded`, if you later create server‑side
     PaymentIntents to charge saved cards, this handler can also enroll users
     (if metadata includes course/user) and log payment details.

3) **Subscriptions (Future‑proof)**
   - On `invoice.payment_succeeded`, if you add subscriptions later, this can
     grant access accordingly and record the payment.

4) **Refunds**
   - On `charge.refunded` or `charge.refund.updated`, local payment records can
     be marked as refunded and (optionally) access revoked.

Event Handling Matrix
---------------------
- checkout.session.completed  → enroll user, record payment
- payment_intent.succeeded    → enroll (if metadata present), record payment
- invoice.payment_succeeded   → grant access for subscriptions, record payment
- charge.refunded/*updated*   → mark local payments as refunded

Data Flow (Happy Path)
----------------------
Stripe → Webhook → dj‑stripe verifies & saves Event → this module receives the
`webhook_event_processed` signal → we:
  1. Parse the event `event.type` and `event.data["object"]`.
  2. Read `metadata.user_id` & `metadata.course_id` if applicable.
  3. Load `User` and `Course` from the DB.
  4. **Idempotently** create an `Enrollment` (get_or_create).
  5. Optionally create a local `Payment` row for analytics.

Assumptions & Model Integration
-------------------------------
- **User**: standard Django user (`get_user_model()`).
- **Course**: a model named `Course` living in `elearning` or `elearning.modules`.
- **Enrollment**: a model named `CourseEnrollment` or `Enrollment` with fields:
  `user`, `course` (plus optional `source`, `reference`).
- **Payment** (optional): a model in `elearning` / `elearning.payments` /
  `payments` with fields like:
  `user`, `course`, `stripe_payment_intent_id`, `amount`, `currency`, `status`,
  `checkout_session_id`.

If your actual model names/fields differ, adjust the `_get_model(...)` lookups
and the field writes in `_enroll_user_in_course(...)` and `_record_payment(...)`.

Idempotency & Safety
--------------------
- Handlers never raise errors out of the signal; failures are logged and
  processing continues to avoid retry storms.
- Enrollments use `get_or_create` to avoid duplicate grants if Stripe retries.
- All writes are wrapped in short `transaction.atomic()` blocks.

Security Considerations
-----------------------
- Events are only handled **after** dj‑stripe signature verification.
- Never trust client‑side metadata for access control unless validated on the
  server (here we only trust metadata coming from our own Checkout creation).

Local Payment Recording (Optional)
---------------------------------
- If a `Payment` model is present, payments are logged. If not, the module logs
  that it skipped local recording. This allows to wire up reporting later
  without blocking current functionality.

Logging
-------
- Success paths and decisions (enrollment created/already exists) are logged at
  `INFO` level.
- Missing model or object lookups are logged with details to aid debugging.
- Exceptions are logged with stack traces; processing does not abort.

"""

from __future__ import annotations

import logging
from typing import Optional, Tuple, Type

from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import transaction
from django.dispatch import receiver

from djstripe.models import Event
from djstripe.signals import webhook_event_processed

logger = logging.getLogger(__name__)
User = get_user_model()


# ---------- Small helpers ----------

def _get_model(app_label: str, model_name: str) -> Optional[Type]:
    """
    Try to import a model in a safe way.
    Returns None if the model doesn't exist (prevents hard crashes while you’re still building).
    """
    try:
        return apps.get_model(app_label, model_name)
    except (LookupError, ValueError):
        return None


def _get_user_and_course(user_id: str | int | None, course_id: str | int | None) -> Tuple[Optional[User], Optional[object]]:
    """
    Resolve user and course instances from IDs. Returns (user, course) or (None, None)
    if they can't be found. Adjust the Course model path if yours differs.
    """
    if not user_id or not course_id:
        logger.warning("Missing user_id or course_id in metadata. Skipping.")
        return None, None

    # 1) User
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        logger.error("Stripe webhook: user %s not found.", user_id)
        user = None

    # 2) Course
    Course = _get_model("elearning", "Course") or _get_model("elearning.modules", "Course")
    course = None
    if Course is None:
        logger.warning("Course model not found. Expected elearning.Course or elearning.modules.Course.")
    else:
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            logger.error("Stripe webhook: course %s not found.", course_id)

    return user, course


def _enroll_user_in_course(user: User, course: object, *, source: str, reference: Optional[str]) -> bool:
    """
    Idempotently enroll a user into a course. If your project uses a different model,
    adjust the import below (Enrollment/CourseEnrollment/etc).
    Returns True if a new enrollment was created, False if it already existed.
    """
    # Try several common enrollment model names; adjust to your actual one:
    Enrollment = (
        _get_model("elearning", "CourseEnrollment")
        or _get_model("elearning.modules", "CourseEnrollment")
        or _get_model("elearning", "Enrollment")
        or _get_model("elearning.modules", "Enrollment")
    )
    if Enrollment is None:
        logger.warning("Enrollment model not found. Please create one (e.g. CourseEnrollment) and update signals.")
        return False


    with transaction.atomic():
        obj, created = Enrollment.objects.get_or_create(
            user=user,
            course=course,
            defaults={"source": source, "reference": reference},
        )
        if created:
            logger.info("Enrolled user %s into course %s (source=%s, ref=%s).", user.id, course.id, source, reference)
        else:
            logger.info("Enrollment already exists for user %s and course %s (idempotent).", user.id, course.id)
        return created


def _record_payment(
    *,
    user: Optional[User],
    course: Optional[object],
    stripe_payment_intent_id: Optional[str],
    amount: Optional[int],
    currency: Optional[str],
    status: Optional[str],
    checkout_session_id: Optional[str] = None,
) -> None:
    """
    Optionally log payments into your own Payment table if it exists.
    """
    Payment = (
        _get_model("elearning", "Payment")
        or _get_model("elearning.payments", "Payment")
        or _get_model("payments", "Payment")
    )
    if Payment is None:
        logger.info(
            "Payment model not found. Skipping local payment record. "
            "PI=%s, amount=%s %s, status=%s, session=%s",
            stripe_payment_intent_id, amount, currency, status, checkout_session_id
        )
        return

    try:
        with transaction.atomic():
            Payment.objects.create(
                user=user,
                course=course,
                stripe_payment_intent_id=stripe_payment_intent_id,
                amount=amount,
                currency=currency,
                status=status,
                checkout_session_id=checkout_session_id,
            )
            logger.info("Recorded payment (PI=%s, status=%s).", stripe_payment_intent_id, status)
    except Exception as exc:
        logger.exception("Failed to record payment locally: %s", exc)


# ---------- Main webhook handler ----------

@receiver(webhook_event_processed)
def handle_webhook_processed(sender, **kwargs):
    """
    Runs after dj-stripe has verified the signature and saved the Event.
    Only trusted, de-duplicated events reach here.
    """
    event: Event = kwargs["event"]
    event_type = event.type
    data_object = event.data.get("object", {}) if isinstance(event.data, dict) else {}

    try:
        if event_type == "checkout.session.completed":
            _handle_checkout_session_completed(data_object)

        elif event_type == "payment_intent.succeeded":
            _handle_payment_intent_succeeded(data_object)

        elif event_type == "invoice.payment_succeeded":
            # Useful for subscriptions if added later
            _handle_invoice_payment_succeeded(data_object)

        elif event_type in {"charge.refunded", "charge.refund.updated"}:
            _handle_charge_refund(data_object)

        else:
            logger.debug("Unhandled Stripe event type: %s", event_type)

    except Exception as exc:
        # Never raise: webhook delivery may retry. Log and move on.
        logger.exception("Error while handling Stripe event %s: %s", event_type, exc)


# ---------- Event-specific handlers ----------

def _handle_checkout_session_completed(session: dict) -> None:
    """
    One-off course purchase completed via Stripe Checkout.
    We expect metadata to contain { course_id, user_id }.
    """
    metadata = session.get("metadata") or {}
    course_id = metadata.get("course_id")
    user_id = metadata.get("user_id")
    checkout_session_id = session.get("id")
    payment_intent_id = session.get("payment_intent")
    amount_total = session.get("amount_total")          # integer (cents)
    currency = session.get("currency")                  # e.g., "eur" or "usd"
    payment_status = session.get("payment_status")      # e.g., "paid"

    logger.info("Stripe checkout.session.completed received (session=%s, user=%s, course=%s).",
                checkout_session_id, user_id, course_id)

    user, course = _get_user_and_course(user_id, course_id)
    if not user or not course:
        return

    # Idempotent enrollment
    _enroll_user_in_course(user, course, source="stripe_checkout", reference=checkout_session_id)

    # Record local payment (optional)
    _record_payment(
        user=user,
        course=course,
        stripe_payment_intent_id=payment_intent_id,
        amount=amount_total,
        currency=currency,
        status=payment_status,
        checkout_session_id=checkout_session_id,
    )


def _handle_payment_intent_succeeded(payment_intent: dict) -> None:
    """
    Generic payment success handler (covers SetupIntent-based later charges or manual flows).
    Used if later we charge saved cards directly (not via Checkout).
    """
    pi_id = payment_intent.get("id")
    amount_received = payment_intent.get("amount_received")
    currency = payment_intent.get("currency")
    status = payment_intent.get("status")  # "succeeded"

    metadata = payment_intent.get("metadata") or {}
    user_id = metadata.get("user_id")
    course_id = metadata.get("course_id")

    logger.info("Stripe payment_intent.succeeded (pi=%s).", pi_id)

    user, course = _get_user_and_course(user_id, course_id)

    # If linked to a course purchase, enroll idempotently
    if user and course:
        _enroll_user_in_course(user, course, source="stripe_payment_intent", reference=pi_id)

    # Record local payment log (optional)
    _record_payment(
        user=user,
        course=course,
        stripe_payment_intent_id=pi_id,
        amount=amount_received,
        currency=currency,
        status=status,
    )


def _handle_invoice_payment_succeeded(invoice: dict) -> None:
    """
    Subscription payment succeeded (future-proofing if subscriptions are added).
    You may link the invoice to a Subscription and grant access accordingly.
    """
    subscription_id = invoice.get("subscription")
    amount_paid = invoice.get("amount_paid")
    currency = invoice.get("currency")
    status = "paid"

    # The invoice might have customer, lines, metadata, etc.
    metadata = invoice.get("metadata") or {}
    user_id = metadata.get("user_id")
    course_id = metadata.get("course_id")  # optional if subs map to courses

    logger.info("Stripe invoice.payment_succeeded (sub=%s).", subscription_id)

    user, course = _get_user_and_course(user_id, course_id)

    # grant access per subscription.
    if user and course:
        _enroll_user_in_course(user, course, source="stripe_subscription", reference=subscription_id)

    # Record local payment (optional)
    _record_payment(
        user=user,
        course=course,
        stripe_payment_intent_id=None,
        amount=amount_paid,
        currency=currency,
        status=status,
    )


def _handle_charge_refund(charge_or_refund: dict) -> None:
    """
    Handle refunds: mark local records as refunded and, if needed, revoke access.
    """
    # For charge.refunded, Stripe sends the Charge object with refunded=True.
    # For charge.refund.updated, Stripe sends the Refund object.
    charge_id = charge_or_refund.get("charge") or charge_or_refund.get("id")
    refunded = charge_or_refund.get("refunded") or charge_or_refund.get("status") == "succeeded"

    logger.info("Stripe refund event for charge=%s refunded=%s", charge_id, refunded)

    Payment = (
        _get_model("elearning", "Payment")
        or _get_model("elearning.payments", "Payment")
        or _get_model("payments", "Payment")
    )
    if Payment and charge_id:
        try:
            with transaction.atomic():
                qs = Payment.objects.filter(stripe_payment_intent_id=charge_id)
                if qs.exists():
                    qs.update(status="refunded")
                    logger.info("Marked %s local payment(s) as refunded for charge=%s.", qs.count(), charge_id)
        except Exception as exc:
            logger.exception("Failed to mark payment refunded locally: %s", exc)
