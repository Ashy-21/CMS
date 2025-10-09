from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages
from django.urls import reverse
from django.http import HttpResponseRedirect

from .forms import (
    LeaveForm, StudentLeaveForm, ResultForm, ResultEntryForm,
    StudentFeedbackForm, ApproveLeaveForm,
    StaffRegistrationForm, StudentRegistrationForm, HodRegistrationForm
)
from .models import (
    Attendance, AttendanceReport, LeaveReportStaff, LeaveReportStudent,
    FeedbackStaff, FeedbackStudent, StudentResult, Department, Semester,
    AdminHOD, Staffs, Students, CustomUser, Course, SessionYear, College
)

User = get_user_model()


def home(request):
    """
    Home page behaviour:
    - If no college selected: show dropdown + create-college form (create includes creating a college admin)
    - If a college is selected: show college landing with login/register links
    """
    # selected college from session (if any)
    selected_college = None
    college_id = request.session.get('selected_college_id')
    if college_id:
        selected_college = College.objects.filter(id=college_id).first()

    # Always provide list of colleges so template can show a selector when colleges exist
    colleges = College.objects.all()

    if request.method == "POST":
        # selecting an existing college
        if 'select_college' in request.POST:
            college_id = request.POST.get('college_id')
            if college_id:
                request.session['selected_college_id'] = int(college_id)
                messages.success(request, "Selected college updated.")
            return redirect('student_management_app:home')

        # create new college + admin
        if 'create_college' in request.POST:
            name = request.POST.get('college_name', '').strip()
            code = request.POST.get('college_code', '').strip()
            tagline = request.POST.get('college_tagline', '').strip()

            admin_username = request.POST.get('admin_username', '').strip()
            admin_email = request.POST.get('admin_email', '').strip()
            admin_password = request.POST.get('admin_password', '').strip()

            if not (name and code and admin_username and admin_email and admin_password):
                messages.error(request, "Please provide college name, code and admin credentials.")
                return redirect('student_management_app:home')

            if College.objects.filter(code__iexact=code).exists():
                messages.error(request, "College code already exists. Choose a different code.")
                return redirect('student_management_app:home')

            if User.objects.filter(username=admin_username).exists() or User.objects.filter(email=admin_email).exists():
                messages.error(request, "Admin username/email already in use. Choose different credentials.")
                return redirect('student_management_app:home')

            college = College.objects.create(name=name, code=code, tagline=tagline)

            # create college admin user (staff but we set user_type to HOD so they can access admin_home dashboard)
            admin_user = User.objects.create_user(
                username=admin_username,
                email=admin_email,
                password=admin_password,
            )
            admin_user.is_staff = True
            admin_user.is_active = True
            admin_user.is_superuser = False
            # mark as HOD (so admin_home view recognizes them)
            try:
                admin_user.user_type = CustomUser.HOD
            except Exception:
                # safety if CustomUser isn't used for some reason - ignore
                pass
            admin_user.college = college
            admin_user.save()

            # create a Staffs record for the admin so admin can edit college objects (optional)
            Staffs.objects.create(admin=admin_user, college=college, employee_id=f"ADM-{college.code}")

            request.session['selected_college_id'] = college.id
            messages.success(request, f"College '{college.name}' created and admin '{admin_username}' created.")
            return redirect('student_management_app:home')

    # GET (or after POST redirect) — render with colleges + selected_college context
    return render(request, 'student_management_app/home.html', {
        'colleges': colleges,
        'college_profile': selected_college,   # keep name used elsewhere in templates
        'college': selected_college,           # compatibility with templates that use 'college'
    })



def loginPage(request):
    """Show login page"""
    return render(request, 'student_management_app/login_page.html')


