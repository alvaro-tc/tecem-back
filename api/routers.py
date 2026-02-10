from api.authentication.viewsets import (
    RegisterViewSet,
    LoginViewSet,
    ActiveSessionViewSet,
    LogoutViewSet,
)
from rest_framework import routers
from api.user.viewsets import UserViewSet, ManageUserViewSet
import api.school.views as school_views

router = routers.DefaultRouter()

router.register(r"edit", UserViewSet, basename="user-edit")
router.register(r"register", RegisterViewSet, basename="register")
router.register(r"login", LoginViewSet, basename="login")
router.register(r"checkSession", ActiveSessionViewSet, basename="check-session")
router.register(r"logout", LogoutViewSet, basename="logout")

# User Management
router.register(r"manage-users", ManageUserViewSet, basename="manage-users")

# School Routes
router.register(r"periods", school_views.AcademicPeriodViewSet, basename="periods")
router.register(r"programs", school_views.ProgramViewSet, basename="programs")
router.register(r"subjects", school_views.SubjectViewSet, basename="subjects")
router.register(r"courses", school_views.CourseViewSet, basename="courses")
router.register(r"enrollments", school_views.EnrollmentViewSet, basename="enrollments")
router.register(r"families", school_views.FamilyRelationshipViewSet, basename="families")
router.register(r"main-evaluations", school_views.MainEvaluationViewSet, basename="main-evaluations")
router.register(r"sub-evaluations", school_views.SubEvaluationViewSet, basename="sub-evaluations")


# Publications
from api.publications.views import PublicationViewSet
router.register(r"publications", PublicationViewSet, basename="publications")

# Web Config (Social Media)
from api.web_config.views import SocialMediaViewSet, LandingPageConfigViewSet
router.register(r"web-config", SocialMediaViewSet, basename="web-config")
router.register(r"landing-page-config", LandingPageConfigViewSet, basename="landing-page-config")

router.register(r"scores", school_views.ScoreViewSet, basename="scores")
router.register(r"reports", school_views.ReportViewSet, basename="reports")
router.register(r"evaluation-templates", school_views.EvaluationTemplateViewSet, basename="evaluation-templates")
router.register(r"course-sub-criteria", school_views.CourseSubCriterionViewSet, basename="course-sub-criteria")
router.register(r"course-special-criteria", school_views.CourseSpecialCriterionViewSet, basename="course-special-criterion")
router.register(r"criterion-scores", school_views.CriterionScoreViewSet, basename="criterion-scores")
router.register(r"course-tasks", school_views.CourseTaskViewSet, basename="course-tasks")
router.register(r"task-scores", school_views.TaskScoreViewSet, basename="task-scores")
router.register(r"projects", school_views.ProjectViewSet, basename="projects")
router.register(r"project-registration", school_views.StudentProjectRegistrationViewSet, basename="project-registration")
router.register(r"student-course-registration", school_views.StudentCourseRegistrationViewSet, basename="student-course-registration")
router.register(r"registration-requests", school_views.RegistrationRequestViewSet, basename="registration-requests")

urlpatterns = [
    *router.urls,
]
