from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Importiere die View-Module aus unseren sauberen Unterordnern
from .authentications import views as auth_views
from .authentications.views.authentication_organisation_user import (
    MicrosoftOrganizationLoginView,
    MicrosoftOrganizationCallbackView,
    OrganizationUserStatusView
)
from .graph_apis import views as graph_views

app_name = 'microsoft_services'

# --- URL-Patterns für die jeweiligen Untermodule ---

# Alle URLs, die mit /authentications/... beginnen
authentications_urlpatterns = [
    # Microsoft Organization Authentication
    path('login/', MicrosoftOrganizationLoginView.as_view(), name='organization-login'),
    path('callback/', MicrosoftOrganizationCallbackView.as_view(), name='organization-callback'),
    path('user-status/', OrganizationUserStatusView.as_view(), name='user-status'),
]

# Alle URLs, die mit /graph/... beginnen
graph_urlpatterns = [
    # Nur User.Read.All Test
    path('test/', graph_views.UserReadTestView.as_view(), name='user-read-test'),
]

# --- Haupt-URL-Liste für die gesamte 'microsoft_services' App ---

urlpatterns = [
    # Bündelung der Untermodul-URLs mit ihren originalen Prefixen
    path('auth/', include((authentications_urlpatterns, 'authentications'))),
    path('graph/', include((graph_urlpatterns, 'graph'))),
] 