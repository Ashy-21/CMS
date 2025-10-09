# student_management_app/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.core.exceptions import FieldError

from .models import (
    CustomUser, College, Department, Semester, AdminHOD, Staffs, Students,
    Course, SessionYear, Attendance, AttendanceReport,
    LeaveReportStaff, LeaveReportStudent, FeedbackStaff, FeedbackStudent, StudentResult
)

# Admin site branding
admin.site.site_header = "College CMS Admin"
admin.site.site_title = "College CMS Control"
admin.site.index_title = "Manage College CMS"


class TenantAdminMixin:
    """
    Admin mixin to scope lists/changes to the request.user.college for staff users.
    Superusers see everything.
    """
    def _user_college(self, request):
        return getattr(request.user, "college", None)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # only staff users linked to a college get scoped results
        if not request.user.is_staff:
            return qs.none()
        user_college = self._user_college(request)
        if not user_college:
            return qs.none()

        # attempt to filter by college field on model
        try:
            return qs.filter(college=user_college)
        except (FieldError, Exception):
            # model doesn't have college field: be conservative -> none
            return qs.none()

    def has_module_permission(self, request):
        if request.user.is_superuser:
            return True
        return request.user.is_staff and bool(self._user_college(request))

    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if not request.user.is_staff:
            return False
        user_college = self._user_college(request)
        if obj is None:
            return bool(user_college)
        if hasattr(obj, "college"):
            return getattr(obj, "college") == user_college
        return False

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if not request.user.is_staff:
            return False
        user_college = self._user_college(request)
        if obj is None:
            return bool(user_college)
        if hasattr(obj, "college"):
            return getattr(obj, "college") == user_college
        return False

    def has_add_permission(self, request):
        if request.user.is_superuser:
            return True
        return request.user.is_staff and bool(self._user_college(request))

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if not request.user.is_staff:
            return False
        if obj is None:
            return bool(self._user_college(request))
        if hasattr(obj, "college"):
            return getattr(obj, "college") == self._user_college(request)
        return False

    def save_model(self, request, obj, form, change):
        # when non-superuser creates/edits, ensure object.college set to user's college if applicable
        if not request.user.is_superuser:
            user_college = self._user_college(request)
            if user_college and hasattr(obj, "college"):
                setattr(obj, "college", user_college)
        super().save_model(request, obj, form, change)


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('username', 'email', 'user_type', 'college', 'is_staff', 'is_active')
    list_filter = ('user_type', 'is_staff', 'is_active', 'college')
    search_fields = ('username', 'email')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if not request.user.is_staff:
            return qs.none()
        user_college = getattr(request.user, "college", None)
        if not user_college:
            return qs.none()
        try:
            return qs.filter(college=user_college)
        except Exception:
            return qs.none()


@admin.register(College)
class CollegeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'created_at')
    readonly_fields = ('created_at',)

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(Department)
class DepartmentAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('name', 'short_code', 'college')
    search_fields = ('name', 'short_code')


@admin.register(Semester)
class SemesterAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('name', 'order', 'college')
    ordering = ('order',)


@admin.register(AdminHOD)
class AdminHODAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('admin', 'employee_id', 'college', 'department')


@admin.register(Staffs)
class StaffsAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('admin', 'employee_id', 'college', 'department')
    search_fields = ('admin__username', 'employee_id')


@admin.register(Students)
class StudentsAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('admin', 'student_id', 'roll_no', 'college', 'department', 'course', 'session_year')
    list_filter = ('department', 'course', 'session_year')
    search_fields = ('admin__username', 'student_id', 'roll_no')


@admin.register(Course)
class CourseAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('name', 'college')
    search_fields = ('name',)


@admin.register(SessionYear)
class SessionYearAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('session_start_year', 'session_end_year', 'college')


@admin.register(Attendance)
class AttendanceAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('course', 'session_year', 'attendance_date', 'college', 'created_at')
    list_filter = ('course', 'session_year', 'college')
    date_hierarchy = 'attendance_date'


@admin.register(AttendanceReport)
class AttendanceReportAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('student', 'attendance', 'status', 'college')
    list_filter = ('status', 'attendance__course')


@admin.register(LeaveReportStaff)
class LeaveReportStaffAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('staff', 'date', 'status')
    list_filter = ('status', 'date', 'staff__admin__username')


@admin.register(LeaveReportStudent)
class LeaveReportStudentAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('student', 'date', 'status')
    list_filter = ('status', 'date', 'student__admin__username')


@admin.register(FeedbackStaff)
class FeedbackStaffAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('staff', 'created_at', 'reply')


@admin.register(FeedbackStudent)
class FeedbackStudentAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('student', 'created_at', 'reply')


@admin.register(StudentResult)
class StudentResultAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('student', 'subject_name', 'marks', 'grade', 'college', 'created_at')
    list_filter = ('subject_name', 'college')
    search_fields = ('student__admin__username', 'subject_name')
