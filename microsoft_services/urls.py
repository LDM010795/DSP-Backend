from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Importiere die View-Module aus unseren sauberen Unterordnern
from .authentications import views as auth_views

app_name = 'microsoft_services'

# --- URL-Patterns für die jeweiligen Untermodule ---

# Alle URLs, die mit /authentications/... beginnen
authentications_urlpatterns = [
    # Hier werden später die Authentication-Views hinzugefügt
    # path('oauth/', auth_views.OAuthView.as_view(), name='oauth'),
    # path('token/', auth_views.TokenView.as_view(), name='token'),
]

# --- Haupt-URL-Liste für die gesamte 'microsoft_services' App ---

urlpatterns = [
    # Bündelung der Untermodul-URLs mit ihren originalen Prefixen
    path('authentications/', include((authentications_urlpatterns, 'authentications'))),
] 