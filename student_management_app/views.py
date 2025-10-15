# student_management_app/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.db.models import Q, Count, F
import json
from django.utils.safestring import mark_safe
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
    selected_college = None
    college_id = request.session.get('selected_college_id')
    if college_id:
        selected_college = College.objects.filter(id=college_id).first()

    colleges = College.objects.all()

    if request.method == "POST":
        if 'select_college' in request.POST:
            college_id = request.POST.get('college_id')
            if college_id:
                request.session['selected_college_id'] = int(college_id)
                messages.success(request, "Selected college updated.")
            return redirect('student_management_app:home')

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

            admin_user = User.objects.create_user(
                username=admin_username,
                email=admin_email,
                password=admin_password,
            )
            admin_user.is_staff = True
            admin_user.is_active = True
            admin_user.is_superuser = False
            try:
                admin_user.user_type = CustomUser.HOD
            except Exception:
                pass
            admin_user.college = college
            admin_user.save()

            Staffs.objects.create(admin=admin_user, college=college, employee_id=f"ADM-{college.code}")

            request.session['selected_college_id'] = college.id
            messages.success(request, f"College '{college.name}' created and admin '{admin_username}' created.")
            return redirect('student_management_app:home')

    return render(request, 'student_management_app/home.html', {
        'colleges': colleges,
        'college_profile': selected_college,
        'college': selected_college,
    })


