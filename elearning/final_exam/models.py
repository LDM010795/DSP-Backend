from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
import datetime

# Angepasster, sauberer Import innerhalb der 'elearning' App
from ..modules.models import Module, Task, UserTaskProgress

User = settings.AUTH_USER_MODEL

class ExamDifficulty(models.TextChoices):
    EASY = "easy", _("Einfach")
    MEDIUM = "medium", _("Mittel")
    HARD = "hard", _("Schwer")

class Exam(models.Model):
    title = models.CharField(max_length=255, unique=True)
    duration_weeks = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)],
        help_text=_("Bearbeitungszeit ab Start in vollen Wochen."),
    )
    difficulty = models.CharField(
        max_length=10, choices=ExamDifficulty.choices, default=ExamDifficulty.MEDIUM
    )
    description = models.TextField()
    modules = models.ManyToManyField(
        Module,
        blank=True,
        related_name="exams",
        help_text=_(
            "Module, die vor Start dieser Prüfung absolviert sein müssen (optional)."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Exam")
        verbose_name_plural = _("Exams")
        ordering = ["title"]

    def __str__(self):
        return self.title

    def is_available_for(self, user) -> bool:
        if not user or not user.is_authenticated:
            return False

        has_started_attempt = ExamAttempt.objects.filter(
            exam=self,
            user=user,
            status=ExamAttempt.Status.STARTED,
        ).exists()
        if has_started_attempt:
            return False

        required_modules = self.modules.all()
        if not required_modules.exists():
            return True

        for module in required_modules.prefetch_related('tasks'):
            all_task_ids_for_module = set(module.tasks.values_list('id', flat=True))
            if not all_task_ids_for_module:
                continue

            completed_task_ids_for_module = set(
                UserTaskProgress.objects.filter(
                    user=user,
                    task_id__in=all_task_ids_for_module,
                    completed=True
                ).values_list('task_id', flat=True)
            )

            if not all_task_ids_for_module.issubset(completed_task_ids_for_module):
                return False

        return True

# ... (Rest der Datei bleibt identisch, hier gekürzt zur Übersicht)

class ExamAttempt(models.Model):
    class Status(models.TextChoices):
        STARTED = "started", _("Gestartet")
        SUBMITTED = "submitted", _("Abgegeben")
        GRADED = "graded", _("Bewertet")

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="attempts")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="exam_attempts")
    status = models.CharField(
        max_length=15, choices=Status.choices, default=Status.STARTED
    )
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    graded_at = models.DateTimeField(null=True, blank=True)
    score = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Gesamtpunktzahl. Wird automatisch berechnet."),
    )
    feedback = models.TextField(blank=True, null=True)
    graded_by = models.ForeignKey(
        User,
        related_name="graded_exam_attempts",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    @property
    def due_date(self):
        if self.started_at and self.exam and self.exam.duration_weeks:
            return self.started_at + datetime.timedelta(weeks=self.exam.duration_weeks)
        return None

    @property
    def remaining_days(self):
        due = self.due_date
        if due:
            return (due - timezone.now()).days
        return None
    
    @property
    def processing_time_days(self):
        if self.started_at and self.submitted_at:
            return (self.submitted_at - self.started_at).days
        return None

    def _calculate_total_score(self) -> float:
        total = sum(cs.achieved_points for cs in self.criterion_scores.all() if cs.achieved_points is not None)
        return round(total, 2)

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        original_status = None
        if not is_new:
            try:
                original_status = ExamAttempt.objects.get(pk=self.pk).status
            except ExamAttempt.DoesNotExist:
                pass
        
        if self.status == self.Status.SUBMITTED and original_status != self.Status.SUBMITTED:
            self.submitted_at = timezone.now()
        elif self.status == self.Status.GRADED and original_status != self.Status.GRADED:
            self.graded_at = timezone.now()
            self.score = self._calculate_total_score()
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Attempt for {self.exam.title} by {self.user.username}"


class ExamRequirement(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="requirements")
    description = models.TextField(help_text=_("Beschreibung der Anforderung."))
    order = models.PositiveSmallIntegerField(default=0)
    
    class Meta:
        verbose_name = _("Exam Requirement")
        verbose_name_plural = _("Exam Requirements")
        ordering = ["exam", "order"]

    def __str__(self):
        return f"Requirement for {self.exam.title}: {self.description[:30]}..."


class ExamAttachment(models.Model):
    attempt = models.ForeignKey(
        ExamAttempt, on_delete=models.CASCADE, related_name="attachments"
    )
    file = models.FileField(upload_to="exam_uploads/%Y/%m/%d")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Exam Attachment")
        verbose_name_plural = _("Exam Attachments")
        ordering = ["uploaded_at"]

    def __str__(self):
        return f"Attachment for attempt {self.attempt.id}"


class ExamCriterion(models.Model):
    exam = models.ForeignKey(
        Exam, on_delete=models.CASCADE, related_name="criteria"
    )
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    max_points = models.PositiveIntegerField(
        help_text=_("Maximale Punktzahl für dieses Kriterium.")
    )

    class Meta:
        verbose_name = _("Exam Criterion")
        verbose_name_plural = _("Exam Criteria")
        unique_together = ("exam", "title")
        ordering = ["exam", "title"]

    def __str__(self):
        return f"{self.title} ({self.max_points} Pts)"


class CriterionScore(models.Model):
    attempt = models.ForeignKey(
        ExamAttempt, on_delete=models.CASCADE, related_name="criterion_scores"
    )
    criterion = models.ForeignKey(
        ExamCriterion, on_delete=models.CASCADE, related_name="scores"
    )
    achieved_points = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text=_("Erreichte Punkte für dieses Kriterium.")
    )

    class Meta:
        verbose_name = _("Criterion Score")
        verbose_name_plural = _("Criterion Scores")
        unique_together = ("attempt", "criterion")
        ordering = ["attempt", "criterion"]

    def __str__(self):
        return f"{self.criterion.title} for {self.attempt.user.username}: {self.achieved_points}/{self.criterion.max_points}"

    def clean(self):
        if self.achieved_points is not None and self.criterion.max_points is not None:
            if self.achieved_points > self.criterion.max_points:
                raise ValidationError(
                    _("Achieved points cannot exceed the criterion's max points.")
                )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
        if self.attempt.status == ExamAttempt.Status.GRADED:
            self.attempt.score = self.attempt._calculate_total_score()
            self.attempt.save(update_fields=['score'])


class CertificationPath(models.Model):
    title = models.CharField(
        max_length=200,
        unique=True,
        help_text=_("Titel des Zertifikatspfads")
    )
    description = models.TextField(
        blank=True,
        help_text=_("Kurze Beschreibung, was dieser Pfad abdeckt.")
    )
    exams = models.ManyToManyField(
        Exam,
        related_name="certification_paths",
        blank=True,
        help_text=_("Die Abschlussprüfungen, die Teil dieses Pfades sind.")
    )
    order = models.PositiveSmallIntegerField(
        default=0,
        db_index=True,
        help_text=_("Reihenfolge für die Anzeige (kleinere Zahlen zuerst).")
    )
    icon_name = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text=_("Name des Icons für das Frontend (z.B. IoCodeSlashOutline).")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Certification Path")
        verbose_name_plural = _("Certification Paths")
        ordering = ["order", "title"]

    def __str__(self):
        return self.title 