from django.db import models
from django.contrib.auth.models import AbstractUser


class College(models.Model):
    name = models.CharField(max_length=255, unique=True)
    code = models.CharField(max_length=64, unique=True)
    tagline = models.CharField(max_length=255, blank=True)
    logo = models.ImageField(upload_to='college_logo/', blank=True, null=True)
    hero_image = models.ImageField(upload_to='college_hero/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.code})"


class CustomUser(AbstractUser):
    STUDENT = 1
    STAFF = 2
    HOD = 3
    USER_TYPE_CHOICES = (
        (HOD, 'HOD'),
        (STAFF, 'Staff'),
        (STUDENT, 'Student'),
    )
    user_type = models.PositiveSmallIntegerField(choices=USER_TYPE_CHOICES, default=STUDENT)

    college = models.ForeignKey(College, null=True, blank=True, on_delete=models.SET_NULL, related_name='users')

    def __str__(self):
        return self.username


class Department(models.Model):
    name = models.CharField(max_length=150)
    short_code = models.CharField(max_length=20, blank=True)
    college = models.ForeignKey(College, null=True, blank=True, on_delete=models.CASCADE, related_name='departments')

    class Meta:
        unique_together = ('college', 'name')

    def __str__(self):
        return f"{self.name} — {self.college.code if self.college else 'NoCollege'}"


class Semester(models.Model):
    name = models.CharField(max_length=50)
    order = models.PositiveSmallIntegerField(default=1)
    college = models.ForeignKey(College, null=True, blank=True, on_delete=models.CASCADE, related_name='semesters')

    class Meta:
        unique_together = ('college', 'name')
        ordering = ('order',)

    def __str__(self):
        return f"{self.name} — {self.college.code if self.college else 'NoCollege'}"


class Course(models.Model):
    name = models.CharField(max_length=255)
    college = models.ForeignKey(College, null=True, blank=True, on_delete=models.CASCADE, related_name='courses')

    class Meta:
        unique_together = ('college', 'name')

    def __str__(self):
        return f"{self.name} — {self.college.code if self.college else 'NoCollege'}"


class SessionYear(models.Model):
    session_start_year = models.IntegerField()
    session_end_year = models.IntegerField()
    college = models.ForeignKey(College, null=True, blank=True, on_delete=models.CASCADE, related_name='session_years')

    class Meta:
        unique_together = ('college', 'session_start_year', 'session_end_year')

    def __str__(self):
        return f"{self.session_start_year}-{self.session_end_year} ({self.college.code if self.college else 'NoCollege'})"


class AdminHOD(models.Model):
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='hod_profile')
    college = models.ForeignKey(College, null=True, blank=True, on_delete=models.SET_NULL, related_name='hods')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='hods')
    employee_id = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"HOD: {self.admin.username}"


class Staffs(models.Model):
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='staff_profile')
    college = models.ForeignKey(College, null=True, blank=True, on_delete=models.SET_NULL, related_name='staffs')
    address = models.TextField(blank=True, null=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='staffs')
    employee_id = models.CharField(max_length=50, blank=True, null=True)
    phone = models.CharField(max_length=30, blank=True, null=True)
    profile_pic = models.ImageField(upload_to='staff_profile/', blank=True, null=True)

    def __str__(self):
        return f"Staff: {self.admin.username}"


class Students(models.Model):
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='student_profile')
    college = models.ForeignKey(College, null=True, blank=True, on_delete=models.SET_NULL, related_name='students')
    student_id = models.CharField(max_length=50, blank=True, null=True)
    roll_no = models.CharField(max_length=50, blank=True, null=True)
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    session_year = models.ForeignKey(SessionYear, on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    year = models.ForeignKey(Semester, on_delete=models.SET_NULL, null=True, blank=True, related_name='student_years')
    semester = models.ForeignKey(Semester, on_delete=models.SET_NULL, null=True, blank=True, related_name='student_semesters')
    address = models.TextField(blank=True, null=True)
    profile_pic = models.ImageField(upload_to='student_profile/', blank=True, null=True)
    phone = models.CharField(max_length=30, blank=True, null=True)

    def __str__(self):
        return f"Student: {self.admin.username} ({self.student_id or 'no-id'})"


class Attendance(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='attendances')
    session_year = models.ForeignKey(SessionYear, on_delete=models.CASCADE, related_name='attendances')
    attendance_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    college = models.ForeignKey(College, null=True, blank=True, on_delete=models.SET_NULL, related_name='attendances')

    class Meta:
        unique_together = ('course', 'session_year', 'attendance_date', 'college')

    def __str__(self):
        return f"{self.course.name} - {self.attendance_date}"


class AttendanceReport(models.Model):
    student = models.ForeignKey(Students, on_delete=models.CASCADE, related_name='attendance_reports')
    attendance = models.ForeignKey(Attendance, on_delete=models.CASCADE, related_name='reports')
    status = models.BooleanField(default=False)
    college = models.ForeignKey(College, null=True, blank=True, on_delete=models.SET_NULL, related_name='attendance_reports')

    def __str__(self):
        return f"{self.student.admin.username} - {self.attendance.attendance_date}"


class LeaveReportStaff(models.Model):
    staff = models.ForeignKey(Staffs, on_delete=models.CASCADE, related_name='leaves')
    date = models.DateField()
    message = models.TextField()
    status = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.staff.admin.username} - {self.date}"


class LeaveReportStudent(models.Model):
    student = models.ForeignKey(Students, on_delete=models.CASCADE, related_name='leaves')
    date = models.DateField()
    message = models.TextField()
    status = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.student.admin.username} - {self.date}"


class FeedbackStaff(models.Model):
    staff = models.ForeignKey(Staffs, on_delete=models.CASCADE, related_name='feedbacks')
    feedback = models.TextField()
    reply = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback from {self.staff.admin.username}"


class FeedbackStudent(models.Model):
    student = models.ForeignKey(Students, on_delete=models.CASCADE, related_name='feedbacks')
    feedback = models.TextField()
    reply = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback from {self.student.admin.username}"


class StudentResult(models.Model):
    student = models.ForeignKey(Students, on_delete=models.CASCADE, related_name='results')
    subject_name = models.CharField(max_length=255)
    marks = models.FloatField()
    grade = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)
    college = models.ForeignKey(College, null=True, blank=True, on_delete=models.SET_NULL, related_name='results')

    def __str__(self):
        return f"{self.student.admin.username} - {self.subject_name} ({self.grade})"