def doLogin(request):
    """Authenticate and redirect based on user_type"""
    if request.method != "POST":
        return redirect('student_management_app:login')
    username = request.POST.get('username')
    password = request.POST.get('password')
    user = authenticate(request, username=username, password=password)
    if user is not None:
        if not user.is_active:
            messages.error(request, "Account disabled. Contact admin.")
            return redirect('student_management_app:login')

        login(request, user)
        # Redirect according to user_type. If superuser, send to admin_home
        if user.is_superuser:
            return redirect('student_management_app:admin_home')
        if getattr(user, "user_type", None) == CustomUser.HOD:
            return redirect('student_management_app:admin_home')
        if getattr(user, "user_type", None) == CustomUser.STAFF:
            return redirect('student_management_app:staff_home')
        if getattr(user, "user_type", None) == CustomUser.STUDENT:
            return redirect('student_management_app:student_home')
        # fallback: staff -> staff_home, else home
        if user.is_staff:
            return redirect('student_management_app:staff_home')
        return redirect('student_management_app:home')

    messages.error(request, 'Invalid credentials')
    return redirect('student_management_app:login')


def logout_user(request):
    logout(request)
    return redirect('student_management_app:login')


def registration(request):
    """
    Registration page for student/staff/hod. Uses selected college from session if present.
    """
    # selected college from session (if any)
    selected_college = None
    college_id = request.session.get('selected_college_id')
    if college_id:
        selected_college = College.objects.filter(id=college_id).first()

    colleges = College.objects.all()

    departments = Department.objects.filter(college=selected_college) if selected_college else Department.objects.none()
    semesters = Semester.objects.filter(college=selected_college) if selected_college else Semester.objects.none()

    if request.method == "POST":
        posted_college_id = request.POST.get('college_id') or college_id
        if not posted_college_id:
            messages.error(request, "Please select a college (from homepage or this form) before registering.")
            return redirect('student_management_app:registration')

        college_obj = College.objects.filter(id=posted_college_id).first()
        if not college_obj:
            messages.error(request, "Selected college not found.")
            return redirect('student_management_app:registration')

        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        # default to STUDENT if missing or non-int
        try:
            user_type = int(request.POST.get('user_type', CustomUser.STUDENT))
        except Exception:
            user_type = CustomUser.STUDENT

        if not (username and email and password):
            messages.error(request, "Please provide username, email and password.")
            return redirect('student_management_app:registration')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken. Choose another.")
            return redirect('student_management_app:registration')
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already taken. Choose another.")
            return redirect('student_management_app:registration')

        # Student
        if user_type == CustomUser.STUDENT:
            student_id = request.POST.get('student_id', '').strip()
            roll_no = request.POST.get('roll_no', '').strip()
            department_id = request.POST.get('department')
            semester_id = request.POST.get('semester')
            session_id = request.POST.get('session_id')
            course_id = request.POST.get('course')

            if not student_id:
                messages.error(request, "Student ID is required.")
                return redirect('student_management_app:registration')

            if Students.objects.filter(student_id=student_id, college=college_obj).exists():
                messages.error(request, "Student ID already used in this college.")
                return redirect('student_management_app:registration')

            user = User.objects.create_user(username=username, email=email, password=password)
            user.user_type = CustomUser.STUDENT
            user.college = college_obj
            user.is_active = True
            user.save()

            dept = Department.objects.filter(id=department_id, college=college_obj).first() if department_id else None
            sem = Semester.objects.filter(id=semester_id, college=college_obj).first() if semester_id else None
            sess = SessionYear.objects.filter(id=session_id, college=college_obj).first() if session_id else None
            course = Course.objects.filter(id=course_id, college=college_obj).first() if course_id else None

            Students.objects.create(
                admin=user,
                student_id=student_id,
                roll_no=roll_no,
                department=dept,
                year=sem,
                semester=sem,
                session_year=sess,
                course=course,
                college=college_obj
            )
            messages.success(request, "Student registered successfully. Please login.")
            return redirect('student_management_app:login')

        # Staff
        if user_type == CustomUser.STAFF:
            employee_id = request.POST.get('employee_id', '').strip()
            department_id = request.POST.get('department')

            if not employee_id:
                messages.error(request, "Employee ID is required.")
                return redirect('student_management_app:registration')

            if Staffs.objects.filter(employee_id=employee_id, college=college_obj).exists():
                messages.error(request, "Employee ID already used in this college.")
                return redirect('student_management_app:registration')

            user = User.objects.create_user(username=username, email=email, password=password)
            user.user_type = CustomUser.STAFF
            user.college = college_obj
            user.is_staff = True
            user.is_active = True
            user.save()

            dept = Department.objects.filter(id=department_id, college=college_obj).first() if department_id else None
            Staffs.objects.create(admin=user, employee_id=employee_id, department=dept, college=college_obj)
            messages.success(request, "Staff registered successfully. Please login.")
            return redirect('student_management_app:login')

        # HOD
        if user_type == CustomUser.HOD:
            hod_id = request.POST.get('hod_id', '').strip()
            department_id = request.POST.get('department')

            if not hod_id:
                messages.error(request, "HOD ID is required.")
                return redirect('student_management_app:registration')

            user = User.objects.create_user(username=username, email=email, password=password)
            user.user_type = CustomUser.HOD
            user.college = college_obj
            user.is_staff = True
            user.is_active = True
            user.save()

            dept = Department.objects.filter(id=department_id, college=college_obj).first() if department_id else None
            AdminHOD.objects.create(admin=user, department=dept, college=college_obj, employee_id=hod_id)
            messages.success(request, "HOD registered successfully. Please login.")
            return redirect('student_management_app:login')

        messages.error(request, "Invalid role selected.")
        return redirect('student_management_app:registration')

    # include User (CustomUser) in context so templates can reference constants if needed
    return render(request, 'student_management_app/registration.html', {
        'college': selected_college,
        'colleges': colleges,
        'departments': departments,
        'semesters': semesters,
        'user_model': CustomUser,
    })


