"""
Cleanup OAuth States Command - DSP (Digital Solutions Platform)

Dieses Django Management Command bereinigt abgelaufene OAuth States aus der Datenbank.
Kann manuell oder automatisiert (z.B. via Cronjob) ausgeführt werden.

Features:
- Dry-Run und verbose Modus für sichere Ausführung
- Statistiken und Empfehlungen für regelmäßige Bereinigung
- Performance- und Security-Empfehlungen

Author: DSP Development Team
Created: 10.07.2025
Version: 1.0.0
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from core.microsoft_services.models import OAuthState

# --- Management Command: Cleanup abgelaufene OAuth States ---


class Command(BaseCommand):
    """
    Cleanup abgelaufene OAuth States

    Usage:
        python manage.py cleanup_oauth_states
        python manage.py cleanup_oauth_states --dry-run
        python manage.py cleanup_oauth_states --verbose
    """

    help = "Cleanup abgelaufene OAuth States aus der Database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Zeige nur was gelöscht werden würde, ohne tatsächlich zu löschen",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Zeige detaillierte Informationen",
        )

    def handle(self, *args, **options):
        """Command Hauptlogik"""
        dry_run = options["dry_run"]
        verbose = options["verbose"]

        # Aktuelle Zeit für Vergleich
        now = timezone.now()

        # Abgelaufene States finden
        expired_states = OAuthState.objects.filter(expires_at__lt=now)
        expired_count = expired_states.count()

        if expired_count == 0:
            self.stdout.write(
                self.style.SUCCESS("✅ Keine abgelaufenen OAuth States gefunden")
            )
            return

        # Statistiken anzeigen
        if verbose:
            self.stdout.write("\n📊 OAuth State Statistiken:")
            total_states = OAuthState.objects.count()
            active_states = OAuthState.objects.filter(expires_at__gt=now).count()

            self.stdout.write(f"   Total States: {total_states}")
            self.stdout.write(f"   Aktive States: {active_states}")
            self.stdout.write(f"   Abgelaufene States: {expired_count}")

            # Älteste und neueste abgelaufene States
            if expired_count > 0:
                oldest = expired_states.order_by("created_at").first()
                newest = expired_states.order_by("-created_at").first()

                self.stdout.write(
                    f"   Ältester abgelaufener State: {oldest.created_at}"
                )
                self.stdout.write(
                    f"   Neuester abgelaufener State: {newest.created_at}"
                )

        # Dry run oder tatsächlich löschen
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"🔍 DRY RUN: Würde {expired_count} abgelaufene OAuth States löschen"
                )
            )

            if verbose and expired_count <= 10:
                self.stdout.write("\n📋 States die gelöscht werden würden:")
                for state in expired_states[:10]:
                    time_expired = now - state.expires_at
                    self.stdout.write(
                        f"   - {state.state[:12]}... (abgelaufen vor {time_expired})"
                    )
        else:
            # Tatsächlich löschen
            deleted_count = OAuthState.cleanup_expired()

            if deleted_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ {deleted_count} abgelaufene OAuth States erfolgreich gelöscht"
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS("✅ Keine OAuth States zu löschen")
                )

        # Performance-Empfehlungen
        if verbose:
            self.stdout.write("\n💡 Empfehlungen:")

            if expired_count > 100:
                self.stdout.write(
                    "   - Führen Sie dieses Command öfter aus (z.B. täglich)"
                )
                self.stdout.write(
                    "   - Erwägen Sie einen Cronjob für automatische Bereinigung"
                )

            active_count = OAuthState.get_active_count()
            if active_count > 50:
                self.stdout.write(
                    "   - Viele aktive States - prüfen Sie auf hängende OAuth Flows"
                )

            self.stdout.write("   - Nächste empfohlene Bereinigung: in 24 Stunden")

        # Cronjob Beispiel
        if verbose and not dry_run:
            self.stdout.write("\n⏰ Automatische Bereinigung einrichten:")
            self.stdout.write("   Fügen Sie zu Ihrer crontab hinzu:")
            self.stdout.write(
                "   0 2 * * * cd /path/to/project && python manage.py cleanup_oauth_states"
            )
            self.stdout.write("   (Läuft täglich um 2:00 Uhr morgens)")
