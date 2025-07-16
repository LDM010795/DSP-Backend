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
from django.db.models import Exists, OuterRef, QuerySet
from typing import Optional


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
        help_text=_("Unique name for this module category")
    )

    def __str__(self) -> str:
        """String representation of the category."""
        return self.name

    class Meta:
        verbose_name = _("Module Category")
        verbose_name_plural = _("Module Categories")
        ordering = ["name"]
        db_table = 'elearning_module_category'


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
        help_text=_("The unique title of the learning module")
    )
    
    category = models.ForeignKey(
        ModuleCategory,
        on_delete=models.PROTECT,
        related_name="modules",
        verbose_name=_("Category"),
        help_text=_("The category this module belongs to")
    )
    
    is_public = models.BooleanField(
        default=True,
        verbose_name=_("Public Access"),
        help_text=_(
            "If True, the module is accessible to all authenticated users. "
            "If False, access is restricted based on ModuleAccess entries."
        )
    )

    def __str__(self) -> str:
        """String representation of the module."""
        return self.title

    class Meta:
        verbose_name = _("Learning Module")
        verbose_name_plural = _("Learning Modules")
        ordering = ['category__name', 'title']
        db_table = 'elearning_module'

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
    def get_accessible_modules_for_user(user) -> QuerySet['Module']:
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
            models.Q(is_public=True) |
            models.Q(pk__in=ModuleAccess.objects.filter(user=user).values('module_id'))
        ).distinct()
    
    @property
    def content_count(self) -> int:
        """Get total number of content items in this module."""
        return self.contents.count()
    
    @property
    def task_count(self) -> int:
        """Get total number of tasks in this module."""
        return self.tasks.count()


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
        related_name='module_access_entries',
        verbose_name=_("User"),
        help_text=_("User granted access to the module")
    )
    
    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name='access_permissions',
        verbose_name=_("Module"),
        help_text=_("Module that user has been granted access to")
    )
    
    granted_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Granted At"),
        help_text=_("Timestamp when access was granted")
    )

    def __str__(self) -> str:
        """String representation of the access permission."""
        return f"Access for {self.user.username} to {self.module.title}"

    class Meta:
        verbose_name = _("Module Access Permission")
        verbose_name_plural = _("Module Access Permissions")
        unique_together = ('user', 'module')
        ordering = ['user', 'module']
        db_table = 'elearning_module_access'


