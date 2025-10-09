# student_management_app/urls.py
from django.urls import path
from . import views

app_name = "student_management_app"

urlpatterns = [
    path("", views.home, name="home"),

    # auth / login
    path("login/", views.loginPage, name="login"),
    path("do-login/", views.doLogin, name="doLogin"),
    path("logout/", views.logout_user, name="logout"),

    # registration (primary) and a compatibility alias 'register' used by templates
    path("registration/", views.registration, name="registration"),
    path("register/", views.registration, name="register"),  # <- added alias

    # dashboards
    path("admin-home/", views.admin_home, name="admin_home"),
    path("staff-home/", views.staff_home, name="staff_home"),
    path("student-home/", views.student_home, name="student_home"),

    # staff pages
    path("staff-attendance/", views.staff_attendance, name="staff_attendance"),
    path("staff-leave/", views.staff_leave, name="staff_leave"),
    path("staff-enter-result/", views.staff_enter_result, name="staff_enter_result"),

    # student pages
    path("student-leave/", views.student_leave, name="student_leave"),
    path("student-results/", views.student_results, name="student_results"),
    path("student-feedback/", views.student_feedback, name="student_feedback"),
    path("student-attendance-history/", views.student_attendance_history, name="student_attendance_history"),

    # HOD pages
    path("hod/leave-requests/", views.hod_leave_requests, name="hod_leave_requests"),
    path("hod/staff-leave/<int:leave_id>/", views.hod_process_staff_leave, name="hod_process_staff_leave"),
    path("hod/student-leave/<int:leave_id>/", views.hod_process_student_leave, name="hod_process_student_leave"),
]
