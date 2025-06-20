from django.db import models, transaction
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class OAuthState(models.Model):
    """
    OAuth State Storage in Database - Production-ready & kostenlos
    
    Speichert OAuth States mit automatischem Expiry und One-Time-Use.
    Ersetzt Redis für OAuth CSRF-Protection in stateless Deployments.
    """
    
    state = models.CharField(
        max_length=255, 
        unique=True, 
        db_index=True,
        help_text="OAuth State Parameter für CSRF-Protection"
    )
    user_identifier = models.CharField(
        max_length=255, 
        null=True, 
        blank=True,
        help_text="Hash von IP+UserAgent für zusätzliche Sicherheit"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Wann wurde der State erstellt"
    )
    expires_at = models.DateTimeField(
        db_index=True,
        help_text="Wann läuft der State ab (TTL)"
    )
    
    class Meta:
        db_table = 'oauth_states'
        verbose_name = 'OAuth State'
        verbose_name_plural = 'OAuth States'
        indexes = [
            models.Index(fields=['state'], name='oauth_state_idx'),
            models.Index(fields=['expires_at'], name='oauth_expires_idx'),
            models.Index(fields=['created_at'], name='oauth_created_idx'),
        ]
        ordering = ['-created_at']
    
    @classmethod
    def create_state(cls, state: str, user_identifier: str = None, timeout: int = 600):
        """
        Erstelle OAuth State mit automatischem Expiry
        
        Args:
            state: Der OAuth State String
            user_identifier: Optional - Hash von IP+UserAgent
            timeout: Sekunden bis Expiry (default: 10 Minuten)
        
        Returns:
            OAuthState instance
        """
        expires_at = timezone.now() + timedelta(seconds=timeout)
        
        oauth_state = cls.objects.create(
            state=state,
            user_identifier=user_identifier,
            expires_at=expires_at
        )
        
        logger.info(f"OAuth state created in database: {state[:8]}... (expires: {expires_at})")
        return oauth_state
    
    @classmethod
    def validate_and_consume(cls, state: str, user_identifier: str = None) -> bool:
        """
        Validiere und konsumiere OAuth State (one-time use)
        
        Args:
            state: Der zu validierende State
            user_identifier: Optional - für zusätzliche Validierung
        
        Returns:
            True wenn State valid und erfolgreich konsumiert
        """
        try:
            # Atomic operation für Thread-Safety
            with transaction.atomic():
                oauth_state = cls.objects.select_for_update().get(
                    state=state,
                    expires_at__gt=timezone.now()  # Nicht abgelaufen
                )
                
                # User identifier check für zusätzliche Sicherheit
                if user_identifier and oauth_state.user_identifier != user_identifier:
                    logger.warning(f"OAuth state user identifier mismatch: {state[:8]}...")
                    return False
                
                # State löschen (one-time use)
                oauth_state.delete()
                
                logger.info(f"OAuth state validated and consumed: {state[:8]}...")
                return True
                
        except cls.DoesNotExist:
            logger.warning(f"OAuth state not found or expired: {state[:8]}...")
            return False
        except Exception as e:
            logger.error(f"OAuth state validation error: {e}")
            return False
    
    @classmethod  
    def cleanup_expired(cls) -> int:
        """
        Cleanup abgelaufene OAuth States
        
        Returns:
            Anzahl gelöschter States
        """
        try:
            count, _ = cls.objects.filter(expires_at__lt=timezone.now()).delete()
            if count > 0:
                logger.info(f"Cleaned up {count} expired OAuth states")
            return count
        except Exception as e:
            logger.error(f"OAuth state cleanup error: {e}")
            return 0
    
    @classmethod
    def get_active_count(cls) -> int:
        """Anzahl aktiver (nicht abgelaufener) States"""
        return cls.objects.filter(expires_at__gt=timezone.now()).count()
    
    def is_expired(self) -> bool:
        """Check ob dieser State abgelaufen ist"""
        return timezone.now() > self.expires_at
    
    def time_until_expiry(self) -> timedelta:
        """Zeit bis zum Ablauf"""
        return self.expires_at - timezone.now()
    
    def __str__(self):
        status = "expired" if self.is_expired() else "active"
        return f"OAuth State {self.state[:8]}... ({status}, expires: {self.expires_at})"
