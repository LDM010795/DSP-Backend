"""
E-Learning Application Django Admin Configuration

This module provides comprehensive Django admin interface configuration for all
E-Learning models. It implements advanced admin features including inline editing,
custom list displays, filtering, and search capabilities.

The admin interface is organized into logical sections:
- User Management: Extended user administration with profile integration
- Module Management: Learning content and module administration
- Examination System: Exam creation, attempt tracking, and grading

Features:
- Enhanced user administration with profile integration
- Comprehensive filtering and search capabilities
- Inline editing for related models
- Custom field displays and readonly configurations
- Proper permission handling and security measures

Author: DSP Development Team
Version: 1.0.0
"""

from typing import Optional
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.db.models import QuerySet
from django.http import HttpRequest

# Import all models from the central models registry
from .models import (
    Profile,
    Module,
    ModuleAccess,
    Chapter,
    Content,
    Task,
    UserTaskProgress,
    Exam,
    ExamCriterion,
    ExamAttempt,
    ExamAttachment,
    CriterionScore,
    CertificationPath,
)

# --- User Management Administration ---


class ProfileInline(admin.StackedInline):
    """
    Inline admin configuration for user profiles.

    Allows editing user profile information directly within the user admin interface.
    Focuses on essential profile fields while maintaining clean presentation.
    """

    model = Profile
    can_delete = False
    verbose_name_plural = "Profile Information"
    fk_name = "user"
    fields = ("force_password_change",)

    def get_extra(
        self, request: HttpRequest, obj: Optional[User] = None, **kwargs
    ) -> int:
        """Return 0 extra forms since profile should exist or be created automatically."""
        return 0


