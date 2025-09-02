"""
E-Learning Module System Models

This module defines the core models for the E-Learning module system,
providing a comprehensive framework for organizing learning content,
tasks, and user progress tracking.

Models:
- ModuleCategory: Organizational categories for modules
- Module: Core learning modules with access control
- ModuleAccess: User-specific module access permissions
- Content: Video and text content within modules
- SupplementaryContent: Additional resources and links
- Article: External article references
- Task: Programming exercises with difficulty levels
- UserTaskProgress: Individual user progress tracking

Features:
- Flexible module categorization system
- Public/private module access control
- Ordered content presentation
- Task difficulty grading
- Comprehensive user progress tracking
- Integration with testing framework

Author: DSP Development Team
Version: 1.0.0
"""

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.db.models import QuerySet
from django.core.exceptions import ValidationError
import re


def validate_cloud_url(value):
    """
    Custom validator for cloud storage URLs that may contain spaces.
    Accepts URLs with spaces in the path (common in cloud storage).
    """
    if not value:
        return

    # Basic URL pattern that allows spaces in the path
    url_pattern = r"^https?://[^\s]+(?:\s[^\s]*)*$"

    if not re.match(url_pattern, value):
        raise ValidationError(_("Enter a valid URL."))

    # Additional check: must start with http/https
    if not value.startswith(("http://", "https://")):
        raise ValidationError(_("Enter a valid URL."))


class ModuleCategory(models.Model):
    """
    Organizational categories for learning modules.

    This model provides a flexible categorization system that allows
    administrators to organize modules into logical groups such as
    "Python Basics", "Data Science", "Web Development", etc.

    Attributes:
        name: Unique category name

    Example:
        >>> category = ModuleCategory.objects.create(name="Python Fundamentals")
        >>> print(category.name)  # "Python Fundamentals"
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_("Category Name"),
        help_text=_("Unique name for this module category"),
    )

    def __str__(self) -> str:
        """String representation of the category."""
        return self.name

    class Meta:
        verbose_name = _("Module Category")
        verbose_name_plural = _("Module Categories")
        ordering = ["name"]
        db_table = "elearning_module_category"


class Module(models.Model):
    """
    Core learning module model with access control.

    Modules represent complete learning units that can contain multiple
    types of content (videos, articles, tasks). They support both public
    and private access models for flexible course management.

    Attributes:
        title: Unique module title
        category: Associated category for organization
        is_public: Public accessibility flag

    Access Control:
        - Public modules: Accessible to all authenticated users
        - Private modules: Require explicit ModuleAccess permissions

    Example:
        >>> module = Module.objects.create(
        ...     title="Introduction to Python",
        ...     category=category,
        ...     is_public=True
        ... )
        >>> module.check_user_accessibility(user)  # True for public modules
    """

    title = models.CharField(
        max_length=200,
        unique=True,
        verbose_name=_("Module Title"),
        help_text=_("The unique title of the learning module"),
    )

    category = models.ForeignKey(
        ModuleCategory,
        on_delete=models.PROTECT,
        related_name="modules",
        verbose_name=_("Category"),
        help_text=_("The category this module belongs to"),
    )

    is_public = models.BooleanField(
        default=True,
        verbose_name=_("Public Access"),
        help_text=_(
            "If True, the module is accessible to all authenticated users. "
            "If False, access is restricted based on ModuleAccess entries."
        ),
    )

    def __str__(self) -> str:
        """String representation of the module."""
        return self.title

    class Meta:
        verbose_name = _("Learning Module")
        verbose_name_plural = _("Learning Modules")
        ordering = ["category__name", "title"]
        db_table = "elearning_module"

    def check_user_accessibility(self, user) -> bool:
        """
        Check if a user has access to this module.

        Args:
            user: Django User instance to check

        Returns:
            True if user has access, False otherwise

        Logic:
            1. Unauthenticated users: Only public modules
            2. Public modules: Always accessible to authenticated users
            3. Private modules: Requires explicit ModuleAccess entry
        """
        if not user or not user.is_authenticated:
            return self.is_public

        if self.is_public:
            return True

        return ModuleAccess.objects.filter(module=self, user=user).exists()

    @staticmethod
    def get_accessible_modules_for_user(user) -> QuerySet["Module"]:
        """
        Get all modules accessible to a specific user.

        Args:
            user: Django User instance

        Returns:
            QuerySet of accessible Module instances

        Example:
            >>> accessible_modules = Module.get_accessible_modules_for_user(request.user)
            >>> for module in accessible_modules:
            ...     print(f"User can access: {module.title}")
        """
        if not user or not user.is_authenticated:
            return Module.objects.filter(is_public=True)

        return Module.objects.filter(
            models.Q(is_public=True)
            | models.Q(
                pk__in=ModuleAccess.objects.filter(user=user).values("module_id")
            )
        ).distinct()

    @property
    def content_count(self) -> int:
        """Get total number of content items across all chapters in this module."""
        return sum(chapter.contents.count() for chapter in self.chapters.all())

    @property
    def task_count(self) -> int:
        """Get total number of tasks across all chapters in this module."""
        return sum(chapter.tasks.count() for chapter in self.chapters.all())

    @property
    def chapter_count(self) -> int:
        """Get total number of chapters in this module."""
        return self.chapters.count()


class ModuleAccess(models.Model):
    """
    User-specific access permissions for private modules.

    This model manages fine-grained access control for private modules,
    allowing administrators to grant specific users access to restricted
    learning content.

    Attributes:
        user: User granted access
        module: Module being accessed
        granted_at: Timestamp of access grant

    Usage:
        Used automatically by Module.check_user_accessibility() and
        Module.get_accessible_modules_for_user() for access control.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="module_access_entries",
        verbose_name=_("User"),
        help_text=_("User granted access to the module"),
    )

    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name="access_permissions",
        verbose_name=_("Module"),
        help_text=_("Module that user has been granted access to"),
    )

    granted_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Granted At"),
        help_text=_("Timestamp when access was granted"),
    )

    def __str__(self) -> str:
        """String representation of the access permission."""
        return f"Access for {self.user.username} to {self.module.title}"

    class Meta:
        verbose_name = _("Module Access Permission")
        verbose_name_plural = _("Module Access Permissions")
        unique_together = ("user", "module")
        ordering = ["user", "module"]
        db_table = "elearning_module_access"


