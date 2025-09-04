from django.urls import path
from .views import (
    EmployeeListView,
    AvailabilityListCreateView,
    AvailabilityDetailView,
    ShiftScheduleListCreateView,
    ShiftScheduleDetailView,
)

app_name = "shift_planner"

urlpatterns = [
    # Mitarbeiter
    path("employees/", EmployeeListView.as_view(), name="employee-list"),
    # Verfügbarkeiten
    path(
        "availabilities/",
        AvailabilityListCreateView.as_view(),
        name="availability-list",
    ),
    path(
        "availabilities/<int:pk>/",
        AvailabilityDetailView.as_view(),
        name="availability-detail",
    ),
    # Schichtpläne
    path("schedules/", ShiftScheduleListCreateView.as_view(), name="schedule-list"),
    path(
        "schedules/<int:pk>/", ShiftScheduleDetailView.as_view(), name="schedule-detail"
    ),
]
