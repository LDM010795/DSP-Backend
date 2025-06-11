from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

# Importiere die View-Module aus unseren sauberen Unterordnern
from .users import views as user_views
from .modules import views as module_views
from .final_exam import views as exam_views

app_name = 'elearning'

# --- URL-Patterns für die jeweiligen Untermodule ---

# Router nur für das User-CRUD-ViewSet, das unter /users/admin/users/ erscheinen soll
users_router = DefaultRouter()
users_router.register(r'admin/users', user_views.UserCrudViewSet, basename='admin-users')

# Alle URLs, die mit /users/... beginnen
users_urlpatterns = [
    path('logout/', user_views.LogoutView.as_view(), name='logout'),
    path('set-initial-password/', user_views.SetInitialPasswordView.as_view(), name='set_initial_password'),
    path('', include(users_router.urls)), # Bindet den /admin/users-Pfad ein
]

# Alle URLs, die mit /modules/... beginnen
modules_urlpatterns = [
    path('public/', module_views.ModuleListViewPublic.as_view(), name='module-list-public'),
    path('public/<int:pk>/', module_views.ModuleDetailViewPublic.as_view(), name='module-detail-public'),
    path('user/', module_views.UserModuleListView.as_view(), name='user-module-list'),
    path('user/<int:pk>/', module_views.UserModuleDetailView.as_view(), name='user-module-detail'),
    path('execute/', module_views.ExecutePythonCodeView.as_view(), name='execute-python-code'),
]

# Alle URLs, die mit /exams/... beginnen
exams_urlpatterns = [
    path('my-exams/available/', exam_views.AvailableExamsView.as_view(), name='my-available-exams'),
    path('my-exams/active/', exam_views.ActiveExamsView.as_view(), name='my-active-exams'),
    path('my-exams/completed/', exam_views.CompletedExamsView.as_view(), name='my-completed-exams'),
    path('all/', exam_views.AllExamsListView.as_view(), name='all-exams-list'),
    path('<int:exam_id>/start/', exam_views.StartExamView.as_view(), name='start-exam'),
    path('attempts/<int:attempt_id>/submit/', exam_views.SubmitExamView.as_view(), name='submit-exam'),
    path('teacher/submissions/', exam_views.TeacherSubmissionsListView.as_view(), name='teacher-submissions'),
    path('teacher/submissions/<int:attempt_id>/grade/', exam_views.TeacherGradeAttemptView.as_view(), name='teacher-grade-attempt'),
    path('certification-paths/', exam_views.CertificationPathViewSet.as_view({'get': 'list'}), name='certification-path-list'),
]


# --- Haupt-URL-Liste für die gesamte 'elearning' App ---

urlpatterns = [
    # 1. Authentifizierungs-Endpunkte (direkt unter /api/)
    path('token/', user_views.CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    
    # 2. Bündelung der Untermodul-URLs mit ihren originalen Prefixen
    path('users/', include((users_urlpatterns, 'users'))),
    path('modules/', include((modules_urlpatterns, 'modules'))),
    path('exams/', include((exams_urlpatterns, 'exams'))),
]