class Chapter(models.Model):
    """
    Kapitel innerhalb von Lernmodulen.

    Chapters ermöglichen eine strukturierte Organisation von Lerninhalten
    innerhalb von Modulen. Sie können Videos, Text-Content und andere
    Lernmaterialien enthalten.

    Attributes:
        module: Parent module
        title: Chapter title
        description: Detailed chapter description
        order: Display order within module
        is_active: Whether the chapter is active and visible
    """

    module = models.ForeignKey(
        Module,
        related_name="chapters",
        on_delete=models.CASCADE,
        verbose_name=_("Module"),
        help_text=_("Module this chapter belongs to"),
    )

    title = models.CharField(
        max_length=255,
        verbose_name=_("Chapter Title"),
        help_text=_("Descriptive title for this chapter"),
    )

    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("Detailed description of the chapter content"),
    )

    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Display Order"),
        help_text=_("Order of chapters within the module (0 = first)"),
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Active"),
        help_text=_("Whether this chapter is active and visible to users"),
    )

    def __str__(self) -> str:
        """String representation of the chapter."""
        return f"{self.module.title} - {self.title}"

    class Meta:
        verbose_name = _("Chapter")
        verbose_name_plural = _("Chapters")
        unique_together = ("module", "title")
        ordering = ["module", "order", "title"]
        db_table = "elearning_chapter"

    @property
    def content_count(self) -> int:
        """Get total number of content items in this chapter."""
        return self.contents.count()

    @property
    def task_count(self) -> int:
        """Get total number of tasks in this chapter."""
        return self.tasks.count()


