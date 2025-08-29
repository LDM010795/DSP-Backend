"""
E-Learning User Management Models

This module defines the user-related models for the E-Learning system,
extending Django's built-in User model with additional profile functionality
and automatic profile management through Django signals.

Models:
- Profile: Extended user information and system-specific settings

Features:
- Automatic profile creation for new users
- Force password change functionality for first-time login security
- Proper signal handling for profile lifecycle management

Author: DSP Development Team
Version: 1.0.0
"""

from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _


class Profile(models.Model):
    """
    Extended user profile model for the E-Learning system.

    This model extends the default Django User model with additional
    functionality specific to the E-Learning platform, including
    security settings and user preferences.

    Attributes:
        user: One-to-one relationship with Django User model
        force_password_change: Security flag requiring password change on next login

    The profile is automatically created when a new user is registered
    and maintains a one-to-one relationship with the User model.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name=_("User"),
        help_text=_("Associated user account"),
    )

    force_password_change = models.BooleanField(
        default=True,
        verbose_name=_("Force Password Change"),
        help_text=_("Require user to change password on next login for security"),
    )

    class Meta:
        verbose_name = _("User Profile")
        verbose_name_plural = _("User Profiles")
        db_table = "elearning_profile"

    def __str__(self) -> str:
        """
        String representation of the profile.

        Returns:
            Formatted string with username and profile indicator
        """
        return f"{self.user.username} Profile"

    def __repr__(self) -> str:
        """
        Developer representation of the profile.

        Returns:
            Detailed string for debugging purposes
        """
        return f"<Profile(user={self.user.username}, force_password_change={self.force_password_change})>"

    @property
    def needs_password_change(self) -> bool:
        """
        Check if user needs to change their password.

        Returns:
            True if password change is required, False otherwise
        """
        return self.force_password_change

    def mark_password_changed(self) -> None:
        """
        Mark that user has changed their password.

        This method should be called after a successful password change
        to remove the force password change requirement.
        """
        self.force_password_change = False
        self.save(update_fields=["force_password_change"])


# --- Signal Handlers for Automatic Profile Management ---


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created: bool, **kwargs) -> None:
    """
    Automatically create a user profile when a new user is created.

    This signal handler ensures that every user has an associated profile
    without requiring manual intervention.

    Args:
        sender: The User model class
        instance: The actual User instance that was saved
        created: Boolean indicating if this is a new instance
        **kwargs: Additional signal arguments
    """
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_profile(sender, instance, **kwargs) -> None:
    """
    Ensure user profile exists and is saved when user is saved.

    This signal handler provides a safety net to ensure profiles exist
    even if the creation signal failed or was bypassed.

    Args:
        sender: The User model class
        instance: The actual User instance that was saved
        **kwargs: Additional signal arguments
    """
    try:
        # Try to save existing profile
        instance.profile.save()
    except Profile.DoesNotExist:
        # Create profile if it doesn't exist
        Profile.objects.create(user=instance)