# --- dashboards ---

def admin_home(request):
    """
    HOD / College admin dashboard. Superuser sees site-wide summary.
    """
    if not request.user.is_authenticated:
        messages.error(request, 'Login required')
        return redirect('student_management_app:login')

    # Allow superuser or HOD users to view this dashboard
    if not (request.user.is_superuser or getattr(request.user, "user_type", None) == CustomUser.HOD):
        messages.error(request, 'Unauthorized')
        return redirect('student_management_app:login')

    college = request.user.college if not request.user.is_superuser else None

    if request.user.is_superuser:
        total_students = Students.objects.count()
        total_staffs = Staffs.objects.count()
        total_courses = Course.objects.count()
    else:
        total_students = Students.objects.filter(college=college).count()
        total_staffs = Staffs.objects.filter(college=college).count()
        total_courses = Course.objects.filter(college=college).count()

    pending_staff_leaves = LeaveReportStaff.objects.filter(staff__college=college, status=False) if college else LeaveReportStaff.objects.filter(status=False)
    pending_student_leaves = LeaveReportStudent.objects.filter(student__college=college, status=False) if college else LeaveReportStudent.objects.filter(status=False)

    context = {
        'college_profile': college,
        'total_students': total_students,
        'total_staffs': total_staffs,
        'total_courses': total_courses,
        'pending_staff_leaves': pending_staff_leaves,
        'pending_student_leaves': pending_student_leaves,
    }
    return render(request, 'student_management_app/dashboard_admin.html', context)


def staff_home(request):
    if not request.user.is_authenticated or getattr(request.user, "user_type", None) != CustomUser.STAFF:
        messages.error(request, 'Unauthorized')
        return redirect('student_management_app:login')

    try:
        staff_profile = request.user.staff_profile
    except Staffs.DoesNotExist:
        messages.error(request, 'Staff profile not found.')
        return redirect('student_management_app:login')

    my_leaves = LeaveReportStaff.objects.filter(staff=staff_profile).order_by('-date')

    context = {
        'staff_profile': staff_profile,
        'college_profile': request.user.college,
        'my_leaves': my_leaves,
    }
    return render(request, 'student_management_app/dashboard_staff.html', context)


def student_home(request):
    if not request.user.is_authenticated or getattr(request.user, "user_type", None) != CustomUser.STUDENT:
        messages.error(request, 'Unauthorized')
        return redirect('student_management_app:login')

    try:
        student_profile = request.user.student_profile
    except Students.DoesNotExist:
        messages.error(request, 'Student profile not found.')
        return redirect('student_management_app:login')

    results = StudentResult.objects.filter(student=student_profile)
    reports = AttendanceReport.objects.filter(student=student_profile).select_related('attendance')
    present = reports.filter(status=True).count()
    total_attendance = reports.count()
    attendance_percent = round((present / total_attendance * 100), 1) if total_attendance else 0

    context = {
        'student_profile': student_profile,
        'college_profile': request.user.college,
        'results': results,
        'attendance_percent': attendance_percent,
        'present': present,
        'total_attendance': total_attendance,
    }
    return render(request, 'student_management_app/dashboard_student.html', context)