class Content(models.Model):
    """
    Video and text content within learning chapters.

    Content represents the primary learning materials within a chapter,
    typically including instructional videos, text descriptions, and
    supplementary information. Content items are ordered within chapters.

    Attributes:
        chapter: Parent chapter
        video_url: Optional video content URL
        title: Content title
        description: Detailed content description
        supplementary_title: Optional additional title
        order: Display order within chapter
    """

    chapter = models.ForeignKey(
        Chapter,
        related_name="contents",
        on_delete=models.CASCADE,
        verbose_name=_("Chapter"),
        help_text=_("Chapter this content belongs to"),
        null=True,
        blank=True,
    )

    video_url = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name=_("Video URL"),
        help_text=_("Optional URL to video content (YouTube, Vimeo, etc.)"),
        validators=[validate_cloud_url],
    )

    title = models.CharField(
        max_length=255,
        verbose_name=_("Content Title"),
        help_text=_("Descriptive title for this content item"),
    )

    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("Detailed description or text content"),
    )

    supplementary_title = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name=_("Supplementary Title"),
        help_text=_("Optional additional title or subtitle"),
    )

    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Display Order"),
        help_text=_("Order of content within the chapter (0 = first)"),
    )

    def __str__(self) -> str:
        """String representation of the content."""
        return f"{self.chapter.title} - {self.title}"

    class Meta:
        verbose_name = _("Learning Content")
        verbose_name_plural = _("Learning Contents")
        unique_together = ("chapter", "title")
        ordering = ["chapter", "order", "title"]
        db_table = "elearning_content"


class SupplementaryContent(models.Model):
    """
    Additional resources and links for learning content.

    This model provides a way to attach supplementary materials,
    external resources, documentation links, and additional reading
    materials to specific content items.

    Attributes:
        content: Parent content item
        label: Descriptive label for the link
        url: URL to the resource
        order: Display order within content
    """

    content = models.ForeignKey(
        Content,
        related_name="supplementary_contents",
        on_delete=models.CASCADE,
        verbose_name=_("Content"),
        help_text=_("Content item this supplementary material belongs to"),
    )

    label = models.CharField(
        max_length=200,
        verbose_name=_("Link Label"),
        help_text=_("Descriptive label for the supplementary link"),
    )

    url = models.CharField(
        max_length=500,
        verbose_name=_("Resource URL"),
        help_text=_("URL to the supplementary resource"),
        validators=[validate_cloud_url],
    )

    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Display Order"),
        help_text=_("Order of supplementary links within content"),
    )

    def __str__(self) -> str:
        """String representation of the supplementary content."""
        return f"{self.content.title} - {self.label}"

    class Meta:
        verbose_name = _("Supplementary Content")
        verbose_name_plural = _("Supplementary Contents")
        ordering = ["content", "order", "label"]
        db_table = "elearning_supplementary_content"


class Article(models.Model):
    """
    External article references for modules.

    Articles represent links to external reading materials, blog posts,
    documentation, or other text-based resources that complement the
    module's learning objectives.

    Attributes:
        module: Parent module
        url: URL to the external article
        title: Article title
        json_content: Optional extracted JSON content from source
        order: Display order within module
    """

    module = models.ForeignKey(
        "Module",
        related_name="articles",
        on_delete=models.CASCADE,
        verbose_name=_("Module"),
        help_text=_("Module this article belongs to."),
    )

    url = models.CharField(
        max_length=500,
        verbose_name=_("Article URL"),
        help_text=_("URL to the external article or resource."),
        validators=[validate_cloud_url],
    )

    title = models.CharField(
        max_length=255,
        verbose_name=_("Article Title"),
        help_text=_("Descriptive title for the article."),
    )

    json_content = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_("Extracted JSON"),
        help_text=_("Optional extracted content in JSON format."),
    )

    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Display Order"),
        help_text=_("Order of articles within the module."),
    )

    def __str__(self) -> str:
        """String representation of the article."""
        return f"{self.module.title} - Article: {self.title}"

    class Meta:
        verbose_name = _("Article Reference")
        verbose_name_plural = _("Article References")
        unique_together = ("module", "title")
        ordering = ["module", "order", "title"]
        db_table = "elearning_article"


