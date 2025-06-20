from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from .models import OAuthState


@admin.register(OAuthState)
class OAuthStateAdmin(admin.ModelAdmin):
    """
    Admin Interface für OAuth States
    
    Ermöglicht Monitoring und Management der OAuth States über Django Admin.
    """
    
    list_display = [
        'state_preview',
        'status_indicator', 
        'user_identifier_preview',
        'created_at',
        'expires_at',
        'time_remaining'
    ]
    
    list_filter = [
        'created_at',
        'expires_at',
        ('expires_at', admin.DateFieldListFilter),
    ]
    
    search_fields = [
        'state',
        'user_identifier'
    ]
    
    readonly_fields = [
        'state',
        'user_identifier', 
        'created_at',
        'expires_at',
        'status_indicator',
        'time_remaining'
    ]
    
    ordering = ['-created_at']
    
    list_per_page = 50
    
    def state_preview(self, obj):
        """Zeige nur ersten Teil des States aus Sicherheitsgründen"""
        return f"{obj.state[:12]}..."
    state_preview.short_description = "State"
    
    def user_identifier_preview(self, obj):
        """Zeige User Identifier mit Anonymisierung"""
        if obj.user_identifier:
            return f"{obj.user_identifier[:8]}..."
        return "-"
    user_identifier_preview.short_description = "User ID"
    
    def status_indicator(self, obj):
        """Visual indicator für State Status"""
        if obj.is_expired():
            return format_html(
                '<span style="color: #dc3545;">🔴 Abgelaufen</span>'
            )
        else:
            return format_html(
                '<span style="color: #28a745;">🟢 Aktiv</span>'
            )
    status_indicator.short_description = "Status"
    
    def time_remaining(self, obj):
        """Verbleibende Zeit bis Ablauf"""
        if obj.is_expired():
            time_expired = timezone.now() - obj.expires_at
            return f"Abgelaufen vor {time_expired}"
        else:
            time_left = obj.time_until_expiry()
            return f"Läuft ab in {time_left}"
    time_remaining.short_description = "Zeit verbleibend"
    
    def has_add_permission(self, request):
        """Neue OAuth States sollten nur über API erstellt werden"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """OAuth States sollten nicht manuell geändert werden"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Erlaubt manuelles Löschen für Cleanup"""
        return True
    
    actions = ['cleanup_expired_states']
    
    def cleanup_expired_states(self, request, queryset):
        """Admin Action zum Cleanup abgelaufener States"""
        count = OAuthState.cleanup_expired()
        if count > 0:
            self.message_user(
                request, 
                f"✅ {count} abgelaufene OAuth States wurden gelöscht."
            )
        else:
            self.message_user(
                request, 
                "✅ Keine abgelaufenen OAuth States gefunden."
            )
    cleanup_expired_states.short_description = "🗑️ Abgelaufene States bereinigen"
