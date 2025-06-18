"""
E-Learning Application URL Configuration

This module defines the complete URL routing structure for the E-Learning application.
It follows a modular approach where each functional area (users, modules, exams) 
has its own URL namespace while maintaining clean separation of concerns.

URL Structure:
- /api/token/: Authentication endpoints (JWT token management)
- /api/users/: User management and account operations
- /api/modules/: Learning content and module interactions
- /api/exams/: Examination system and certification management

Architecture Features:
- Modular URL organization with clear namespaces
- Separation of public and authenticated endpoints
- RESTful API design principles
- Comprehensive endpoint coverage for all features

Author: DSP Development Team
Version: 1.0.0
"""

from typing import List
from django.urls import path, include, URLPattern
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

# Import view modules from clean submodule structure
from .users import views as user_views
from .modules import views as module_views
from .final_exam import views as exam_views

app_name = 'elearning'

# --- URL Pattern Definitions for Submodules ---

def _create_users_router() -> DefaultRouter:
    """
    Create and configure the router for user management endpoints.
    
    Returns:
        Configured DefaultRouter for user CRUD operations
    """
    router = DefaultRouter()
    router.register(r'admin/users', user_views.UserCrudViewSet, basename='admin-users')
    return router

# Initialize user management router
users_router = _create_users_router()

# User management URL patterns
users_urlpatterns: List[URLPattern] = [
    # User authentication and account management
    path('logout/', user_views.LogoutView.as_view(), name='logout'),
    path('set-initial-password/', user_views.SetInitialPasswordView.as_view(), name='set_initial_password'),
    
    # User administration endpoints (requires admin privileges)
    path('', include(users_router.urls)),
]

# Learning modules URL patterns  
modules_urlpatterns: List[URLPattern] = [
    # Public module endpoints (no authentication required)
    path('public/', module_views.ModuleListViewPublic.as_view(), name='module-list-public'),
    path('public/<int:pk>/', module_views.ModuleDetailViewPublic.as_view(), name='module-detail-public'),
    
    # User-specific module endpoints (authentication required)
    path('user/', module_views.UserModuleListView.as_view(), name='user-module-list'),
    path('user/<int:pk>/', module_views.UserModuleDetailView.as_view(), name='user-module-detail'),
    
    # Interactive code execution endpoint
    path('execute/', module_views.ExecutePythonCodeView.as_view(), name='execute-python-code'),
]

# Examination system URL patterns
exams_urlpatterns: List[URLPattern] = [
    # Student exam management endpoints
    path('my-exams/available/', exam_views.AvailableExamsView.as_view(), name='my-available-exams'),
    path('my-exams/active/', exam_views.ActiveExamsView.as_view(), name='my-active-exams'),
    path('my-exams/completed/', exam_views.CompletedExamsView.as_view(), name='my-completed-exams'),
    
    # Exam administration and management
    path('all/', exam_views.AllExamsListView.as_view(), name='all-exams-list'),
    
    # Exam execution endpoints
    path('<int:exam_id>/start/', exam_views.StartExamView.as_view(), name='start-exam'),
    path('attempts/<int:attempt_id>/submit/', exam_views.SubmitExamView.as_view(), name='submit-exam'),
    
    # Teacher/grader endpoints (requires staff privileges)
    path('teacher/submissions/', exam_views.TeacherSubmissionsListView.as_view(), name='teacher-submissions'),
    path('teacher/submissions/<int:attempt_id>/grade/', exam_views.TeacherGradeAttemptView.as_view(), name='teacher-grade-attempt'),
    
    # Certification management
    path('certification-paths/', exam_views.CertificationPathViewSet.as_view({'get': 'list'}), name='certification-path-list'),
]

# --- Main URL Configuration for E-Learning Application ---

urlpatterns: List[URLPattern] = [
    # Authentication endpoints (JWT token management)
    path('token/', user_views.CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    
    # Functional area URL includes with proper namespacing
    path('users/', include((users_urlpatterns, 'users'))),
    path('modules/', include((modules_urlpatterns, 'modules'))),
    path('exams/', include((exams_urlpatterns, 'exams'))),
]