# --- Staff: attendance page ---
def staff_attendance(request):
    if not request.user.is_authenticated or getattr(request.user, "user_type", None) != CustomUser.STAFF:
        messages.error(request, 'Unauthorized')
        return redirect('student_management_app:login')

    # limit courses/sessions to staff.college
    college = request.user.college
    courses = Course.objects.filter(college=college) if college else Course.objects.none()
    sessions = SessionYear.objects.filter(college=college) if college else SessionYear.objects.none()

    if request.method == "POST":
        course_id = request.POST.get('course')
        session_id = request.POST.get('session')
        attendance_date = request.POST.get('attendance_date')
        if not (course_id and session_id and attendance_date):
            messages.error(request, "Please provide course, session, and date.")
            return redirect('student_management_app:staff_attendance')

        attendance_obj, created = Attendance.objects.get_or_create(
            course_id=course_id,
            session_year_id=session_id,
            attendance_date=attendance_date,
            defaults={"college": college}
        )
        messages.success(request, "Attendance record created." if created else "Attendance already exists (opened).")
        return redirect('student_management_app:staff_attendance')

    return render(request, 'student_management_app/staff_attendance.html', {'courses': courses, 'sessions': sessions})


# --- Staff leave ---
def staff_leave(request):
    if not request.user.is_authenticated or getattr(request.user, "user_type", None) != CustomUser.STAFF:
        messages.error(request, 'Unauthorized')
        return redirect('student_management_app:login')

    try:
        staff = request.user.staff_profile
    except Staffs.DoesNotExist:
        messages.error(request, "Staff profile not found.")
        return redirect('student_management_app:staff_home')

    if request.method == "POST":
        form = LeaveForm(request.POST)
        if form.is_valid():
            leave = form.save(commit=False)
            leave.staff = staff
            leave.save()
            messages.success(request, "Leave applied successfully.")
            return redirect('student_management_app:staff_leave')
    else:
        form = LeaveForm()

    leaves = LeaveReportStaff.objects.filter(staff=staff)
    return render(request, 'student_management_app/staff_leave.html', {'form': form, 'leaves': leaves})


# --- Student leave ---
def student_leave(request):
    if not request.user.is_authenticated or getattr(request.user, "user_type", None) != CustomUser.STUDENT:
        messages.error(request, 'Unauthorized')
        return redirect('student_management_app:login')

    try:
        student = request.user.student_profile
    except Students.DoesNotExist:
        messages.error(request, "Student profile not found.")
        return redirect('student_management_app:student_home')

    if request.method == "POST":
        form = StudentLeaveForm(request.POST)
        if form.is_valid():
            leave = form.save(commit=False)
            leave.student = student
            leave.save()
            messages.success(request, "Leave request sent.")
            return redirect('student_management_app:student_leave')
    else:
        form = StudentLeaveForm()

    leaves = LeaveReportStudent.objects.filter(student=student)
    return render(request, 'student_management_app/student_leave.html', {'form': form, 'leaves': leaves})


# --- Student results listing ---
def student_results(request):
    if not request.user.is_authenticated or getattr(request.user, "user_type", None) != CustomUser.STUDENT:
        messages.error(request, 'Unauthorized')
        return redirect('student_management_app:login')
    try:
        student = request.user.student_profile
    except Students.DoesNotExist:
        messages.error(request, "Student profile not found.")
        return redirect('student_management_app:student_home')

    results = StudentResult.objects.filter(student=student)
    return render(request, 'student_management_app/student_results.html', {'results': results})


# --- HOD leave requests ---
def hod_leave_requests(request):
    if not request.user.is_authenticated or getattr(request.user, "user_type", None) != CustomUser.HOD:
        messages.error(request, "Unauthorized")
        return redirect('student_management_app:login')

    college = request.user.college
    pending_staff_leaves = LeaveReportStaff.objects.filter(staff__college=college, status=False)
    pending_student_leaves = LeaveReportStudent.objects.filter(student__college=college, status=False)
    return render(request, 'student_management_app/hod_leave_requests.html', {
        'pending_staff_leaves': pending_staff_leaves,
        'pending_student_leaves': pending_student_leaves,
    })


