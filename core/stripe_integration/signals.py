"""
Stripe Webhook Handlers (core.stripe_integration.signals)
=========================================================

This module listens to Stripe webhook events via dj-stripe.
We use Django’s stable `post_save` signal on `djstripe.models.Event`
instead of version-specific signals. That guarantees compatibility
and ensures we only process verified, de-duplicated events.

Responsibilities
----------------
1. One-off Purchases
   - Event: checkout.session.completed
   - Action: enroll user into course (via metadata) and optionally
     record a local Payment object.

2. Saved Card Charges
   - Event: payment_intent.succeeded
   - Action: enroll user (if metadata is present), record payment.

3. Subscriptions (future extension)
   - Event: invoice.payment_succeeded
   - Action: grant subscription access, record payment.

4. Refunds
   - Events: charge.refunded, charge.refund.updated
   - Action: mark local Payment as refunded.

5. SetupIntents
   - Event: setup_intent.succeeded
   - Action: attach the card to the Customer and mark as default.

Event Flow
----------
Stripe → Webhook → dj-stripe verifies & saves Event →
post_save(Event) → this module processes the payload.

Safety & Idempotency
--------------------
- Enrollments use `get_or_create` to avoid duplicates.
- Payment creation is atomic and logged.
- Failures are logged but never re-raised (to avoid retry storms).

Extensibility
-------------
- Works with Course/Enrollment/Payment models if present.
- Can be extended to handle invoices, subscriptions, or other products.

Security
--------
- Events are handled only after dj-stripe signature verification.
- Metadata is trusted only when set server-side (e.g., by Checkout creation).

Author: DSP Development Team
Date: 2025-08-21
"""


from __future__ import annotations

import logging
from typing import Optional, Tuple, Type, Any, Dict

from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from djstripe.models import Event
import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

logger = logging.getLogger(__name__)
User = get_user_model()


# ---------- helpers ----------

def _get_model(app_label: str, model_name: str) -> Optional[Type]:
    try:
        return apps.get_model(app_label, model_name)
    except (LookupError, ValueError):
        return None


def _extract_data_object(event: Event) -> Dict[str, Any]:
    """
    dj-stripe stores the raw Stripe JSON in `event.data`. Depending on
    dj-stripe version and event type, the payload shape can vary a bit.

    Preferred shape:
      event.data == {"object":"event", "data":{"object":{...}}}
    Fallbacks supported here.
    """
    try:
        data = event.data or {}
        # Standard Stripe event shape
        if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
            obj = data["data"].get("object")
            if isinstance(obj, dict):
                return obj
        # Fallback: sometimes `object` is top-level
        if isinstance(data, dict) and "object" in data and isinstance(data["object"], dict):
            return data["object"]
    except Exception:
        logger.exception("Failed to parse Event.data")
    return {}


