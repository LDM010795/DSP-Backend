"""
Employees Views Test Suite
==========================

Purpose
-------
End-to-end-ish tests (via DRF APIClient) for the employees app viewsets:
- DepartmentViewSet
- PositionViewSet
- EmployeeViewSet (incl. actions: active, by_department, statistics)
- ToolViewSet (staff vs non-staff visibility)
- AttendanceViewSet (object-level scoping + filters)

Scope & Approach
----------------
- Focus on VIEW behavior (routing, permissions, queryset filters, actions, response shape).
- Serializers are covered indirectly via the view responses (no dedicated serializer unit tests here).
- No external services are used/mocked in this suite.

Fixtures Strategy
-----------------
- Class-level immutable data is created once in `setUpTestData(cls)` for speed.
  Treat these objects as READ-ONLY inside tests.
- A fresh authenticated `APIClient` is created in `setUp(self)` for each test:
  `force_authenticate(self.user)` is used to exercise `IsAuthenticated` endpoints
  without depending on the auth/JWT flow.

Conventions
-----------
- Test methods use clear names: `test_<feature>_<behavior>()`.
- Avoid inter-test coupling; every test must be order-independent.
- Prefer named URLs with `reverse()` if route names are available; paths here assume
  routes like `/api/employees/.../`.
- Keep assertions high-signal: status codes, counts, key fields, and behavior toggles
  (e.g., staff vs non-staff).

References
----------
- Django Testing Overview: https://docs.djangoproject.com/en/stable/topics/testing/overview/

Author: DSP Development Team
Date: 2025-09-09
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from datetime import date
from unittest import skip
from decimal import Decimal

from core.employees.models import (
    Department,
    Position,
    Employee,
    Attendance,
    Tool,
    EmployeeToolAccess,
)

User = get_user_model()


class EmployeeViewTests(TestCase):
    """
    One big TestCase for all core/employees viewsets:
    - DepartmentViewSet
    - PositionViewSet
    - EmployeeViewSet (incl. actions: active, by_department, statistics)
    - ToolViewSet (staff vs. non-staff visibility)
    - EmployeeToolAccessViewSet (filters)
    - AttendanceViewSet (object-level scoping + filters)
    """

    @classmethod
    def setUpTestData(cls):
        # Users
        # We could add users also if the Employee model has a user field. (need to discuss it)
        cls.user = User.objects.create_user("u1", "u1@example.com", "pass")
        # cls.user2 = User.objects.create_user("u2", "u2@example.com", "pass")
        # cls.user3 = User.objects.create_user("u3", "u3@example.com", "pass")

        # Departments
        cls.dept_a = Department.objects.create(name="A", is_active=True)
        cls.dept_b = Department.objects.create(name="B", is_active=True)

        # Positions
        cls.pos_dev = Position.objects.create(title="Dev", is_active=True)
        cls.pos_hr = Position.objects.create(title="HR", is_active=True)

        # Employees
        cls.emp_self = Employee.objects.create(
            # user=cls.user
            first_name="Alpha",
            last_name="Tester",
            email="u1@example.com",
            department=cls.dept_a,
            position=cls.pos_dev,
            is_active=True,
            max_working_hours=30,
        )
        cls.emp2 = Employee.objects.create(
            # user=cls.user2,
            first_name="Beta",
            last_name="Inactive",
            email="u2@example.com",
            department=cls.dept_a,
            position=cls.pos_hr,
            is_active=False,
            max_working_hours=10,
        )
        cls.emp3 = Employee.objects.create(
            # user=cls.user3,
            first_name="Gamma",
            last_name="Active",
            email="u3@example.com",
            department=cls.dept_b,
            position=cls.pos_dev,
            is_active=True,
            max_working_hours=40,
        )

        # Attendance (two for self, one for others)
        Attendance.objects.create(
            employee=cls.emp_self,
            department=cls.dept_a,
            date=date(2025, 5, 10),
            hours=Decimal("6"),
        )
        Attendance.objects.create(
            employee=cls.emp_self,
            department=cls.dept_a,
            date=date(2025, 6, 1),
            hours=Decimal("4"),
        )
        Attendance.objects.create(
            employee=cls.emp2,
            department=cls.dept_a,
            date=date(2025, 6, 2),
            hours=Decimal("3"),
        )

    def setUp(self):
        self.client = APIClient()
        # reset user baseline so tests are independent
        self.user.refresh_from_db()
        self.user.is_staff = False
        self.user.is_superuser = False
        self.user.save()
        self.client.force_authenticate(self.user)

    # ----------------- Departments -----------------

    def test_departments_requires_auth(self):
        anon = APIClient()
        resp = anon.get("/api/employees/departments/")
        self.assertEqual(resp.status_code, 401)

    def test_departments_list_filter_search_active_action(self):
        Department.objects.create(name="HR", is_active=False)
        Department.objects.create(name="Helpdesk", is_active=True)

        resp = self.client.get("/api/employees/departments/")
        self.assertEqual(resp.status_code, 200)
        # Expected: A, B, HR, Helpdesk
        self.assertEqual(len(resp.json()), 4)

        resp = self.client.get("/api/employees/departments/?is_active=false")
        self.assertEqual(len(resp.json()), 1)
        self.assertEqual(resp.json()[0]["name"], "HR")

        resp = self.client.get("/api/employees/departments/?search=help")
        self.assertEqual(len(resp.json()), 1)
        self.assertEqual(resp.json()[0]["name"], "Helpdesk")

        resp = self.client.get("/api/employees/departments/active/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual({d["name"] for d in resp.json()}, {"A", "B", "Helpdesk"})

    # ----------------- Positions -----------------

    def test_positions_list_filter_search_active_action(self):
        # Already have Dev, HR (active); add one active and one inactive
        Position.objects.create(title="Devops", is_active=True)
        Position.objects.create(title="Recruiter", is_active=False)

        resp = self.client.get("/api/employees/positions/")
        self.assertEqual(resp.status_code, 200)
        # Expected: Dev, HR, Devops, Recruiter
        self.assertEqual(len(resp.json()), 4)

        resp = self.client.get("/api/employees/positions/?is_active=false")
        self.assertEqual(len(resp.json()), 1)
        self.assertEqual(resp.json()[0]["title"], "Recruiter")

        resp = self.client.get("/api/employees/positions/?search=dev")
        # "Dev" appears in Dev + Devops
        self.assertEqual(len(resp.json()), 2)

        resp = self.client.get("/api/employees/positions/active/")
        self.assertEqual({p["title"] for p in resp.json()}, {"Dev", "HR", "Devops"})

    # ----------------- Employees -----------------

    def test_employees_list_filter_search(self):
        resp = self.client.get("/api/employees/employees/")
        self.assertEqual(resp.status_code, 200)
        # Expected: emp_self (Alpha), emp2 (Beta), emp3 (Gamma)
        self.assertEqual(len(resp.json()), 3)

        resp = self.client.get("/api/employees/employees/?is_active=true")
        self.assertEqual(len(resp.json()), 2)

        r = self.client.get(f"/api/employees/employees/?department={self.dept_b.id}")
        self.assertEqual(len(r.json()), 1)

        r = self.client.get(f"/api/employees/employees/?position={self.pos_hr.id}")
        self.assertEqual(len(r.json()), 1)

        r = self.client.get("/api/employees/employees/?search=dev")
        # Dev position => emp_self (A/Dev) + emp3 (B/Dev)
        self.assertEqual(len(r.json()), 2)

    def test_employees_active_action(self):
        resp = self.client.get("/api/employees/employees/active/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 2)

    def test_employees_by_department_action(self):
        resp = self.client.get("/api/employees/employees/by_department/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        # Only active employees are grouped
        self.assertIn("A", data)
        self.assertIn("B", data)
        self.assertEqual(len(data["A"]), 1)  # emp_self
        self.assertEqual(len(data["B"]), 1)  # emp3

    def test_employees_statistics_action(self):
        resp = self.client.get("/api/employees/employees/statistics/")
        self.assertEqual(resp.status_code, 200)
        stats = resp.json()
        self.assertEqual(stats["total_employees"], 3)
        self.assertEqual(stats["active_employees"], 2)
        self.assertEqual(stats["inactive_employees"], 1)
        self.assertGreaterEqual(stats["departments_count"], 2)
        self.assertGreaterEqual(stats["positions_count"], 2)
        self.assertIsInstance(stats["average_working_hours"], (int, float))
        self.assertGreater(stats["average_working_hours"], 0)

    # ----------------- Tools -----------------

    def test_tools_visibility_non_staff_and_staff(self):
        Tool.objects.create(slug="active-1", name="Active One", is_active=True)
        Tool.objects.create(slug="active-2", name="Active Two", is_active=True)
        Tool.objects.create(slug="inactive-1", name="Inactive One", is_active=False)

        # Non-staff sees only active
        resp = self.client.get("/api/employees/tools/")
        self.assertEqual(resp.status_code, 200)
        slugs = {t["slug"] for t in resp.json()}
        self.assertEqual(slugs, {"active-1", "active-2"})

        # Staff sees all
        self.user.is_staff = True
        self.user.save()
        resp = self.client.get("/api/employees/tools/")
        self.assertEqual(resp.status_code, 200)
        slugs = {t["slug"] for t in resp.json()}
        self.assertEqual(slugs, {"active-1", "active-2", "inactive-1"})

    # ----------------- EmployeeToolAccess -----------------

    def test_employee_tool_access_filters(self):
        tool1 = Tool.objects.create(slug="elearning", name="E-Learning", is_active=True)
        tool2 = Tool.objects.create(slug="planner", name="Planner", is_active=True)
        EmployeeToolAccess.objects.create(employee=self.emp_self, tool=tool1)
        EmployeeToolAccess.objects.create(employee=self.emp_self, tool=tool2)

        resp = self.client.get(
            f"/api/employees/tool-access/?employee={self.emp_self.id}"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 2)

        resp = self.client.get(
            f"/api/employees/tool-access/?employee={self.emp_self.id}&tool={tool1.id}"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)
        self.assertEqual(resp.json()[0]["tool"]["id"], tool1.id)

    # ----------------- Attendance -----------------

    @skip("Pending Employee.user relation; non-staff scoping not testable yet.")
    def test_attendance_non_staff_sees_only_own(self):
        pass

    def test_attendance_staff_sees_everyone(self):
        self.user.is_staff = True
        self.user.save()
        resp = self.client.get("/api/employees/attendances/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 3)  # all three records visible to staff

    def test_attendance_filter_month_year_staff(self):
        self.user.is_staff = True
        self.user.save()
        resp = self.client.get("/api/employees/attendances/?month=6&year=2025")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 2)  # June 1 (emp_self) + June 2 (emp2)
