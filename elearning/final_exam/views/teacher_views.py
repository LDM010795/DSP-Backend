from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ..models import ExamAttempt, ExamCriterion, CriterionScore, Exam
from ..serializers import (
    TeacherSubmissionSerializer,
    TeacherGradingSerializer,
    ExamListSerializer,
)


class TeacherSubmissionsListView(generics.ListAPIView):
    serializer_class = TeacherSubmissionSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        return (
            ExamAttempt.objects.filter(status=ExamAttempt.Status.SUBMITTED)
            .select_related("user", "exam")
            .order_by("submitted_at")
        )


class TeacherGradeAttemptView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, attempt_id):
        attempt = get_object_or_404(ExamAttempt, pk=attempt_id)

        # ---- Backward-compat normalization (accept dict or list) ----
        data = request.data.copy()
        scores = data.get("scores")
        if isinstance(scores, dict):
            # convert {"12": 9, "13": 4} -> [{"criterion_id": 12, "achieved_points": 9}, ...]
            data["scores"] = [
                {"criterion_id": int(k), "achieved_points": v}
                for k, v in scores.items()
            ]

        serializer = TeacherGradingSerializer(
            data=data,
            context={"request": request, "attempt": attempt},
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        scores_data = serializer.validated_data["scores"]
        feedback = serializer.validated_data.get("feedback", "")

        for item in scores_data:
            criterion_id = item["criterion_id"]
            points = item["achieved_points"]
            criterion = get_object_or_404(
                ExamCriterion, pk=criterion_id, exam=attempt.exam
            )
            CriterionScore.objects.update_or_create(
                attempt=attempt,
                criterion=criterion,
                defaults={"achieved_points": points},
            )

        attempt.feedback = feedback
        attempt.graded_by = request.user
        attempt.status = ExamAttempt.Status.GRADED
        attempt.graded_at = timezone.now()
        attempt.save(update_fields=["feedback", "graded_by", "status", "graded_at"])

        return Response(
            {"message": "Bewertung erfolgreich gespeichert."}, status=status.HTTP_200_OK
        )


class AllExamsListView(generics.ListAPIView):
    queryset = Exam.objects.all()
    serializer_class = ExamListSerializer
    permission_classes = [permissions.IsAuthenticated]