def _get_user_and_course(user_id: str | int | None, course_id: str | int | None) -> Tuple[Optional[User], Optional[object]]:
    if not user_id or not course_id:
        logger.warning("Missing user_id or course_id in metadata. Skipping.")
        return None, None

    # user
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        logger.error("Stripe webhook: user %s not found.", user_id)
        user = None

    # course (try a couple of likely locations)
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
    Idempotently enroll a user into a course. Adjust model/fields if needed.
    Returns True if created, False if it already existed.
    """
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
            logger.info("Enrollment already exists for user %s and course %s.", user.id, course.id)
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
    Optionally persist a local Payment row (if you have such a model).
    Safe no-op if not present.
    """
    Payment = (
        _get_model("elearning", "Payment")
        or _get_model("elearning.payments", "Payment")
        or _get_model("payments", "Payment")
    )
    if Payment is None:
        logger.info(
            "Payment model not found. Skipping local record. "
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


# ---------- signal entrypoint (version-agnostic) ----------

@receiver(post_save, sender=Event)
def on_djstripe_event_created(sender, instance: Event, created: bool, **kwargs):
    """
    Runs as soon as dj-stripe saves a new Event (after signature verification & de-dup).
    Only trusted events reach here. We keep processing idempotent.
    """
    if not created:
        return

    event_type = instance.type
    obj = _extract_data_object(instance)

    logger.info("[webhook] %s (event_id=%s)", event_type, instance.id)

    try:
        if event_type == "setup_intent.succeeded":
            _handle_setup_intent_succeeded(obj)

        elif event_type == "checkout.session.completed":
            _handle_checkout_session_completed(obj)

        elif event_type == "payment_intent.succeeded":
            _handle_payment_intent_succeeded(obj)

        elif event_type == "invoice.payment_succeeded":
            _handle_invoice_payment_succeeded(obj)

        elif event_type in {"charge.refunded", "charge.refund.updated"}:
            _handle_charge_refund(obj)

        else:
            logger.debug("Unhandled event type: %s", event_type)

    except Exception as exc:
        # Never re-raise: Stripe may retry. We just log.
        logger.exception("Error handling event %s: %s", event_type, exc)


# ---------- concrete handlers ----------

def _handle_checkout_session_completed(session: Dict[str, Any]) -> None:
    metadata = session.get("metadata") or {}
    course_id = metadata.get("course_id")
    user_id = metadata.get("user_id")
    checkout_session_id = session.get("id")
    payment_intent_id = session.get("payment_intent")
    amount_total = session.get("amount_total")          # cents
    currency = session.get("currency")                  # "eur"/"usd"
    payment_status = session.get("payment_status")      # "paid"

    logger.info("checkout.session.completed session=%s user=%s course=%s", checkout_session_id, user_id, course_id)

    user, course = _get_user_and_course(user_id, course_id)
    if not user or not course:
        return

    _enroll_user_in_course(user, course, source="stripe_checkout", reference=checkout_session_id)

    _record_payment(
        user=user,
        course=course,
        stripe_payment_intent_id=payment_intent_id,
        amount=amount_total,
        currency=currency,
        status=payment_status,
        checkout_session_id=checkout_session_id,
    )


def _handle_payment_intent_succeeded(payment_intent: Dict[str, Any]) -> None:
    pi_id = payment_intent.get("id")
    amount_received = payment_intent.get("amount_received")
    currency = payment_intent.get("currency")
    status = payment_intent.get("status")  # "succeeded"
    metadata = payment_intent.get("metadata") or {}

    user_id = metadata.get("user_id")
    course_id = metadata.get("course_id")

    logger.info("payment_intent.succeeded pi=%s", pi_id)

    user, course = _get_user_and_course(user_id, course_id)
    if user and course:
        _enroll_user_in_course(user, course, source="stripe_payment_intent", reference=pi_id)

    _record_payment(
        user=user,
        course=course,
        stripe_payment_intent_id=pi_id,
        amount=amount_received,
        currency=currency,
        status=status,
    )


def _handle_invoice_payment_succeeded(invoice: Dict[str, Any]) -> None:
    subscription_id = invoice.get("subscription")
    amount_paid = invoice.get("amount_paid")
    currency = invoice.get("currency")
    status = "paid"
    metadata = invoice.get("metadata") or {}
    user_id = metadata.get("user_id")
    course_id = metadata.get("course_id")

    logger.info("invoice.payment_succeeded sub=%s", subscription_id)

    user, course = _get_user_and_course(user_id, course_id)
    if user and course:
        _enroll_user_in_course(user, course, source="stripe_subscription", reference=subscription_id)

    _record_payment(
        user=user,
        course=course,
        stripe_payment_intent_id=None,
        amount=amount_paid,
        currency=currency,
        status=status,
    )


def _handle_charge_refund(charge_or_refund: Dict[str, Any]) -> None:
    charge_id = charge_or_refund.get("charge") or charge_or_refund.get("id")
    refunded = charge_or_refund.get("refunded") or charge_or_refund.get("status") == "succeeded"

    logger.info("refund event charge=%s refunded=%s", charge_id, refunded)

    Payment = (
        _get_model("elearning", "Payment")
        or _get_model("elearning.payments", "Payment")
        or _get_model("payments", "Payment")
    )
    if not Payment or not charge_id:
        return

    try:
        with transaction.atomic():
            # If your Payment stores charge_id separately, adjust this filter.
            qs = Payment.objects.filter(stripe_payment_intent_id=charge_id)
            if qs.exists():
                qs.update(status="refunded")
                logger.info("Marked %s local payment(s) as refunded for charge=%s.", qs.count(), charge_id)
    except Exception as exc:
        logger.exception("Failed to mark payment refunded: %s", exc)


def _handle_setup_intent_succeeded(setup_intent: Dict[str, Any]) -> None:
    """
       On `setup_intent.succeeded`, attach the PaymentMethod to the Customer
       and set it as the default for future invoices. Ensures saved cards are
       usable without re-entering details. Idempotent and logs errors.
    """

    customer_id = setup_intent.get("customer")
    pm_id = setup_intent.get("payment_method")
    if not customer_id or not pm_id:
        logger.warning("setup_intent.succeeded missing customer or payment_method")
        return

    try:
        # Attach (idempotent): will no-op/error if already attached — safe to try
        try:
            stripe.PaymentMethod.attach(pm_id, customer=customer_id)
        except stripe.error.InvalidRequestError as e:
            if "already exists" not in str(e).lower():
                raise

        # Make default for invoices (the key to stop “ask for card again”)
        stripe.Customer.modify(
            customer_id,
            invoice_settings={"default_payment_method": pm_id},
        )
        logger.info("Set default PaymentMethod %s for customer %s", pm_id, customer_id)
    except Exception:
        logger.exception("Failed handling setup_intent.succeeded")