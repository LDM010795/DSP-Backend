from rest_framework import serializers
from .models import (
    Exam,
    ExamAttempt,
    ExamCriterion,
    CriterionScore,
    ExamAttachment,
    ExamRequirement,
    CertificationPath,
)
from django.db.models import Sum
from django.contrib.auth import get_user_model  # User importieren

User = get_user_model()

# Import Module model from the other app
try:
    from ..modules.models import Module
except ImportError:
    Module = None  # Fallback if module app is not available

# --- Base Serializers ---


class ModuleSerializer(serializers.ModelSerializer):
    class Meta:
        # Verwende das importierte Modul-Modell
        model = Module
        fields = ["id", "title"]  # Nur ID und Titel benötigt
        read_only_fields = fields  # Machen wir es read-only


class ExamRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamRequirement
        fields = ["id", "description", "order"]


class ExamCriterionSerializer(serializers.ModelSerializer):
    """Serializer für Bewertungskriterien mit Maximalpunktzahl."""

    class Meta:
        model = ExamCriterion
        # Ersetzt 'weight' durch 'max_points'
        fields = ["id", "title", "description", "max_points"]


class CriterionScoreSerializer(serializers.ModelSerializer):
    """Serializer für die erreichte Punktzahl pro Kriterium."""

    criterion = ExamCriterionSerializer(read_only=True)
    # `weighted_points` entfernt, `score` durch `achieved_points` ersetzt

    class Meta:
        model = CriterionScore
        fields = ["criterion", "achieved_points"]


class ExamAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamAttachment
        fields = ["id", "file", "uploaded_at"]


class UserSerializer(serializers.ModelSerializer):
    """Einfacher Serializer für Benutzerdetails."""

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email"]


class ExamSerializer(serializers.ModelSerializer):
    """Serializer für die grundlegenden Prüfungsdetails."""

    exam_title = serializers.CharField(source="title")
    exam_duration_week = serializers.IntegerField(source="duration_weeks")
    exam_difficulty = serializers.CharField(source="difficulty")
    exam_description = serializers.CharField(source="description")
    # Verwendet den aktualisierten ExamCriterionSerializer
    criteria = ExamCriterionSerializer(many=True, read_only=True)
    # NEU: Module hinzufügen (Voraussetzungen)
    modules = ModuleSerializer(many=True, read_only=True)
    # NEU: Anforderungen hinzufügen
    requirements = ExamRequirementSerializer(many=True, read_only=True)
    # Berechnete Gesamtpunktzahl der Prüfung hinzufügen
    total_max_points = serializers.SerializerMethodField()

    class Meta:
        model = Exam
        fields = [
            "id",
            "exam_title",
            "exam_duration_week",
            "exam_difficulty",
            "exam_description",
            "criteria",
            "requirements",
            "modules",
            "total_max_points",
        ]

    def get_total_max_points(self, obj):
        """Berechnet die Summe der max_points aller Kriterien dieser Prüfung."""
        # Aggregiert direkt über die RelatedManager
        return obj.criteria.aggregate(total=Sum("max_points"))["total"] or 0


# --- NEU: Vereinfachter Exam Serializer für Pfade ---


class SimpleExamSerializer(serializers.ModelSerializer):
    """Zeigt nur grundlegende Infos einer Prüfung an, für die Verwendung in Listen."""

    exam_title = serializers.CharField(source="title")
    exam_difficulty = serializers.CharField(source="difficulty")

    class Meta:
        model = Exam
        fields = [
            "id",
            "exam_title",
            "exam_difficulty",
        ]
        read_only_fields = fields


# --- NEU: Certification Path Serializer ---


class CertificationPathSerializer(serializers.ModelSerializer):
    """Serializer für Zertifikatspfade, inklusive der zugehörigen Prüfungen."""

    # Verschachtelter Serializer für die Prüfungen
    exams = SimpleExamSerializer(many=True, read_only=True)
    # Optional: icon_name direkt verwenden oder ggf. umbenennen
    icon = serializers.CharField(source="icon_name", read_only=True)

    class Meta:
        model = CertificationPath
        fields = [
            "id",
            "title",
            "description",
            "icon",  # Renamed from icon_name for potential frontend consistency
            "order",
            "exams",  # Liste der Prüfungen
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]  # Annahme: Pfade werden im Admin erstellt/bearbeitet


