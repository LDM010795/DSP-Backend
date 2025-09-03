from django.urls import path
from .views import (
    CreateSetupIntentView,
    CreateCheckoutSessionView,
    GetStripeConfigView,
    ListPaymentMethodsView,
    SetDefaultPaymentMethodView,
)

app_name = "stripe_integration"

urlpatterns = [
    path("stripe/config/", GetStripeConfigView.as_view(), name="stripe-config"),
    path("stripe/setup-intent/", CreateSetupIntentView.as_view(), name="stripe-setup-intent"),
    path("stripe/checkout-session/", CreateCheckoutSessionView.as_view(), name="stripe-checkout-session"),
    path("stripe/payment-methods/", ListPaymentMethodsView.as_view(), name="stripe-list-payment-methods"),
    path("stripe/payment-methods/default/", SetDefaultPaymentMethodView.as_view(), name="stripe-set-default-payment-method"),
]

