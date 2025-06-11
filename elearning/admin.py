from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

# Importiere alle Modelle aus der zentralen models.py der elearning App
from .models import (
    Profile,
    Module, ModuleAccess, Content, SupplementaryContent, Task, UserTaskProgress,
    Exam, ExamCriterion, ExamAttempt, ExamAttachment, CriterionScore, CertificationPath
)

# --- USER & PROFILE ADMIN (aus der alten users App) ---

# Inline Admin für das Profil
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profil'
    fk_name = 'user'
    fields = ('force_password_change',)

# Erweiterte UserAdmin-Klasse
class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'get_force_password_change')
    list_select_related = ('profile',)
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups', 'profile__force_password_change')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('username',)

    @admin.display(boolean=True, description=_('Passwortänderung erzwingen'))
    def get_force_password_change(self, instance):
        try:
            return instance.profile.force_password_change
        except Profile.DoesNotExist:
            return None

# Registriere die erweiterte User-Ansicht
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

# --- MODULES ADMIN (neu hinzugefügt) ---

class ContentInline(admin.TabularInline):
    model = Content
    extra = 1

class TaskInline(admin.TabularInline):
    model = Task
    extra = 1

@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'is_public')
    list_filter = ('category', 'is_public')
    search_fields = ('title',)
    inlines = [ContentInline, TaskInline]

@admin.register(ModuleAccess)
class ModuleAccessAdmin(admin.ModelAdmin):
    list_display = ('user', 'module', 'granted_at')
    list_filter = ('module',)
    search_fields = ('user__username', 'module__title')
    autocomplete_fields = ('user', 'module')

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'module', 'difficulty')
    list_filter = ('module', 'difficulty')
    search_fields = ('title', 'description', 'module__title')
    autocomplete_fields = ('module',)

# --- FINAL_EXAM ADMIN (aus der alten final_exam App) ---

class ExamCriterionInline(admin.TabularInline):
    model = ExamCriterion
    extra = 1
    fields = ('title', 'description', 'max_points')

@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('title', 'difficulty', 'duration_weeks', 'created_at')
    list_filter = ('difficulty', 'created_at')
    search_fields = ('title', 'description')
    filter_horizontal = ('modules',)
    autocomplete_fields = ('modules',) # Besser für viele Module als filter_horizontal
    fieldsets = (
        (_('Grundinformationen'), {
            'fields': ('title', 'description', 'difficulty', 'duration_weeks')
        }),
        (_('Module-Voraussetzungen'), {
            'fields': ('modules',),
        }),
    )
    inlines = [ExamCriterionInline]

class CriterionScoreInline(admin.TabularInline):
    model = CriterionScore
    extra = 1
    fields = ('criterion', 'achieved_points')
    autocomplete_fields = ('criterion',)

class ExamAttachmentInline(admin.TabularInline):
    model = ExamAttachment
    extra = 1
    fields = ('file', 'uploaded_at')
    readonly_fields = ('uploaded_at',)

@admin.register(ExamAttempt)
class ExamAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'exam', 'status', 'started_at', 'score')
    list_filter = ('status', 'exam')
    search_fields = ('user__username', 'exam__title')
    readonly_fields = ('started_at', 'submitted_at', 'graded_at', 'score', 'processing_time_days', 'due_date', 'remaining_days')
    autocomplete_fields = ('user', 'exam', 'graded_by')
    fieldsets = (
        (_('Versuch-Information'), {'fields': ('user', 'exam', 'status')}),
        (_('Zeitstempel'), {'fields': ('started_at', 'submitted_at', 'graded_at', 'processing_time_days', 'due_date', 'remaining_days'), 'classes': ('collapse',)}),
        (_('Bewertung'), {'fields': ('score', 'feedback', 'graded_by')}),
    )
    inlines = [CriterionScoreInline, ExamAttachmentInline]

    def has_add_permission(self, request):
        return False # Versuche sollen nur via API erstellt werden

@admin.register(ExamCriterion)
class ExamCriterionAdmin(admin.ModelAdmin):
    list_display = ('title', 'exam', 'max_points')
    list_filter = ('exam',)
    search_fields = ('title', 'exam__title')
    autocomplete_fields = ('exam',)

@admin.register(CertificationPath)
class CertificationPathAdmin(admin.ModelAdmin):
    list_display = ('title', 'order')
    search_fields = ('title', 'description')
    filter_horizontal = ('exams',)
