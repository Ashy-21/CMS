from django.urls import path
from . import views


app_name = "student_management_app"

urlpatterns = [
    path("", views.home, name="home"),

    path("login/", views.loginPage, name="login"),
    path("do-login/", views.doLogin, name="doLogin"),
    path("logout/", views.logout_user, name="logout"),

    path("registration/", views.registration, name="registration"),
    path("registration/", views.registration, name="register"),

    path("admin-home/", views.admin_home, name="admin_home"),
    path("staff-home/", views.staff_home, name="staff_home"),
    path("student-home/", views.student_home, name="student_home"),

    path("student/subject/<int:student_id>/<int:result_id>/", views.student_subject_detail, name="student_subject_detail"),

    path("api/student/subject-data/<int:student_id>/<int:result_id>/", views.api_student_subject_data, name="api_student_subject_data"),

    path("staff-attendance/", views.staff_attendance, name="staff_attendance"),
    path("staff-leave/", views.staff_leave, name="staff_leave"),
    path("staff-enter-result/", views.staff_enter_result, name="staff_enter_result"),

    path("staff/students/", views.staff_student_list, name="staff_student_list"),
    path("staff/edit-attendance/<int:attendance_report_id>/", views.staff_edit_attendance, name="staff_edit_attendance"),
    path("staff/edit-result/<int:result_id>/", views.staff_edit_result, name="staff_edit_result"),

    path("student-leave/", views.student_leave, name="student_leave"),
    path("student-results/", views.student_results, name="student_results"),
    path("student-feedback/", views.student_feedback, name="student_feedback"),
    path("student-attendance-history/", views.student_attendance_history, name="student_attendance_history"),

    path("hod/leave-requests/", views.hod_leave_requests, name="hod_leave_requests"),
    path("hod/staff-leave/<int:leave_id>/", views.hod_process_staff_leave, name="hod_process_staff_leave"),
    path("hod/student-leave/<int:leave_id>/", views.hod_process_student_leave, name="hod_process_student_leave"),
]