class Content(models.Model):
    """
    Video and text content within learning modules.
    
    Content represents the primary learning materials within a module,
    typically including instructional videos, text descriptions, and
    supplementary information. Content items are ordered within modules.
    
    Attributes:
        module: Parent module
        video_url: Optional video content URL
        title: Content title
        description: Detailed content description
        supplementary_title: Optional additional title
        order: Display order within module
    """
    
    module = models.ForeignKey(
        Module,
        related_name='contents',
        on_delete=models.CASCADE,
        verbose_name=_("Module"),
        help_text=_("Module this content belongs to")
    )
    
    video_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name=_("Video URL"),
        help_text=_("Optional URL to video content (YouTube, Vimeo, etc.)")
    )
    
    title = models.CharField(
        max_length=255,
        verbose_name=_("Content Title"),
        help_text=_("Descriptive title for this content item")
    )
    
    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("Detailed description or text content")
    )
    
    supplementary_title = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name=_("Supplementary Title"),
        help_text=_("Optional additional title or subtitle")
    )
    
    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Display Order"),
        help_text=_("Order of content within the module (0 = first)")
    )

    def __str__(self) -> str:
        """String representation of the content."""
        return f"{self.module.title} - {self.title}"

    class Meta:
        verbose_name = _("Learning Content")
        verbose_name_plural = _("Learning Contents")
        unique_together = ('module', 'title')
        ordering = ['module', 'order', 'title']
        db_table = 'elearning_content'


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
        related_name='supplementary_contents',
        on_delete=models.CASCADE,
        verbose_name=_("Content"),
        help_text=_("Content item this supplementary material belongs to")
    )
    
    label = models.CharField(
        max_length=200,
        verbose_name=_("Link Label"),
        help_text=_("Descriptive label for the supplementary link")
    )
    
    url = models.URLField(
        max_length=500,
        verbose_name=_("Resource URL"),
        help_text=_("URL to the supplementary resource")
    )
    
    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Display Order"),
        help_text=_("Order of supplementary links within content")
    )

    def __str__(self) -> str:
        """String representation of the supplementary content."""
        return f"{self.content.title} - {self.label}"

    class Meta:
        verbose_name = _("Supplementary Content")
        verbose_name_plural = _("Supplementary Contents")
        ordering = ['content', 'order', 'label']
        db_table = 'elearning_supplementary_content'


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
        order: Display order within module
    """
    
    module = models.ForeignKey(
        Module,
        related_name='articles',
        on_delete=models.CASCADE,
        verbose_name=_("Module"),
        help_text=_("Module this article belongs to")
    )
    
    url = models.URLField(
        max_length=500,
        verbose_name=_("Article URL"),
        help_text=_("URL to the external article or resource")
    )
    
    title = models.CharField(
        max_length=255,
        verbose_name=_("Article Title"),
        help_text=_("Descriptive title for the article")
    )
    
    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Display Order"),
        help_text=_("Order of articles within the module")
    )

    def __str__(self) -> str:
        """String representation of the article."""
        return f"{self.module.title} - Article: {self.title}"

    class Meta:
        verbose_name = _("Article Reference")
        verbose_name_plural = _("Article References")
        unique_together = ('module', 'title')
        ordering = ['module', 'order', 'title']
        db_table = 'elearning_article'


class Task(models.Model):
    """
    Programming exercises with difficulty levels and testing integration.
    
    Tasks represent hands-on programming exercises that allow students
    to practice concepts learned in the module. They include automated
    testing capabilities and difficulty grading.
    
    Attributes:
        module: Parent module
        title: Task title
        description: Task instructions and requirements
        difficulty: Difficulty level (Easy/Medium/Hard)
        hint: Optional hint for students
        test_file_path: Path to automated test file
        order: Display order within module
        
    Testing Integration:
        The test_file_path points to a Python file containing unittest
        cases that can be executed against student submissions.
    """
    
    class Difficulty(models.TextChoices):
        """Task difficulty levels with German display names."""
        EASY = 'Einfach', _('Easy')
        MEDIUM = 'Mittel', _('Medium')
        HARD = 'Schwer', _('Hard')

    module = models.ForeignKey(
        Module,
        related_name='tasks',
        on_delete=models.CASCADE,
        verbose_name=_("Module"),
        help_text=_("Module this task belongs to")
    )
    
    title = models.CharField(
        max_length=255,
        verbose_name=_("Task Title"),
        help_text=_("Descriptive title for the programming task")
    )
    
    description = models.TextField(
        verbose_name=_("Task Description"),
        help_text=_("Detailed instructions and requirements for the task")
    )
    
    difficulty = models.CharField(
        max_length=10,
        choices=Difficulty.choices,
        default=Difficulty.MEDIUM,
        verbose_name=_("Difficulty Level"),
        help_text=_("Difficulty level for student guidance")
    )
    
    hint = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Hint"),
        help_text=_("Optional hint to help students solve the task")
    )
    
    test_file_path = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Test File Path"),
        help_text=_(
            "Relative path from the 'elearning' app directory to the python file "
            "containing unittest cases. E.g., 'task_tests/module1/task10_tests.py'"
        )
    )
    
    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Display Order"),
        help_text=_("Order of tasks within the module")
    )

    def __str__(self) -> str:
        """String representation of the task."""
        return f"{self.module.title} - Task: {self.title}"

    class Meta:
        verbose_name = _("Programming Task")
        verbose_name_plural = _("Programming Tasks")
        unique_together = ('module', 'title')
        ordering = ['module', 'order', 'title']
        db_table = 'elearning_task'
    
    @property
    def difficulty_display(self) -> str:
        """Get the display name for the difficulty level."""
        return self.get_difficulty_display()
    
    def has_automated_tests(self) -> bool:
        """Check if this task has automated tests configured."""
        return bool(self.test_file_path)


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
        related_name='task_progress',
        verbose_name=_("User"),
        help_text=_("User whose progress is being tracked")
    )
    
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='user_progress',
        verbose_name=_("Task"),
        help_text=_("Task being tracked")
    )
    
    completed = models.BooleanField(
        default=False,
        verbose_name=_("Completed"),
        help_text=_("Whether the user has completed this task")
    )
    
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Completed At"),
        help_text=_("Timestamp when the task was marked as completed")
    )

    def __str__(self) -> str:
        """String representation of the progress entry."""
        status = _("Completed") if self.completed else _("Not Completed")
        return f"{self.user.username} - {self.task.title} ({status})"

    class Meta:
        verbose_name = _("User Task Progress")
        verbose_name_plural = _("User Task Progress Entries")
        unique_together = ('user', 'task')
        ordering = ['user', 'task'] 
        db_table = 'elearning_user_task_progress'
        indexes = [
            models.Index(fields=['user', 'completed']),
            models.Index(fields=['task', 'completed']),
            models.Index(fields=['completed_at']),
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
        self.save(update_fields=['completed', 'completed_at']) 