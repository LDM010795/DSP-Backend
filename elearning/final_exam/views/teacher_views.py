from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

# Angepasste Importe
from ..models import ExamAttempt, ExamCriterion, CriterionScore
from ..serializers import TeacherSubmissionSerializer, GradeSubmissionSerializer

class TeacherSubmissionsListView(generics.ListAPIView):
    serializer_class = TeacherSubmissionSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        return ExamAttempt.objects.filter(status=ExamAttempt.Status.SUBMITTED).select_related('user', 'exam').order_by('submitted_at')

class TeacherGradeAttemptView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, attempt_id):
        attempt = get_object_or_404(ExamAttempt, pk=attempt_id)
        serializer = GradeSubmissionSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        scores_data = serializer.validated_data['scores']
        feedback = serializer.validated_data.get('feedback', '')

        for criterion_id, points in scores_data.items():
            criterion = get_object_or_404(ExamCriterion, pk=criterion_id, exam=attempt.exam)
            CriterionScore.objects.update_or_create(
                attempt=attempt,
                criterion=criterion,
                defaults={'achieved_points': points}
            )
        
        attempt.feedback = feedback
        attempt.graded_by = request.user
        attempt.status = ExamAttempt.Status.GRADED
        attempt.save()

        return Response({'message': 'Bewertung erfolgreich gespeichert.'}, status=status.HTTP_200_OK)

class AllExamsListView(generics.ListAPIView):
    from ..models import Exam
    from ..serializers import ExamListSerializer
    
    queryset = Exam.objects.all()
    serializer_class = ExamListSerializer
    permission_classes = [permissions.IsAdminUser] 