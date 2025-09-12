"""
Final Exam – Student Views Test Suite

Covers:
- AvailableExamsView (auth-only; filters via Exam.is_available_for(user))
- ActiveExamsView (auth-only; only STARTED attempts for the current user, newest first)
- CompletedExamsView (auth-only; excludes STARTED, newest submitted first)
- StartExamView (auth-only; respects availability; creates attempt)
- SubmitExamView (auth-only; only for own STARTED attempt; moves to SUBMITTED)

Author: DSP Development Team
Date: 2025-09-11
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from unittest.mock import patch
from rest_framework.test import APIClient

from elearning.final_exam.models import Exam, ExamAttempt

User = get_user_model()

AVAILABLE_URL = "/api/elearning/exams/my-exams/available/"
ACTIVE_URL = "/api/elearning/exams/my-exams/active/"
COMPLETED_URL = "/api/elearning/exams/my-exams/completed/"
START_URL_TMPL = "/api/elearning/exams/{exam_id}/start/"
SUBMIT_URL_TMPL = "/api/elearning/exams/attempts/{attempt_id}/submit/"


class StudentExamViewsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Users
        cls.student = User.objects.create_user(
            username="s1", email="s1@example.com", password="pass"
        )
        cls.other = User.objects.create_user(
            username="s2", email="s2@example.com", password="pass"
        )

        # Exams (titles used by availability monkeypatch)
        cls.exam_open_1 = Exam.objects.create(
            title="Open - Python", duration_weeks=6, description="desc"
        )
        cls.exam_open_2 = Exam.objects.create(
            title="Open - DS", duration_weeks=8, description="desc"
        )
        cls.exam_locked = Exam.objects.create(
            title="Locked - Python", duration_weeks=4, description="desc"
        )

        # Attempts (use bulk_create so ExamAttempt.save() doesn't run during creation)
        now = timezone.now()
        attempts = [
            # STARTED (for ACTIVE)
            ExamAttempt(
                user=cls.student,
                exam=cls.exam_open_1,
                status=ExamAttempt.Status.STARTED,
                started_at=now - timezone.timedelta(hours=2),
            ),
            ExamAttempt(
                user=cls.student,
                exam=cls.exam_open_2,
                status=ExamAttempt.Status.STARTED,
                started_at=now - timezone.timedelta(hours=1),
            ),
            # Another user's started attempt (should not appear for s1)
            ExamAttempt(
                user=cls.other,
                exam=cls.exam_open_1,
                status=ExamAttempt.Status.STARTED,
                started_at=now - timezone.timedelta(minutes=30),
            ),
            # COMPLETED (submitted/graded) for current user
            ExamAttempt(
                user=cls.student,
                exam=cls.exam_open_1,
                status=ExamAttempt.Status.SUBMITTED,
                started_at=now - timezone.timedelta(days=3),
                submitted_at=now - timezone.timedelta(days=2, hours=1),
            ),
            ExamAttempt(
                user=cls.student,
                exam=cls.exam_open_2,
                status=ExamAttempt.Status.GRADED,
                started_at=now - timezone.timedelta(days=4),
                submitted_at=now
                - timezone.timedelta(days=2),  # newer submitted -> should be first
                graded_at=now - timezone.timedelta(days=1, hours=20),
            ),
        ]
        ExamAttempt.objects.bulk_create(attempts)

        # Reattach handles for assertions
        started_list = list(
            ExamAttempt.objects.filter(
                user=cls.student, status=ExamAttempt.Status.STARTED
            ).order_by("started_at")
        )
        cls.start_old, cls.start_new = started_list[0], started_list[1]

        cls.submitted = ExamAttempt.objects.get(
            user=cls.student, exam=cls.exam_open_1, status=ExamAttempt.Status.SUBMITTED
        )
        cls.graded = ExamAttempt.objects.get(
            user=cls.student, exam=cls.exam_open_2, status=ExamAttempt.Status.GRADED
        )

    def setUp(self):
        self.client = APIClient()

    # -------------- permission ----------------

    def test_requires_auth_all_lists_and_actions(self):
        anon = APIClient()
        self.assertEqual(anon.get(AVAILABLE_URL).status_code, 401)
        self.assertEqual(anon.get(ACTIVE_URL).status_code, 401)
        self.assertEqual(anon.get(COMPLETED_URL).status_code, 401)
        self.assertEqual(
            anon.post(START_URL_TMPL.format(exam_id=self.exam_open_1.id)).status_code,
            401,
        )
        self.assertEqual(
            anon.post(SUBMIT_URL_TMPL.format(attempt_id=self.start_old.id)).status_code,
            401,
        )

    # ------------- AvailableExamView --------------

    def test_available_exams_filters_by_is_available_for(self):
        """
        Monkeypatch Exam.is_available_for to simulate availability.
        We'll allow titles starting with 'Open'.
        """
        self.client.force_authenticate(self.student)

        def fake_is_available_for(exam_self, user):
            return exam_self.title.startswith("Open")

        with patch(
            "elearning.final_exam.models.Exam.is_available_for",
            new=fake_is_available_for,
        ):
            resp = self.client.get(AVAILABLE_URL)
        self.assertEqual(resp.status_code, 200)

        titles = {e["exam_title"] for e in resp.json()}
        self.assertEqual(titles, {"Open - Python", "Open - DS"})
        self.assertNotIn("Locked - Python", titles)

    # ---------- ActiveExamsView -------------

    def test_active_exams_lists_only_started_for_user_newest_first(self):
        self.client.force_authenticate(self.student)
        resp = self.client.get(ACTIVE_URL)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        # only the two current user's STARTED attempts, newest first
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["id"], self.start_new.id)
        self.assertEqual(data[1]["id"], self.start_old.id)

    # ---------- CompletedExamsView ----------

    def test_completed_exams_excludes_started_and_orders_by_submitted_desc(self):
        self.client.force_authenticate(self.student)
        resp = self.client.get(COMPLETED_URL)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        # Should include submitted + graded, newest submitted_at first -> graded then submitted
        self.assertEqual([d["id"] for d in data], [self.graded.id, self.submitted.id])

    # ---------- StartExamView ----------

    def test_start_exam_forbidden_when_not_available(self):
        self.client.force_authenticate(self.student)
        with patch(
            "elearning.final_exam.models.Exam.is_available_for", return_value=False
        ):
            resp = self.client.post(START_URL_TMPL.format(exam_id=self.exam_locked.id))
        self.assertEqual(resp.status_code, 403)

    def test_start_exam_creates_attempt_and_returns_201(self):
        self.client.force_authenticate(self.student)
        with patch(
            "elearning.final_exam.models.Exam.is_available_for", return_value=True
        ):
            resp = self.client.post(START_URL_TMPL.format(exam_id=self.exam_locked.id))
        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        self.assertIn("attempt_id", body)
        # Verify attempt exists and belongs to user
        attempt = ExamAttempt.objects.get(id=body["attempt_id"])
        self.assertEqual(attempt.user_id, self.student.id)
        self.assertEqual(attempt.exam_id, self.exam_locked.id)
        self.assertEqual(attempt.status, ExamAttempt.Status.STARTED)

    # ---------- SubmitExamView ----------

    def test_submit_exam_404_if_attempt_not_owned(self):
        self.client.force_authenticate(self.student)
        ExamAttempt.objects.bulk_create(
            [
                ExamAttempt(
                    user=self.other,
                    exam=self.exam_open_1,
                    status=ExamAttempt.Status.STARTED,
                )
            ]
        )
        other_attempt = ExamAttempt.objects.filter(
            user=self.other, exam=self.exam_open_1, status=ExamAttempt.Status.STARTED
        ).first()

        resp = self.client.post(SUBMIT_URL_TMPL.format(attempt_id=other_attempt.id))
        self.assertEqual(resp.status_code, 404)

    def test_submit_exam_400_if_not_started(self):
        self.client.force_authenticate(self.student)
        # already submitted in fixtures -> reuse
        resp = self.client.post(SUBMIT_URL_TMPL.format(attempt_id=self.submitted.id))
        self.assertEqual(resp.status_code, 400)

    def test_submit_exam_success_updates_status_and_timestamp(self):
        self.client.force_authenticate(self.student)
        ExamAttempt.objects.bulk_create(
            [
                ExamAttempt(
                    user=self.student,
                    exam=self.exam_open_1,
                    status=ExamAttempt.Status.STARTED,
                )
            ]
        )
        fresh = (
            ExamAttempt.objects.filter(
                user=self.student,
                exam=self.exam_open_1,
                status=ExamAttempt.Status.STARTED,
            )
            .order_by("-id")
            .first()
        )

        resp = self.client.post(SUBMIT_URL_TMPL.format(attempt_id=fresh.id))
        self.assertEqual(resp.status_code, 200)

        fresh.refresh_from_db()
        self.assertEqual(fresh.status, ExamAttempt.Status.SUBMITTED)
        self.assertIsNotNone(fresh.submitted_at)
