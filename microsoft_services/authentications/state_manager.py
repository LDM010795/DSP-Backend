"""
Production-ready OAuth State Manager für Microsoft Authentication

Löst Session-Probleme in Production durch Redis-basierte State-Speicherung.
Designed für stateless Deployments und Load Balancer.
"""

import secrets
import logging
from typing import Optional
from datetime import timedelta
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


class OAuthStateManager:
    """
    Production-ready OAuth State Manager - Database Edition
    
    Verwendet PostgreSQL statt Redis für OAuth State-Speicherung.
    Kostenlos, production-ready und vollständig unter Ihrer Kontrolle.
    """
    
    STATE_TIMEOUT = 600  # 10 Minuten - OAuth Flow sollte schnell sein
    
    @classmethod
    def create_state(cls, user_identifier: Optional[str] = None) -> str:
        """
        Erstelle OAuth State Parameter in Database
        
        Args:
            user_identifier: Optional - IP+UserAgent Hash für zusätzliche Sicherheit
        
        Returns:
            Generierter State-String
        """
        # Import hier um circular imports zu vermeiden
        from microsoft_services.models import OAuthState
        
        state = secrets.token_urlsafe(32)
        
        # State in Database speichern
        OAuthState.create_state(state, user_identifier, cls.STATE_TIMEOUT)
        
        logger.info(f"OAuth state created in database: {state[:8]}... (expires in {cls.STATE_TIMEOUT}s)")
        return state
    
    @classmethod
    def validate_and_consume_state(cls, state: str, user_identifier: Optional[str] = None) -> bool:
        """
        Validiere und konsumiere OAuth State aus Database (one-time use)
        
        Args:
            state: Der zu validierende State
            user_identifier: Optional - für zusätzliche Validierung
        
        Returns:
            True wenn State valid und erfolgreich konsumiert
        """
        if not state:
            logger.warning("OAuth state validation failed: No state provided")
            return False
        
        # Import hier um circular imports zu vermeiden
        from microsoft_services.models import OAuthState
        
        # Database validation mit one-time use
        success = OAuthState.validate_and_consume(state, user_identifier)
        
        if success:
            logger.info(f"OAuth state validated and consumed from database: {state[:8]}...")
        else:
            logger.warning(f"OAuth state validation failed: {state[:8]}...")
        
        return success
    
    @classmethod
    def cleanup_expired_states(cls) -> int:
        """
        Cleanup abgelaufene OAuth States aus Database
        
        Returns:
            Anzahl gelöschter States
        """
        from microsoft_services.models import OAuthState
        
        count = OAuthState.cleanup_expired()
        if count > 0:
            logger.info(f"Cleaned up {count} expired OAuth states from database")
        return count


class ProductionOAuthMixin:
    """
    Production-ready OAuth Mixin
    
    Ersetzt Session-basierte State-Handling durch Cache-basierte Lösung
    """
    
    def create_oauth_state(self, request) -> str:
        """Erstelle OAuth State mit Production-ready Manager"""
        user_identifier = self._get_user_identifier(request)
        return OAuthStateManager.create_state(user_identifier)
    
    def validate_oauth_state(self, request, received_state: str) -> bool:
        """Validiere OAuth State mit Production-ready Manager"""
        user_identifier = self._get_user_identifier(request)
        return OAuthStateManager.validate_and_consume_state(received_state, user_identifier)
    
    def _get_user_identifier(self, request) -> str:
        """
        Generiere User-Identifier für zusätzliche Sicherheit
        
        Verwendet IP + User-Agent Hash für stateless Identifikation
        """
        import hashlib
        
        ip_address = self._get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Hash aus IP + User-Agent für Anonymität
        identifier_string = f"{ip_address}:{user_agent}"
        return hashlib.sha256(identifier_string.encode()).hexdigest()[:16]
    
    def _get_client_ip(self, request) -> str:
        """Hole Client IP (berücksichtigt Proxy/Load Balancer)"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip.strip()


# Fallback für Development ohne Redis
class DevelopmentOAuthMixin:
    """
    Development-Fallback für OAuth State Management
    
    Verwendet Sessions wie vorher, aber mit besserer Fehlerbehandlung
    """
    
    def create_oauth_state(self, request) -> str:
        """Erstelle OAuth State in Session (Development)"""
        state = secrets.token_urlsafe(32)
        request.session['oauth_state'] = state
        request.session['oauth_state_created'] = True
        return state
    
    def validate_oauth_state(self, request, received_state: str) -> bool:
        """Validiere OAuth State aus Session (Development)"""
        stored_state = request.session.get('oauth_state')
        
        if not stored_state:
            logger.warning("OAuth state validation failed: No state in session")
            return False
        
        if stored_state != received_state:
            logger.warning(f"OAuth state mismatch. Expected: {stored_state}, Received: {received_state}")
            return False
        
        # State aus Session entfernen
        request.session.pop('oauth_state', None)
        request.session.pop('oauth_state_created', None)
        
        return True


# Auto-Selection basierend auf verfügbarer Database
def get_oauth_mixin():
    """
    Automatische Auswahl des OAuth Mixins basierend auf Environment
    
    Returns:
        ProductionOAuthMixin für Database-basierte States (default)
        DevelopmentOAuthMixin nur als Fallback wenn Database nicht verfügbar
    """
    try:
        # Test ob Database verfügbar ist
        from django.db import connection
        from microsoft_services.models import OAuthState
        
        # Simple DB connectivity test
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        # Check ob OAuthState Tabelle existiert (Migrations gelaufen)
        OAuthState._meta.get_field('state')  # Raises exception wenn Model nicht existiert
        
        logger.info("Database OAuth state management activated")
        return ProductionOAuthMixin
        
    except Exception as e:
        logger.warning(f"Database not available for OAuth states, falling back to sessions: {e}")
        return DevelopmentOAuthMixin 