# --- Serializers for User Views ---


class BaseExamAttemptSerializer(serializers.ModelSerializer):
    """Basis-Serializer für Exam Attempts mit berechneten Feldern."""

    # Fügt die berechneten Properties hinzu
    due_date = serializers.DateTimeField(read_only=True)
    remaining_days = serializers.IntegerField(read_only=True)
    processing_time_days = serializers.IntegerField(read_only=True)

    # Fügt verschachtelte Serializer hinzu
    criterion_scores = CriterionScoreSerializer(many=True, read_only=True)
    attachments = ExamAttachmentSerializer(many=True, read_only=True)
    # Zeigt grundlegende Exam-Infos direkt an
    exam = ExamSerializer(read_only=True)
    # Optional: Zeigt User-Infos an (könnte in spezialisierten Serializern überschrieben werden)
    # user = UserSerializer(read_only=True)

    class Meta:
        model = ExamAttempt
        fields = [
            "id",
            "exam",  # Enthält jetzt ExamSerializer-Daten
            # "user", # Explizit in spezialisierten Serializern oder weglassen für 'my-exams'
            "status",
            "started_at",
            "submitted_at",
            "graded_at",
            "score",  # Summe der erreichten Punkte
            "feedback",
            "criterion_scores",  # Liste mit {criterion, achieved_points}
            "attachments",
            # Berechnete Felder
            "due_date",
            "remaining_days",
            "processing_time_days",
        ]
        read_only_fields = fields  # Machen wir erstmal alles read-only hier


class ActiveExamAttemptSerializer(BaseExamAttemptSerializer):
    """Serializer für aktive Prüfungen des Benutzers."""

    class Meta(BaseExamAttemptSerializer.Meta):
        # Felder auswählen, die für aktive Prüfungen relevant sind
        fields = [
            "id",
            "exam",
            "status",  # Sollte immer 'started' sein
            "started_at",
            "due_date",
            "remaining_days",
            "attachments",  # Evtl. nützlich für Zwischenstände
        ]
        read_only_fields = fields


class CompletedExamAttemptSerializer(BaseExamAttemptSerializer):
    """Serializer für abgeschlossene Prüfungen des Benutzers."""

    class Meta(BaseExamAttemptSerializer.Meta):
        # Felder auswählen, die für abgeschlossene Prüfungen relevant sind
        fields = [
            "id",
            "exam",
            "status",  # Sollte 'submitted' oder 'graded' sein
            "started_at",
            "submitted_at",
            "graded_at",
            "score",
            "feedback",
            "criterion_scores",
            "processing_time_days",
            "attachments",
        ]
        read_only_fields = fields


# --- Serializers for Teacher Views ---


class TeacherSubmissionSerializer(BaseExamAttemptSerializer):
    """Serializer für die Lehreransicht der eingereichten Prüfungen."""

    # Fügt Benutzerdetails des Studenten hinzu
    user = UserSerializer(read_only=True)
    # NEU: Fügt Benutzerdetails des Bewerters hinzu
    graded_by = UserSerializer(read_only=True)

    class Meta(BaseExamAttemptSerializer.Meta):
        # Felder auswählen, die für die Lehrerbewertung relevant sind
        fields = [
            "id",
            "exam",
            "user",  # Student
            "status",
            "started_at",
            "submitted_at",
            "attachments",
            "graded_at",
            "graded_by",  # NEU: Feld hinzugefügt
            "score",
            "feedback",
            "criterion_scores",
            "processing_time_days",
        ]
        read_only_fields = fields


class CriterionScoreInputSerializer(serializers.Serializer):
    """Serializer für die Eingabe einer einzelnen Kriteriumbewertung durch den Lehrer."""

    criterion_id = serializers.IntegerField()
    # Ersetzt 'score' durch 'achieved_points'
    achieved_points = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=0,
        # MaxValue wird in validate geprüft
    )

    def validate(self, data):
        """Prüft, ob criterion existiert und achieved_points <= max_points ist."""
        criterion_id = data.get("criterion_id")
        achieved_points = data.get("achieved_points")

        try:
            criterion = ExamCriterion.objects.get(pk=criterion_id)
        except ExamCriterion.DoesNotExist:
            raise serializers.ValidationError(
                {"criterion_id": "Criterion with this ID does not exist."}
            )

        if achieved_points is not None and criterion.max_points is not None:
            if achieved_points > criterion.max_points:
                raise serializers.ValidationError(
                    {
                        "achieved_points": f"Achieved points ({achieved_points}) cannot exceed max points ({criterion.max_points}) for criterion ID {criterion_id}."
                    }
                )

        # Füge das Kriterium-Objekt zum validierten Daten hinzu, falls es später benötigt wird
        # data['criterion'] = criterion
        return data

    # Alte validate_criterion_id entfernt, da in validate integriert


