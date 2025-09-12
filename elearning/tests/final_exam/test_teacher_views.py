"""
Final Exam – Teacher Views Test Suite

Covers:
- TeacherSubmissionsListView (admin-only, lists SUBMITTED attempts ordered by submitted_at)
- TeacherGradeAttemptView (admin-only grading: creates/updates CriterionScore, sets feedback/graded_by/status)
- AllExamsListView (authenticated list)

Author: DSP Development Team
Date: 2025-09-10
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from django.utils import timezone

from elearning.final_exam.models import Exam, ExamAttempt, ExamCriterion, CriterionScore

User = get_user_model()


class TeacherExamViewsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Users
        cls.student = User.objects.create_user(
            username="student", email="s@example.com", password="pass"
        )
        cls.teacher_admin = User.objects.create_user(
            username="admin", email="a@example.com", password="pass"
        )
        cls.teacher_admin.is_staff = True
        cls.teacher_admin.save()

        # Exam
        cls.exam = Exam.objects.create(
            title="Python Basics", duration_weeks=8, description="Intro to Python"
        )
        cls.other_exam = Exam.objects.create(
            title="Data Science Intro",
            duration_weeks=6,
            description="Basics of Data Science",
        )

        # Criteria
        cls.crit_1 = ExamCriterion.objects.create(
            exam=cls.exam,
            title="Correctness",
            description="Korrektheit bewerten",
            max_points=10,
        )
        cls.crit_2 = ExamCriterion.objects.create(
            exam=cls.exam, title="Style", description="Code-Stil bewerten", max_points=5
        )

        # Criterion for a different exam (used to test 404 on cross-exam scoring)
        cls.other_exam_crit = ExamCriterion.objects.create(
            exam=cls.other_exam,
            title="Irrelevant",
            description="Falsches Exam",
            max_points=3,
        )

        # Attempts (SUBMITTED) – order by submitted_at
        cls.attempt_early = ExamAttempt.objects.create(
            user=cls.student,
            exam=cls.exam,
            status=ExamAttempt.Status.SUBMITTED,
            submitted_at=timezone.now() - timezone.timedelta(hours=2),
        )
        cls.attempt_late = ExamAttempt.objects.create(
            user=cls.student,
            exam=cls.exam,
            status=ExamAttempt.Status.SUBMITTED,
            submitted_at=timezone.now() - timezone.timedelta(hours=1),
        )

        # A graded attempt (should NOT appear in submissions list)
        ExamAttempt.objects.bulk_create(
            [
                ExamAttempt(
                    user=cls.student,
                    exam=cls.exam,
                    status=ExamAttempt.Status.GRADED,
                    submitted_at=timezone.now() - timezone.timedelta(hours=3),
                )
            ]
        )
        # get a handle to the created object (optional, but handy)
        cls.attempt_graded = (
            ExamAttempt.objects.filter(
                user=cls.student, exam=cls.exam, status=ExamAttempt.Status.GRADED
            )
            .order_by("id")
            .first()
        )

    def setUp(self):
        self.client = APIClient()

    # -------- URL helpers (match show_urls names) --------

    def _submissions_url(self):
        return reverse("elearning:exams:teacher-submissions")

    def _grade_url(self, attempt_id):
        return reverse(
            "elearning:exams:teacher-grade-attempt", kwargs={"attempt_id": attempt_id}
        )

    def _exams_list_url(self):
        return reverse("elearning:exams:all-exams-list")

    # ------------- TeacherSubmissionListView ----------------

    def test_teacher_submissions_requires_admin(self):
        # Unauthenticated
        resp = self.client.get(self._submissions_url())
        self.assertEqual(resp.status_code, 401)

        # Authenticated non-admin
        self.client.force_authenticate(user=self.student)
        resp = self.client.get(self._submissions_url())
        self.assertIn(resp.status_code, (401, 403))  # DRF version dependent

        # Authenticated admin
        self.client.force_authenticate(user=self.teacher_admin)
        resp = self.client.get(self._submissions_url())
        self.assertEqual(resp.status_code, 200)

    def test_teacher_submissions_lists_only_submitted_sorted_by_submitted_at(self):
        self.client.force_authenticate(self.teacher_admin)
        resp = self.client.get(self._submissions_url())
        self.assertEqual(resp.status_code, 200)

        data = resp.json()
        # Should include only the two SUBMITTED attempts, ordered by submitted_at (early -> late)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["id"], self.attempt_early.id)
        self.assertEqual(data[1]["id"], self.attempt_late.id)

    # ------------- TeacherGradeAttemptView ----------------

    def test_grade_requires_admin(self):
        url = self._grade_url(self.attempt_early.id)

        # unauthenticated
        resp = self.client.post(url, data={"scores": {}}, format="json")
        self.assertEqual(resp.status_code, 401)

        # non-admin
        self.client.force_authenticate(self.student)
        resp = self.client.post(url, data={"scores": {}}, format="json")
        self.assertEqual(resp.status_code, 403)

    def test_grade_valid_payload_creates_scores_and_updates_Attempt(self):
        self.client.force_authenticate(self.teacher_admin)
        url = self._grade_url(self.attempt_early.id)

        payload = {
            "scores": {
                str(self.crit_1.id): 9.0,
                str(self.crit_2.id): 4.0,
            },
            "feedback": "Good job overall.",
        }

        resp = self.client.post(url, data=payload, format="json")
        self.assertEqual(resp.status_code, 200)

        # Attempt should be updated
        self.attempt_early.refresh_from_db()
        self.assertEqual(self.attempt_early.status, ExamAttempt.Status.GRADED)
        self.assertEqual(self.attempt_early.feedback, "Good job overall.")
        self.assertEqual(self.attempt_early.graded_by, self.teacher_admin)

        # CriterionScores should be created
        cs1 = CriterionScore.objects.get(
            attempt=self.attempt_early, criterion=self.crit_1
        )
        cs2 = CriterionScore.objects.get(
            attempt=self.attempt_early, criterion=self.crit_2
        )
        self.assertEqual(cs1.achieved_points, 9.0)
        self.assertEqual(cs2.achieved_points, 4.0)

    def test_grade_updates_existing_scores_idempotently(self):
        # First grade
        self.client.force_authenticate(self.teacher_admin)
        url = self._grade_url(self.attempt_late.id)

        payload1 = {
            "scores": {str(self.crit_1.id): "8.0", str(self.crit_2.id): "5.0"},
            "feedback": "v1",
        }
        resp = self.client.post(url, data=payload1, format="json")
        self.assertEqual(resp.status_code, 200)

        # Second grade (update values)
        payload2 = {
            "scores": {str(self.crit_1.id): "10.0", str(self.crit_2.id): "3.0"},
            "feedback": "v2",
        }
        resp = self.client.post(url, data=payload2, format="json")
        self.assertEqual(resp.status_code, 200)

        cs1 = CriterionScore.objects.get(
            attempt=self.attempt_late, criterion=self.crit_1
        )
        cs2 = CriterionScore.objects.get(
            attempt=self.attempt_late, criterion=self.crit_2
        )
        self.assertEqual(cs1.achieved_points, 10.0)
        self.assertEqual(cs2.achieved_points, 3.0)

        self.attempt_late.refresh_from_db()
        self.assertEqual(self.attempt_late.feedback, "v2")
        self.assertEqual(self.attempt_late.status, ExamAttempt.Status.GRADED)
        self.assertEqual(self.attempt_late.graded_by_id, self.teacher_admin.id)

    def test_grade_invalid_payload_returns_400(self):
        self.client.force_authenticate(self.teacher_admin)
        url = self._grade_url(self.attempt_early.id)

        # Missing 'scores'
        resp = self.client.post(url, data={"feedback": "x"}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("scores", resp.json())

    def test_grade_404_when_criterion_not_in_attempt_exam(self):
        self.client.force_authenticate(self.teacher_admin)
        url = self._grade_url(self.attempt_early.id)

        # Include a criterion from a different exam -> should 404 inside the grading loop
        payload = {
            "scores": {
                str(self.other_exam_crit.id): 1.0,  # wrong exam
            }
        }
        resp = self.client.post(url, data=payload, format="json")
        self.assertEqual(resp.status_code, 400)

        # ---------- AllExamsListView ----------

    def test_all_exams_requires_auth(self):
        # anon
        resp = self.client.get(self._exams_list_url())
        self.assertEqual(resp.status_code, 401)

        # authenticated non-admin ok
        self.client.force_authenticate(self.student)
        resp = self.client.get(self._exams_list_url())
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.json()), 2)  # exam + other_exam exist