def loginPage(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if not user.is_active:
                messages.error(request, "Account disabled. Contact admin.")
                return redirect('student_management_app:login')

            login(request, user)
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

    # GET: show the page
    return render(request, 'student_management_app/login_page.html')


def doLogin(request):
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
        if user.is_superuser:
            return redirect('student_management_app:admin_home')
        if getattr(user, "user_type", None) == CustomUser.HOD:
            return redirect('student_management_app:admin_home')
        if getattr(user, "user_type", None) == CustomUser.STAFF:
            return redirect('student_management_app:staff_home')
        if getattr(user, "user_type", None) == CustomUser.STUDENT:
            return redirect('student_management_app:student_home')
        if user.is_staff:
            return redirect('student_management_app:staff_home')
        return redirect('student_management_app:home')

    messages.error(request, 'Invalid credentials')
    return redirect('student_management_app:login')


def logout_user(request):
    logout(request)
    return redirect('student_management_app:login')


def registration(request):
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

    return render(request, 'student_management_app/registration.html', {
        'college': selected_college,
        'colleges': colleges,
        'departments': departments,
        'semesters': semesters,
        'user_model': CustomUser,
    })

def admin_home(request):
    if not request.user.is_authenticated:
        messages.error(request, 'Login required')
        return redirect('student_management_app:login')

    if not (request.user.is_superuser or getattr(request.user, "user_type", None) == CustomUser.HOD):
        messages.error(request, 'Unauthorized')
        return redirect('student_management_app:login')

    college = request.user.college if not request.user.is_superuser else None

    if request.user.is_superuser:
        total_students = Students.objects.count()
        total_staffs = Staffs.objects.count()
        total_courses = Course.objects.count()
        students_qs = Students.objects.select_related('admin', 'department', 'course')
        staffs_qs = Staffs.objects.select_related('admin', 'department')
    else:
        total_students = Students.objects.filter(college=college).count()
        total_staffs = Staffs.objects.filter(college=college).count()
        total_courses = Course.objects.filter(college=college).count()
        students_qs = Students.objects.filter(college=college).select_related('admin', 'department', 'course')
        staffs_qs = Staffs.objects.filter(college=college).select_related('admin', 'department')

    pending_staff_leaves = LeaveReportStaff.objects.filter(staff__college=college, status=False) if college else LeaveReportStaff.objects.filter(status=False)
    pending_student_leaves = LeaveReportStudent.objects.filter(student__college=college, status=False) if college else LeaveReportStudent.objects.filter(status=False)

    students_list = students_qs.order_by('student_id')[:200]
    staffs_list = staffs_qs.order_by('employee_id')[:200]

    students_by_dept_qs = students_qs.values(dept_name=F('department__name')).annotate(count=Count('id')).order_by('-count')
    labels_students = []
    values_students = []
    for row in students_by_dept_qs:
        label = row.get('dept_name') or "Unknown"
        labels_students.append(label)
        values_students.append(row.get('count', 0))

    staffs_by_dept_qs = staffs_qs.values(dept_name=F('department__name')).annotate(count=Count('id')).order_by('-count')
    labels_staffs = []
    values_staffs = []
    for row in staffs_by_dept_qs:
        label = row.get('dept_name') or "Unknown"
        labels_staffs.append(label)
        values_staffs.append(row.get('count', 0))

    context = {
        'college_profile': college,
        'total_students': total_students,
        'total_staffs': total_staffs,
        'total_courses': total_courses,
        'pending_staff_leaves': pending_staff_leaves,
        'pending_student_leaves': pending_student_leaves,
        'students_list': students_list,
        'staffs_list': staffs_list,
        'students_chart_labels': mark_safe(json.dumps(labels_students)),
        'students_chart_values': mark_safe(json.dumps(values_students)),
        'staffs_chart_labels': mark_safe(json.dumps(labels_staffs)),
        'staffs_chart_values': mark_safe(json.dumps(values_staffs)),
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

    college = request.user.college
    students_preview = Students.objects.filter(college=college).select_related('admin', 'department', 'course', 'semester')[:50] if college else Students.objects.none()
    courses = Course.objects.filter(college=college) if college else Course.objects.none()
    semesters = Semester.objects.filter(college=college) if college else Semester.objects.none()

    context = {
        'staff_profile': staff_profile,
        'college_profile': request.user.college,
        'my_leaves': my_leaves,
        'students_preview': students_preview,
        'courses': courses,
        'semesters': semesters,
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

def staff_attendance(request):
    if not request.user.is_authenticated or getattr(request.user, "user_type", None) != CustomUser.STAFF:
        messages.error(request, 'Unauthorized')
        return redirect('student_management_app:login')

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

def student_results(request):
    if not request.user.is_authenticated or getattr(request.user, "user_type", None) != CustomUser.STUDENT:
        messages.error(request, 'Unauthorized')
        return redirect('student_management_app:login')
    try:
        student = request.user.student_profile
    except Students.DoesNotExist:
        messages.error(request, 'Student profile not found.')
        return redirect('student_management_app:student_home')

    results = StudentResult.objects.filter(student=student)
    return render(request, 'student_management_app/student_results.html', {'results': results})

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

def staff_enter_result(request):
    if not request.user.is_authenticated or getattr(request.user, "user_type", None) != CustomUser.STAFF:
        messages.error(request, 'Unauthorized')
        return redirect('student_management_app:login')

    if request.method == "POST":
        form = ResultEntryForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            if hasattr(obj, 'college') and getattr(request.user, "college", None):
                obj.college = request.user.college
            obj.save()
            messages.success(request, "Result saved.")
            return redirect('student_management_app:staff_enter_result')
    else:
        form = ResultEntryForm()
    return render(request, 'student_management_app/staff_enter_result.html', {'form': form})

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

def student_subject_detail(request, student_id, result_id):
    if not request.user.is_authenticated or getattr(request.user, "user_type", None) != CustomUser.STUDENT:
        messages.error(request, 'Unauthorized')
        return redirect('student_management_app:login')

    try:
        student_profile = request.user.student_profile
    except Students.DoesNotExist:
        messages.error(request, 'Student profile missing.')
        return redirect('student_management_app:student_home')

    if student_profile.id != student_id:
        messages.error(request, 'Unauthorized access to student data.')
        return redirect('student_management_app:student_home')

    result = StudentResult.objects.filter(id=result_id, student=student_profile).first()
    if not result:
        messages.error(request, 'Result not found.')
        return redirect('student_management_app:student_home')

    return render(request, 'student_management_app/student_subject_detail.html', {
        'student_profile': student_profile,
        'result': result,
    })


def api_student_subject_data(request, student_id, result_id):
    if not request.user.is_authenticated or getattr(request.user, "user_type", None) != CustomUser.STUDENT:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        student_profile = request.user.student_profile
    except Students.DoesNotExist:
        return JsonResponse({'error': 'Student profile missing'}, status=404)

    if student_profile.id != student_id:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    result = StudentResult.objects.filter(id=result_id, student=student_profile).first()
    if not result:
        return JsonResponse({'error': 'Result not found'}, status=404)

    marks = {
        'subject': getattr(result, 'subject_name', str(getattr(result, 'subject', 'Unknown'))),
        'marks': float(result.marks) if getattr(result, 'marks', None) is not None else None,
        'grade': getattr(result, 'grade', None),
    }

    reports = AttendanceReport.objects.filter(student=student_profile).select_related('attendance__course')
    attendance_by_course = {}
    for r in reports:
        course_name = r.attendance.course.name if r.attendance and getattr(r.attendance, 'course', None) else 'Unknown'
        if course_name not in attendance_by_course:
            attendance_by_course[course_name] = {'present': 0, 'total': 0}
        attendance_by_course[course_name]['total'] += 1
        if r.status:
            attendance_by_course[course_name]['present'] += 1

    attendance_list = []
    for course_name, v in attendance_by_course.items():
        total = v['total']
        present = v['present']
        percent = round((present / total * 100), 1) if total else 0
        attendance_list.append({
            'course': course_name,
            'present': present,
            'total': total,
            'percent': percent,
        })

    return JsonResponse({
        'marks': marks,
        'attendance': attendance_list,
    })

def staff_student_list(request):
    if not request.user.is_authenticated or getattr(request.user, "user_type", None) != CustomUser.STAFF:
        messages.error(request, 'Unauthorized')
        return redirect('student_management_app:login')

    college = request.user.college
    courses = Course.objects.filter(college=college) if college else Course.objects.none()
    semesters = Semester.objects.filter(college=college) if college else Semester.objects.none()

    students = Students.objects.filter(college=college) if college else Students.objects.none()

    selected_course_id = request.GET.get('course')
    selected_sem_id = request.GET.get('semester')

    if selected_course_id:
        students = students.filter(course_id=selected_course_id)
    if selected_sem_id:
        students = students.filter(semester_id=selected_sem_id)

    return render(request, 'student_management_app/staff_student_list.html', {
        'students': students,
        'courses': courses,
        'semesters': semesters,
        'selected_course_id': selected_course_id,
        'selected_semester_id': selected_sem_id,
    })


@require_POST
def staff_edit_attendance(request, attendance_report_id):
    if not request.user.is_authenticated or getattr(request.user, "user_type", None) != CustomUser.STAFF:
        return HttpResponseForbidden("Unauthorized")

    ar = get_object_or_404(AttendanceReport, id=attendance_report_id)
    if request.user.college and getattr(ar, 'college', None) != request.user.college:
        return HttpResponseForbidden("Not allowed")

    new_status = request.POST.get('status')
    ar.status = True if new_status == '1' or new_status == 'true' or new_status == 'on' else False
    ar.save()
    return JsonResponse({'ok': True, 'status': ar.status})


@require_POST
def staff_edit_result(request, result_id):
    if not request.user.is_authenticated or getattr(request.user, "user_type", None) != CustomUser.STAFF:
        return HttpResponseForbidden("Unauthorized")

    res = get_object_or_404(StudentResult, id=result_id)
    if request.user.college and getattr(res, 'college', None) != request.user.college:
        return HttpResponseForbidden("Not allowed")

    marks = request.POST.get('marks')
    grade = request.POST.get('grade')
    try:
        if marks is not None and marks != '':
            res.marks = float(marks)
        if grade is not None:
            res.grade = grade
        res.save()
        return JsonResponse({'ok': True, 'marks': res.marks, 'grade': res.grade})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