class TeacherGradingSerializer(serializers.Serializer):
    """Serializer für die gesamte Bewertungseingabe durch den Lehrer."""

    scores = CriterionScoreInputSerializer(many=True)
    feedback = serializers.CharField(required=False, allow_blank=True)

    def validate_scores(self, value):
        """Stellt sicher, dass für jedes Kriterium der Prüfung ein Score angegeben wird."""
        # Den Attempt holen wir uns aus dem View-Kontext
        attempt = self.context.get("attempt")
        if not attempt:
            # Dieser Fehler sollte nicht auftreten, wenn der Serializer korrekt im View verwendet wird
            raise serializers.ValidationError("Attempt context is missing.")

        required_criterion_ids = set(attempt.exam.criteria.values_list("id", flat=True))
        provided_criterion_ids = set(item["criterion_id"] for item in value)

        missing_ids = required_criterion_ids - provided_criterion_ids
        if missing_ids:
            raise serializers.ValidationError(
                f"Missing scores for criteria IDs: {missing_ids}"
            )

        extra_ids = provided_criterion_ids - required_criterion_ids
        if extra_ids:
            raise serializers.ValidationError(
                f"Scores provided for non-exam criteria IDs: {extra_ids}"
            )

        # Prüfen auf doppelte Kriterien-IDs in der Eingabe
        if len(provided_criterion_ids) != len(value):
            raise serializers.ValidationError(
                "Duplicate criterion IDs provided in scores."
            )

        # Die Einzelpunkt-Validierung (<= max_points) geschieht im CriterionScoreInputSerializer.validate
        return value


# --- Alter Serializer für UserExamStatus (wird nicht mehr direkt verwendet) ---
class UserExamStatusSerializer(ExamSerializer):
    """Dieser Serializer wird nicht mehr direkt für die Views benötigt,
    da die Logik jetzt in spezifischeren Views/Serializern liegt.
    """

    user_status = serializers.SerializerMethodField()
    attempt_details = serializers.SerializerMethodField()

    class Meta(ExamSerializer.Meta):
        fields = ExamSerializer.Meta.fields + ["user_status", "attempt_details"]

    # Implementierungen von get_user_status und get_attempt_details bleiben hier,
    # falls sie an anderer Stelle nützlich sind, werden aber von den neuen Views
    # nicht direkt aufgerufen.
    def get_user_status(self, obj):
        # ... (alte Logik)
        user = self.context["request"].user
        if not user.is_authenticated:
            return "locked"

        attempt = (
            ExamAttempt.objects.filter(exam=obj, user=user)
            .order_by("-started_at")
            .first()
        )

        if attempt:
            return attempt.status  # started, submitted, graded
        else:
            if obj.is_available_for(user):
                return "available"
            else:
                return "locked"

    def get_attempt_details(self, obj):
        # ... (alte Logik)
        user = self.context["request"].user
        if not user.is_authenticated:
            return None

        attempt = (
            ExamAttempt.objects.filter(exam=obj, user=user)
            .order_by("-started_at")
            .first()
        )

        if attempt:
            # Hier müssten wir jetzt entscheiden, welchen Serializer wir nehmen...
            # Das wird jetzt direkt in den Views gemacht.
            # serializer = BaseExamAttemptSerializer(attempt, context=self.context)
            return None  # oder alte Logik beibehalten? Besser None.
        else:
            return None


# --- Compatibility Aliases für die bestehenden View-Importe ---

# Diese Aliase sorgen dafür, dass die alten Import-Namen in den Views weiterhin funktionieren
ExamListSerializer = ExamSerializer
ActiveExamSerializer = ActiveExamAttemptSerializer
CompletedExamSerializer = CompletedExamAttemptSerializer
GradeSubmissionSerializer = TeacherGradingSerializer
