from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone

# Angepasste Importe
from ..models import Exam, ExamAttempt
from ..serializers import ExamListSerializer, ActiveExamSerializer, CompletedExamSerializer

class AvailableExamsView(generics.ListAPIView):
    serializer_class = ExamListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        all_exams = Exam.objects.all()
        return [exam for exam in all_exams if exam.is_available_for(user)]

class ActiveExamsView(generics.ListAPIView):
    serializer_class = ActiveExamSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ExamAttempt.objects.filter(
            user=self.request.user, status=ExamAttempt.Status.STARTED
        ).select_related('exam').order_by('-started_at')

class CompletedExamsView(generics.ListAPIView):
    serializer_class = CompletedExamSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ExamAttempt.objects.filter(
            user=self.request.user
        ).exclude(
            status=ExamAttempt.Status.STARTED
        ).select_related('exam').order_by('-submitted_at')

class StartExamView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, exam_id):
        exam = get_object_or_404(Exam, pk=exam_id)
        user = request.user

        if not exam.is_available_for(user):
            return Response({'error': 'Diese Prüfung ist für Sie nicht verfügbar.'}, status=status.HTTP_403_FORBIDDEN)

        attempt = ExamAttempt.objects.create(exam=exam, user=user)
        return Response({'attempt_id': attempt.id, 'message': 'Prüfung erfolgreich gestartet.'}, status=status.HTTP_201_CREATED)

class SubmitExamView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, attempt_id):
        attempt = get_object_or_404(ExamAttempt, pk=attempt_id, user=request.user)
        if attempt.status != ExamAttempt.Status.STARTED:
            return Response({'error': 'Dieser Versuch kann nicht mehr abgegeben werden.'}, status=status.HTTP_400_BAD_REQUEST)

        attempt.status = ExamAttempt.Status.SUBMITTED
        attempt.submitted_at = timezone.now()
        attempt.save()
        return Response({'message': 'Prüfung erfolgreich abgegeben.'}, status=status.HTTP_200_OK) 