class UserAdmin(BaseUserAdmin):
    """
    Enhanced user administration interface with profile integration.

    Extends Django's default UserAdmin to include profile information
    and provides advanced filtering and search capabilities for better
    user management in the E-Learning system.
    """

    inlines = (ProfileInline,)
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
        "get_force_password_change",
    )
    list_select_related = ("profile",)
    list_filter = (
        "is_staff",
        "is_superuser",
        "is_active",
        "groups",
        "profile__force_password_change",
        "date_joined",
    )
    search_fields = ("username", "first_name", "last_name", "email")
    ordering = ("username",)

    @admin.display(boolean=True, description=_("Force Password Change"))
    def get_force_password_change(self, instance: User) -> Optional[bool]:
        """
        Display force password change status for the user.

        Args:
            instance: User instance to check

        Returns:
            Boolean indicating if password change is forced, None if no profile exists
        """
        try:
            return instance.profile.force_password_change
        except Profile.DoesNotExist:
            return None

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Optimize queryset with profile prefetch for better performance."""
        return super().get_queryset(request).select_related("profile")


# Register enhanced user administration
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

# --- Learning Modules Administration ---


class ChapterInline(admin.TabularInline):
    """Inline admin for module chapter management."""

    model = Chapter
    extra = 1
    fields = ("title", "description", "order", "is_active")
    ordering = ("order",)


class ContentInline(admin.TabularInline):
    """Inline admin for chapter content management."""

    model = Content
    extra = 1
    fields = ("title", "video_url", "order")
    ordering = ("order",)


# class SupplementaryContentInline(admin.TabularInline):
#     """Inline admin for supplementary content management."""
#     model = SupplementaryContent
#     extra = 0
#     fields = ('title', 'content_type', 'order')
#     ordering = ('order',)


class TaskInline(admin.TabularInline):
    """Inline admin for chapter task management."""

    model = Task
    extra = 1
    fields = ("title", "difficulty", "order")
    ordering = ("order",)


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    """
    Administration interface for learning modules.

    Provides comprehensive module management including chapter editing,
    access control, and categorization features.
    """

    list_display = ("title", "category", "is_public", "chapter_count")
    list_filter = ("category", "is_public")
    search_fields = ("title", "description")
    prepopulated_fields = {"slug": ("title",)} if hasattr(Module, "slug") else {}
    inlines = [ChapterInline]

    fieldsets = (
        (_("Basic Information"), {"fields": ("title", "description", "category")}),
        (
            _("Access Control"),
            {
                "fields": ("is_public",),
                "description": _("Configure who can access this module"),
            },
        ),
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Optimize queryset for better performance."""
        return super().get_queryset(request).prefetch_related("chapters")


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    """Administration interface for learning chapters."""

    list_display = (
        "title",
        "module",
        "order",
        "is_active",
        "content_count",
        "task_count",
    )
    list_filter = ("module", "is_active", "order")
    search_fields = ("title", "description", "module__title")
    autocomplete_fields = ("module",)
    ordering = ("module", "order")
    inlines = [ContentInline, TaskInline]

    fieldsets = (
        (_("Chapter Information"), {"fields": ("title", "description", "module")}),
        (_("Configuration"), {"fields": ("order", "is_active")}),
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Optimize queryset with related object prefetch."""
        return (
            super()
            .get_queryset(request)
            .select_related("module")
            .prefetch_related("contents", "tasks")
        )


@admin.register(ModuleAccess)
class ModuleAccessAdmin(admin.ModelAdmin):
    """Administration interface for module access permissions."""

    list_display = ("user", "module", "granted_at")
    list_filter = ("module", "granted_at")
    search_fields = ("user__username", "user__email", "module__title")
    autocomplete_fields = ("user", "module")
    readonly_fields = ("granted_at",)

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Optimize queryset with related object prefetch."""
        return super().get_queryset(request).select_related("user", "module")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    """Administration interface for learning tasks."""

    list_display = ("title", "chapter", "difficulty", "order")
    list_filter = ("chapter", "difficulty")
    search_fields = ("title", "description", "chapter__title")
    autocomplete_fields = ("chapter",)
    ordering = ("chapter", "order")

    fieldsets = (
        (_("Task Information"), {"fields": ("title", "description", "chapter")}),
        (
            _("Configuration"),
            {
                "fields": ("difficulty", "order", "task_type")
                if hasattr(Task, "task_type")
                else ("difficulty", "order")
            },
        ),
        (
            _("Content"),
            {
                "fields": ("content", "solution")
                if hasattr(Task, "solution")
                else ("content",)
            },
        ),
    )


@admin.register(UserTaskProgress)
class UserTaskProgressAdmin(admin.ModelAdmin):
    """Administration interface for tracking user task progress."""

    list_display = ("user", "task", "completed", "completed_at")
    list_filter = ("completed", "task__chapter", "completed_at")
    search_fields = ("user__username", "task__title")
    autocomplete_fields = ("user", "task")
    readonly_fields = ("completed_at",)

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Optimize queryset with related object prefetch."""
        return (
            super()
            .get_queryset(request)
            .select_related("user", "task", "task__chapter")
        )


# --- Examination System Administration ---


class ExamCriterionInline(admin.TabularInline):
    """Inline admin for exam criteria management."""

    model = ExamCriterion
    extra = 1
    fields = ("title", "description", "max_points")


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    """
    Administration interface for examination management.

    Provides comprehensive exam creation and management including criteria definition,
    module prerequisites, and duration configuration.
    """

    list_display = (
        "title",
        "difficulty",
        "duration_weeks",
        "total_max_points",
        "created_at",
    )
    list_filter = ("difficulty", "created_at")
    search_fields = ("title", "description")
    filter_horizontal = ("modules",)
    inlines = [ExamCriterionInline]

    fieldsets = (
        (
            _("Basic Information"),
            {"fields": ("title", "description", "difficulty", "duration_weeks")},
        ),
        (
            _("Module Prerequisites"),
            {
                "fields": ("modules",),
                "description": _(
                    "Select modules that students must complete before taking this exam"
                ),
            },
        ),
        (
            _("Configuration"),
            {
                "fields": ("max_attempts", "passing_score")
                if hasattr(Exam, "max_attempts")
                else (),
                "classes": ("collapse",),
            },
        ),
    )

    readonly_fields = (
        ("created_at", "updated_at") if hasattr(Exam, "updated_at") else ("created_at",)
    )

    @admin.display(description=_("Total Points"))
    def total_max_points(self, obj: Exam) -> int:
        """Calculate and display total maximum points for the exam."""
        return sum(criterion.max_points for criterion in obj.examcriterion_set.all())

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Optimize queryset with related object prefetch."""
        return (
            super()
            .get_queryset(request)
            .prefetch_related("modules", "examcriterion_set")
        )


class CriterionScoreInline(admin.TabularInline):
    """Inline admin for criterion score management."""

    model = CriterionScore
    extra = 0
    fields = ("criterion", "achieved_points", "feedback")
    autocomplete_fields = ("criterion",)

    def get_extra(
        self, request: HttpRequest, obj: Optional[ExamAttempt] = None, **kwargs
    ) -> int:
        """Return number of extra forms based on exam criteria."""
        if obj and obj.exam:
            return max(
                0, obj.exam.examcriterion_set.count() - obj.criterionscore_set.count()
            )
        return 0


class ExamAttachmentInline(admin.TabularInline):
    """Inline admin for exam attachment management."""

    model = ExamAttachment
    extra = 1
    fields = (
        ("file", "uploaded_at", "file_size")
        if hasattr(ExamAttachment, "file_size")
        else ("file", "uploaded_at")
    )
    readonly_fields = (
        ("uploaded_at", "file_size")
        if hasattr(ExamAttachment, "file_size")
        else ("uploaded_at",)
    )


@admin.register(ExamAttempt)
class ExamAttemptAdmin(admin.ModelAdmin):
    """
    Administration interface for exam attempt management and grading.

    Provides comprehensive tracking of student exam attempts including
    timing, scoring, and grading workflow management.
    """

    list_display = (
        "user",
        "exam",
        "status",
        "started_at",
        "score",
        "processing_time_days",
    )
    list_filter = ("status", "exam", "started_at", "graded_by")
    search_fields = ("user__username", "user__email", "exam__title")
    readonly_fields = (
        "started_at",
        "submitted_at",
        "graded_at",
        "score",
        "processing_time_days",
        "due_date",
        "remaining_days",
    )
    autocomplete_fields = ("user", "exam", "graded_by")

    fieldsets = (
        (_("Attempt Information"), {"fields": ("user", "exam", "status")}),
        (
            _("Timestamps"),
            {
                "fields": (
                    "started_at",
                    "submitted_at",
                    "graded_at",
                    "processing_time_days",
                    "due_date",
                    "remaining_days",
                ),
                "classes": ("collapse",),
            },
        ),
        (_("Grading"), {"fields": ("score", "feedback", "graded_by")}),
    )

    inlines = [CriterionScoreInline, ExamAttachmentInline]

    def has_add_permission(self, request: HttpRequest) -> bool:
        """
        Prevent manual creation of exam attempts.

        Exam attempts should only be created through the API to ensure
        proper workflow and data integrity.
        """
        return False

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Optimize queryset with related object prefetch."""
        return (
            super()
            .get_queryset(request)
            .select_related("user", "exam", "graded_by")
            .prefetch_related("criterionscore_set", "examattachment_set")
        )


@admin.register(ExamCriterion)
class ExamCriterionAdmin(admin.ModelAdmin):
    """Administration interface for exam criteria management."""

    list_display = ("title", "exam", "max_points")
    list_filter = ("exam",)
    search_fields = ("title", "exam__title")
    autocomplete_fields = ("exam",)

    fieldsets = (
        (_("Criterion Information"), {"fields": ("title", "description", "exam")}),
        (_("Scoring"), {"fields": ("max_points", "order")}),
    )


@admin.register(CertificationPath)
class CertificationPathAdmin(admin.ModelAdmin):
    """Administration interface for certification path management."""

    list_display = ("title", "order", "exam_count")
    search_fields = ("title", "description")
    filter_horizontal = ("exams",)
    ordering = ("order",)

    fieldsets = (
        (_("Path Information"), {"fields": ("title", "description", "order")}),
        (
            _("Examinations"),
            {
                "fields": ("exams",),
                "description": _(
                    "Select exams that are part of this certification path"
                ),
            },
        ),
    )

    @admin.display(description=_("Number of Exams"))
    def exam_count(self, obj: CertificationPath) -> int:
        """Display the number of exams in this certification path."""
        return obj.exams.count()

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Optimize queryset with exam count prefetch."""
        return super().get_queryset(request).prefetch_related("exams")
