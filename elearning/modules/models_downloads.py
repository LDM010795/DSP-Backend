from django.db import models
from django.utils import timezone
from .models import Module, Article
from django.core.exceptions import ValidationError

class ResourceType(models.TextChoices):
    PDF = "pdf", "PDF"
    NOTEBOOK = "ipynb", "Jupyter Notebook"
    CODE = "code", "Code File"
    SLIDES = "slides", "Slides"
    IMAGE = "image", "Image"
    OTHER = "other", "Other"

class DownloadableResource(models.Model):
    # What the user sees
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")

    # Optional association (we can attach to a module or a specific article)
    module = models.ForeignKey(
        Module, on_delete=models.CASCADE, related_name="resources", null=True, blank=True
    )
    article = models.ForeignKey(
        Article, on_delete=models.CASCADE, related_name="resources", null=True, blank=True
    )

    # Classification for filtering/UX
    resource_type = models.CharField(
        max_length=16,
        choices=ResourceType.choices,
        default=ResourceType.OTHER,
    )

    # Storage metadata
    # We DO NOT store files; we store WHERE they live in Wasabi:
    # - cloud_key: S3 object key (authoritative locator)
    # - cloud_url: optional human/preview URL (not authoritative)
    cloud_key = models.CharField(
        max_length=1024,
        help_text="S3/Wsabi object key,  e.g. Lerninhalte/SQL/Notebooks/intro.ipynb",
    )
    cloud_url = models.URLField(
        max_length=2048,
        blank=True,
        default="",
        help_text="Optional URL for previewing or accessing the resource directly.",
    )

    # Optional technical metadata (for UI)
    content_type = models.CharField(max_length=128, blank=True, default="")
    size_bytes = models.BigIntegerField(null=True, blank=True)
    checksum = models.CharField(max_length=128, blank=True, help_text="Optional ETag/MD5/SHA1 for integrity")

    # Visibility and auditing
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Downloadable Resource"
        verbose_name_plural = "Downloadable Resources"
        indexes = [
            models.Index(fields=["module", "resource_type"]),
            models.Index(fields=["article"]),
            models.Index(fields=["cloud_key"]),
        ]

    def __str__(self):
        scope = self.article.title if self.article_id else (self.module.title if self.module_id else "Global")
        return f"{self.title} ({self.resource_type}) — {scope}"

    def clean(self):
        # Ensure at least one scope (module or article) is set, but allow either
        if not self.module_id and not self.article_id:
            raise ValidationError("Please set either 'module' or 'article' to scope the resource.")

        # Prefer cloud_key as the source of truth; cloud_url is purely informational
        if not self.cloud_key:
            raise ValidationError("cloud_key is required (S3/Wasabi object key).")