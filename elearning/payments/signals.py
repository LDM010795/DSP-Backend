"""
Stripe Webhook Signal Handlers for E‑Learning Payments (version‑agnostic)
========================================================================

Overview
--------
This module contains **post‑processing handlers** for Stripe webhooks using
`dj-stripe`. Unlike an earlier variant that listened to
`djstripe.signals.webhook_event_processed` (not present in all versions),
this module hooks into **Django’s stable `post_save` signal on
`djstripe.models.Event`**. That means it runs **after dj‑stripe has verified
the signature, de‑duplicated the event, and stored it in the database**,
but without relying on a version‑specific signal. The handlers therefore
only receive **trusted and idempotent** events and work across dj‑stripe versions.

What this module does
---------------------
1) **One‑off Purchases (Checkout)**
   - On `checkout.session.completed`, enroll the user into the purchased
     course (using metadata `{ "user_id": ..., "course_id": ... }` set by the
     backend when creating the Checkout Session).
   - Optionally create a local `Payment` record for reporting/analytics.

2) **Direct Charges / Saved Cards**
   - On `payment_intent.succeeded`, if the backend later charges saved cards
     (PaymentIntents created server‑side), this handler can also enroll users
     (when metadata contains course/user) and persist payment details.

3) **Subscriptions (Future‑proof)**
   - On `invoice.payment_succeeded`, if subscriptions are added, grant access
     accordingly and record the payment.

4) **Refunds**
   - On `charge.refunded` or `charge.refund.updated`, mark local payment
     records as refunded and (optionally) revoke access.

Event Handling Matrix
---------------------
- `checkout.session.completed`  → enroll user, record payment
- `payment_intent.succeeded`    → enroll (if metadata present), record payment
- `invoice.payment_succeeded`   → grant access for subscriptions, record payment
- `charge.refunded/*updated*`   → mark local payments as refunded

Data Flow (Happy Path)
----------------------
Stripe → Webhook → **dj‑stripe verifies & saves `Event`** → this module receives
**`post_save(Event)`** and:
  1. Reads `event.type` and extracts the payload from `event.data` safely.
  2. Reads `metadata.user_id` & `metadata.course_id` when applicable.
  3. Loads `User` and `Course` from the DB.
  4. **Idempotently** creates an `Enrollment` (via `get_or_create`).
  5. Optionally persists a local `Payment` row for analytics/reporting.

Assumptions & Model Integration
-------------------------------
- **User**: standard Django user (`get_user_model()`).
- **Course**: a model named `Course` in `elearning` or `elearning.modules`.
- **Enrollment**: a model named `CourseEnrollment` or `Enrollment` with fields
  `user`, `course` (plus optional `source`, `reference`).
- **Payment** (optional): a model in `elearning` / `elearning.payments` /
  `payments` with fields like:
  `user`, `course`, `stripe_payment_intent_id`, `amount`, `currency`, `status`,
  `checkout_session_id`.

If your actual model names/fields differ, adjust the `_get_model(...)` lookups
and the writes in `_enroll_user_in_course(...)` and `_record_payment(...)`.

Why `post_save(Event)` instead of `webhook_event_processed`
-----------------------------------------------------------
- **Compatibility:** Some dj‑stripe versions don’t expose `webhook_event_processed`.
- **Reliability:** `post_save(Event)` still fires **after** signature verification
  and persistence, so events are de‑duplicated and trustworthy.
- **Simplicity:** One unified, version‑agnostic entrypoint reduces breakage risk.

Idempotency & Safety
--------------------
- Handlers never re‑raise exceptions out of the signal; failures are logged to
  avoid webhook retry storms.
- Enrollment uses `get_or_create` to prevent duplicates on Stripe retries.
- Writes are wrapped in short `transaction.atomic()` blocks.

Security Considerations
-----------------------
- Events are processed **after** dj‑stripe signature verification.
- Never trust client‑side metadata for access control unless it was set by the
  backend (here we rely on metadata we add when creating Checkout Sessions).

Local Payment Recording (Optional)
---------------------------------
- If a `Payment` model exists, payments are recorded. If not, the module logs
  that local recording was skipped. This keeps reporting optional and decoupled.

Logging
-------
- Success paths and decisions (enrollment created/already exists) are logged at
  `INFO` level.
- Missing models or objects are logged with enough context for debugging.
- Exceptions are logged with stack traces; processing continues to keep webhook
  delivery healthy.

Author: DSP Development Team
Date: [2025-08-21]
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
        if event_type == "checkout.session.completed":
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


@receiver(post_save, sender=Event)
def _on_djstripe_event_saved(sender, instance: Event, created: bool, **kwargs):
    """
    Runs after dj-stripe has validated & stored the event.
    We only handle on first save (created=True) to avoid reprocessing on updates.
    """
    if not created:
        return  # avoid reprocessing when dj-stripe touches the row later

    # Extract type & payload safely
    event_type = instance.type
    data_object = instance.data.get("object", {}) if isinstance(instance.data, dict) else {}

    try:
        if event_type == "checkout.session.completed":
            _handle_checkout_session_completed(data_object)

        elif event_type == "payment_intent.succeeded":
            _handle_payment_intent_succeeded(data_object)

        elif event_type == "invoice.payment_succeeded":
            _handle_invoice_payment_succeeded(data_object)

        elif event_type in {"charge.refunded", "charge.refund.updated"}:
            _handle_charge_refund(data_object)

        else:
            # Not interesting for us—keep logs quiet to avoid noise
            logger.debug("Ignoring Stripe event type: %s (id=%s)", event_type, instance.id)

    except Exception as exc:
        # Never raise from a signal—log and move on to prevent retry storms
        logger.exception("Error handling Stripe event %s (id=%s): %s", event_type, instance.id, exc)