class ArticleImage(models.Model):
    """
    Bildverwaltung für Artikel in Lernmodulen.

    Speichert Cloud-URLs und Metadaten für Bilder, die in Artikeln vorkommen.
    Ermöglicht automatische Zuordnung durch Frontend basierend auf Bildnamen.
    """

    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name="article_images",
        verbose_name=_("Module"),
        help_text=_("Modul, zu dem dieses Bild gehört"),
    )

    image_name = models.CharField(
        max_length=255,
        unique=True,
        verbose_name=_("Image Name"),
        help_text=_("Eindeutiger Name für automatische Frontend-Zuordnung"),
    )

    cloud_url = models.CharField(
        max_length=1000,
        verbose_name=_("Cloud URL"),
        help_text=_("Vollständige Cloud-URL des Bildes"),
        validators=[validate_cloud_url],
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Article Image")
        verbose_name_plural = _("Article Images")
        ordering = ["module", "image_name"]
        db_table = "elearning_article_image"
        indexes = [
            models.Index(fields=["module"]),
            models.Index(fields=["image_name"]),
        ]

    def __str__(self) -> str:
        """String representation of the article image."""
        return f"{self.module.title} - {self.image_name}"


class Task(models.Model):
    """
    Programming exercises with difficulty levels and testing integration.

    Tasks represent hands-on programming exercises that allow students
    to practice concepts learned in the chapter. They include automated
    testing capabilities and difficulty grading.

    Attributes:
        chapter: Parent chapter
        title: Task title
        description: Task instructions and requirements
        difficulty: Difficulty level (Easy/Medium/Hard)
        hint: Optional hint for students
        test_file_path: Path to automated test file
        order: Display order within chapter

    Testing Integration:
        The test_file_path points to a Python file containing unittest
        cases that can be executed against student submissions.
    """

    class TaskType(models.TextChoices):
        """
        Please add task types here.
        """

        NONE = "none", _("None")
        PROGRAMMING = "programming", _("Programming Exercise")
        MULTIPLE_CHOICE = "multiple_choice", _("Multiple Choice")

    class Difficulty(models.TextChoices):
        """Task difficulty levels with German display names."""

        EASY = "Einfach", _("Easy")
        MEDIUM = "Mittel", _("Medium")
        HARD = "Schwer", _("Hard")

    chapter = models.ForeignKey(
        Chapter,
        related_name="tasks",
        on_delete=models.CASCADE,
        verbose_name=_("Chapter"),
        help_text=_("Chapter this task belongs to"),
        null=True,
        blank=True,
    )

    title = models.CharField(
        max_length=255,
        verbose_name=_("Task Title"),
        help_text=_("Descriptive title for the programming task"),
    )

    description = models.TextField(
        verbose_name=_("Task Description"),
        help_text=_("To describe how to use the task type element"),
    )

    difficulty = models.CharField(
        max_length=10,
        choices=Difficulty.choices,
        default=Difficulty.MEDIUM,
        verbose_name=_("Difficulty Level"),
        help_text=_("Difficulty level for student guidance"),
    )

    hint = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Hint"),
        help_text=_("Optional hint to help students solve the task"),
    )

    task_type = models.CharField(
        max_length=50,
        choices=TaskType.choices,
        default=TaskType.NONE,
        verbose_name=_("Task Type"),
        help_text=_("Type of task"),
    )

    task_config = models.JSONField(
        blank=True,
        null=True,
        verbose_name=_("Task Configuration"),
        help_text=_(
            "JSON configuration for task-specific settings. "
            "For multiple choice: options, correct_answer, explanation. "
            "For programming: test configuration."
        ),
    )

    test_file_path = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Test File Path"),
        help_text=_(
            "Relative path from the 'elearning' app directory to the python file "
            "containing unittest cases. E.g., 'task_tests/module1/task10_tests.py'"
        ),
    )

    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Display Order"),
        help_text=_("Order of tasks within the module"),
    )

    def __str__(self) -> str:
        """String representation of the task."""
        return f"{self.chapter.title} - Task: {self.title}"

    class Meta:
        verbose_name = _("Programming Task")
        verbose_name_plural = _("Programming Tasks")
        unique_together = ("chapter", "title")
        ordering = ["chapter", "order", "title"]
        db_table = "elearning_task"

    @property
    def difficulty_display(self) -> str:
        """Get the display name for the difficulty level."""
        return self.get_difficulty_display()

    def has_automated_tests(self) -> bool:
        """Check if this task has automated tests configured."""
        return bool(self.test_file_path)

    def clean(self):
        """Validate task_config based on task_type."""
        # Ensures valid JSON structure for each task type
        super().clean()

        if self.task_config and self.task_type == self.TaskType.MULTIPLE_CHOICE:
            # Prüfe required fields
            required_fields = ["options", "correct_answer"]
            for field in required_fields:
                if field not in self.task_config:
                    raise ValidationError(
                        f"Multiple choice tasks require '{field}' in task_config"
                    )

            # Prüfe options ist eine Liste
            if not isinstance(self.task_config.get("options"), list):
                raise ValidationError("Options must be a list")

            # Prüfe correct_answer ist ein gültiger Index
            correct_answer = self.task_config.get("correct_answer")
            options = self.task_config.get("options", [])

            if not isinstance(correct_answer, int):
                raise ValidationError("correct_answer must be an integer (index)")

            if correct_answer < 0 or correct_answer >= len(options):
                raise ValidationError(
                    f"correct_answer index {correct_answer} is out of range (0-{len(options) - 1})"
                )

    """
    Create new Task_Type Formats here
    Region for defining configuration retrieval methods for different task types.
    Add new 'get_<task_type>_config' methods here.
    """

    def get_multiple_choice_config(self):
        """Get validated multiple choice configuration."""
        # Returns: {'options': [...], 'correct_answer': 0, 'explanation': '...'}
        if self.task_type != self.TaskType.MULTIPLE_CHOICE:
            return None

        if not self.task_config:
            return None

        """
        This is the format for the multiple choice task.
        """
        return {
            "options": self.task_config.get("options", []),
            "correct_answer": self.task_config.get("correct_answer"),
            "explanation": self.task_config.get("explanation", ""),
        }


