from django.urls import path, include

# Direkte Imports der Views
from .authentications.views.authentication_organisation_user import (
    MicrosoftOrganizationLoginView,
    MicrosoftOrganizationCallbackView,
    MicrosoftAuthTokensView,
    OrganizationUserStatusView
)
from .graph_apis.views import UserReadTestView

app_name = 'microsoft_services'

# --- URL-Patterns für die jeweiligen Untermodule ---

# Alle URLs, die mit /auth/... beginnen
authentications_urlpatterns = [
    # Microsoft Organization Authentication
    path('login/', MicrosoftOrganizationLoginView.as_view(), name='organization-login'),
    path('callback/', MicrosoftOrganizationCallbackView.as_view(), name='organization-callback'),
    path('tokens/', MicrosoftAuthTokensView.as_view(), name='auth-tokens'),
    path('user-status/', OrganizationUserStatusView.as_view(), name='user-status'),
]

# Alle URLs, die mit /graph/... beginnen
graph_urlpatterns = [
    # Microsoft Graph API Test
    path('test/', UserReadTestView.as_view(), name='user-read-test'),
]

# --- Haupt-URL-Liste für die gesamte 'microsoft_services' App ---

urlpatterns = [
    # Bündelung der Untermodul-URLs mit ihren originalen Prefixen
    path('auth/', include((authentications_urlpatterns, 'authentications'))),
    path('graph/', include((graph_urlpatterns, 'graph'))),
] 