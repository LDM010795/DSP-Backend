"""
Cleanup Inactive Users Management Command - DSP (Digital Solutions Platform)

Dieses Management Command bereinigt inaktive Benutzer, die ihr initiales Passwort
nicht innerhalb der vorgegebenen Zeit geändert haben.

Features:
- Automatische Bereinigung abgelaufener Benutzerkonten
- Konfigurierbare Timeout-Einstellungen
- Sichere Benutzerverwaltung mit Logging
- Detaillierte Ausgabe für Monitoring

Author: DSP Development Team
Created: 10.07.2025
Version: 1.0.0
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
import logging

User = get_user_model()

# Logger einrichten
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Django Management Command für die Bereinigung inaktiver Benutzer.

    Löscht Benutzer, die erstellt wurden, aber ihr initiales Passwort nicht
    innerhalb der vorgegebenen Zeit (standardmäßig 1 Stunde) geändert haben.

    Features:
    - Konfigurierbare Timeout-Einstellungen über PASSWORD_RESET_TIMEOUT
    - Sichere Benutzerverwaltung mit Logging
    - Detaillierte Ausgabe für Monitoring und Debugging
    """

    help = "Löscht Benutzer, die erstellt wurden, aber ihr initiales Passwort nicht innerhalb der vorgegebenen Zeit (standardmäßig 1 Stunde) geändert haben."

    def handle(self, *args, **options):
        """
        Hauptausführungsmethode für das Management Command.

        Args:
            *args: Zusätzliche Argumente
            **options: Command-Optionen

        Raises:
            CommandError: Bei Fehlern während der Ausführung
        """
        # Hole das Timeout aus den Settings, default 3600 Sekunden (1 Stunde)
        # Wir verwenden hier PASSWORD_RESET_TIMEOUT, da es bereits dafür gedacht ist
        timeout_seconds = getattr(settings, "PASSWORD_RESET_TIMEOUT", 3600)
        expiration_time = timezone.now() - timedelta(seconds=timeout_seconds)

        self.stdout.write(
            f"Suche nach Benutzern, die vor {expiration_time.strftime('%Y-%m-%d %H:%M:%S')} erstellt wurden und deren Passwortänderung noch aussteht..."
        )

        # Finde Kandidaten zum Löschen:
        # - Profil existiert (sollte immer der Fall sein dank Signalen)
        # - force_password_change ist True
        # - date_joined (Zeit der Erstellung) ist älter als die expiration_time
        try:
            users_to_delete = User.objects.filter(
                profile__isnull=False,
                profile__force_password_change=True,
                date_joined__lt=expiration_time,
            )

            count = users_to_delete.count()

            if count == 0:
                self.stdout.write(
                    self.style.SUCCESS("Keine abgelaufenen Benutzer gefunden.")
                )
                return

            self.stdout.write(f"{count} Benutzer gefunden, die gelöscht werden:")
            for user in users_to_delete:
                self.stdout.write(
                    f"  - {user.username} (ID: {user.id}), erstellt am {user.date_joined.strftime('%Y-%m-%d %H:%M:%S')}"
                )

            # Führe die Löschung durch
            deleted_count, _ = users_to_delete.delete()

            self.stdout.write(
                self.style.SUCCESS(f"{deleted_count} Benutzer erfolgreich gelöscht.")
            )

        except Exception as e:
            logger.error(
                f"Fehler beim Ausführen von cleanup_inactive_users: {e}", exc_info=True
            )
            raise CommandError(f"Ein Fehler ist aufgetreten: {e}")