def hod_process_staff_leave(request, leave_id):
    if not request.user.is_authenticated or getattr(request.user, "user_type", None) != CustomUser.HOD:
        messages.error(request, "Unauthorized")
        return redirect('student_management_app:login')
    leave = get_object_or_404(LeaveReportStaff, id=leave_id)
    if request.method == "POST":
        decision = request.POST.get('decision')
        if decision == 'approve':
            leave.status = True
            leave.save()
            messages.success(request, "Leave approved.")
        else:
            leave.message = f"[REJECTED] {leave.message}"
            leave.save()
            messages.success(request, "Leave rejected.")
        return redirect('student_management_app:hod_leave_requests')
    form = ApproveLeaveForm()
    return render(request, 'student_management_app/hod_process_leave.html', {'leave': leave, 'form': form})


def hod_process_student_leave(request, leave_id):
    if not request.user.is_authenticated or getattr(request.user, "user_type", None) != CustomUser.HOD:
        messages.error(request, "Unauthorized")
        return redirect('student_management_app:login')
    leave = get_object_or_404(LeaveReportStudent, id=leave_id)
    if request.method == "POST":
        decision = request.POST.get('decision')
        if decision == 'approve':
            leave.status = True
            leave.save()
            messages.success(request, "Student leave approved.")
        else:
            leave.message = f"[REJECTED] {leave.message}"
            leave.save()
            messages.success(request, "Student leave rejected.")
        return redirect('student_management_app:hod_leave_requests')
    form = ApproveLeaveForm()
    return render(request, 'student_management_app/hod_process_leave.html', {'leave': leave, 'form': form})


# --- Staff enter result ---
def staff_enter_result(request):
    if not request.user.is_authenticated or getattr(request.user, "user_type", None) != CustomUser.STAFF:
        messages.error(request, 'Unauthorized')
        return redirect('student_management_app:login')

    if request.method == "POST":
        form = ResultEntryForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            # attach college from staff user if the model has college
            if hasattr(obj, 'college') and getattr(request.user, "college", None):
                obj.college = request.user.college
            obj.save()
            messages.success(request, "Result saved.")
            return redirect('student_management_app:staff_enter_result')
    else:
        form = ResultEntryForm()
    return render(request, 'student_management_app/staff_enter_result.html', {'form': form})


# --- Student feedback ---
def student_feedback(request):
    if not request.user.is_authenticated or getattr(request.user, "user_type", None) != CustomUser.STUDENT:
        messages.error(request, 'Unauthorized')
        return redirect('student_management_app:login')

    try:
        student = request.user.student_profile
    except Students.DoesNotExist:
        messages.error(request, "Student profile missing.")
        return redirect('student_management_app:student_home')

    if request.method == "POST":
        form = StudentFeedbackForm(request.POST)
        if form.is_valid():
            f = form.save(commit=False)
            f.student = student
            f.save()
            messages.success(request, "Feedback submitted.")
            return redirect('student_management_app:student_feedback')
    else:
        form = StudentFeedbackForm()

    feedbacks = FeedbackStudent.objects.filter(student=student).order_by('-created_at')
    return render(request, 'student_management_app/student_feedback.html', {'form': form, 'feedbacks': feedbacks})


# --- Student attendance history ---
def student_attendance_history(request):
    if not request.user.is_authenticated or getattr(request.user, "user_type", None) != CustomUser.STUDENT:
        messages.error(request, 'Unauthorized')
        return redirect('student_management_app:login')

    try:
        student = request.user.student_profile
    except Students.DoesNotExist:
        messages.error(request, 'Student profile missing.')
        return redirect('student_management_app:student_home')

    reports = AttendanceReport.objects.filter(student=student).select_related('attendance__course')
    stats = {}
    for rep in reports:
        course_name = rep.attendance.course.name
        if course_name not in stats:
            stats[course_name] = {'present': 0, 'total': 0}
        stats[course_name]['total'] += 1
        if rep.status:
            stats[course_name]['present'] += 1

    for course_name, v in stats.items():
        total = v['total']
        present = v['present']
        v['percent'] = round((present / total * 100), 1) if total else 0

    return render(request, 'student_management_app/student_attendance_history.html', {'stats': stats})