class UserTaskProgress(models.Model):
    """
    Individual user progress tracking for tasks.

    This model tracks each user's progress through programming tasks,
    recording completion status and timestamps for learning analytics
    and progress reporting.

    Attributes:
        user: User whose progress is being tracked
        task: Task being tracked
        completed: Completion status
        completed_at: Timestamp of completion

    Analytics:
        This model enables comprehensive learning analytics including:
        - Individual progress tracking
        - Module completion rates
        - Time-to-completion analysis
        - Difficulty-based performance metrics
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="task_progress",
        verbose_name=_("User"),
        help_text=_("User whose progress is being tracked"),
    )

    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="user_progress",
        verbose_name=_("Task"),
        help_text=_("Task being tracked"),
    )

    completed = models.BooleanField(
        default=False,
        verbose_name=_("Completed"),
        help_text=_("Whether the user has completed this task"),
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Completed At"),
        help_text=_("Timestamp when the task was marked as completed"),
    )

    def __str__(self) -> str:
        """String representation of the progress entry."""
        status = _("Completed") if self.completed else _("Not Completed")
        return f"{self.user.username} - {self.task.title} ({status})"

    class Meta:
        verbose_name = _("User Task Progress")
        verbose_name_plural = _("User Task Progress Entries")
        unique_together = ("user", "task")
        ordering = ["user", "task"]
        db_table = "elearning_user_task_progress"
        indexes = [
            models.Index(fields=["user", "completed"]),
            models.Index(fields=["task", "completed"]),
            models.Index(fields=["completed_at"]),
        ]

    def mark_completed(self) -> None:
        """
        Mark this task as completed and set the completion timestamp.

        This method should be called when a user successfully completes
        a task to ensure proper progress tracking.
        """
        from django.utils import timezone

        self.completed = True
        self.completed_at = timezone.now()
        self.save(update_fields=["completed", "completed_at"])
