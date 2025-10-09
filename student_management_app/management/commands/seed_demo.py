from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

from student_management_app.models import (
    College, Department, Semester, Course, SessionYear,
    CustomUser, Staffs, AdminHOD, Students, Attendance, AttendanceReport, StudentResult
)

User = get_user_model()

class Command(BaseCommand):
    help = "Seed demo colleges, users and minimal data for testing"

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Starting demo seeding..."))

        # Demo configuration for two colleges
        demo_colleges = [
            {
                "name": "Demo College A",
                "code": "DEMA",
                "tagline": "Learning for tomorrow - A",
                "admin_username": "admin_dema",
                "admin_email": "admin_dema@example.com",
                "admin_password": "Password123!"
            },
            {
                "name": "Demo College B",
                "code": "DEMB",
                "tagline": "Learning for tomorrow - B",
                "admin_username": "admin_demb",
                "admin_email": "admin_demb@example.com",
                "admin_password": "Password123!"
            }
        ]

        for cfg in demo_colleges:
            college, created = College.objects.get_or_create(code=cfg["code"], defaults={
                "name": cfg["name"],
                "tagline": cfg.get("tagline", ""),
            })
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created college: {college.name}"))
            else:
                self.stdout.write(self.style.WARNING(f"College exists: {college.name}"))

            # Create or get college-admin user (we mark them HOD so they can access admin_home)
            admin_user, ucreated = User.objects.get_or_create(username=cfg["admin_username"], defaults={
                "email": cfg["admin_email"],
            })
            if ucreated:
                admin_user.set_password(cfg["admin_password"])
                admin_user.is_staff = True
                admin_user.is_active = True
                admin_user.is_superuser = False
                try:
                    admin_user.user_type = CustomUser.HOD
                except Exception:
                    pass
                admin_user.college = college
                admin_user.save()
                self.stdout.write(self.style.SUCCESS(f"Created college admin user: {admin_user.username}"))
            else:
                # ensure user is staff and linked
                admin_user.is_staff = True
                admin_user.college = college
                try:
                    admin_user.user_type = CustomUser.HOD
                except Exception:
                    pass
                admin_user.save()
                self.stdout.write(self.style.WARNING(f"College admin existed, updated: {admin_user.username}"))

            # create a couple of Departments for this college
            dept_names = ["Computer Science", "Electronics"]
            departments = []
            for dname in dept_names:
                dept, _ = Department.objects.get_or_create(name=dname, college=college, defaults={
                    "short_code": (dname[:4] + college.code).upper()[:10]
                })
                departments.append(dept)

            # create semesters for this college
            sem1, _ = Semester.objects.get_or_create(name="Semester 1", college=college, defaults={"order": 1})
            sem2, _ = Semester.objects.get_or_create(name="Semester 2", college=college, defaults={"order": 2})

            # create courses for this college
            course_cs, _ = Course.objects.get_or_create(name=f"B.Tech CSE ({college.code})", college=college)
            course_ec, _ = Course.objects.get_or_create(name=f"B.Tech ECE ({college.code})", college=college)

            # create a session year for this college
            sy, _ = SessionYear.objects.get_or_create(session_start_year=2024, session_end_year=2025, college=college)

            # create staff users
            staff_users = []
            for i in range(1, 3):
                uname = f"staff_{college.code.lower()}_{i}"
                email = f"{uname}@example.com"
                user, created_u = User.objects.get_or_create(username=uname, defaults={
                    "email": email,
                })
                if created_u:
                    user.set_password("StaffPass123!")
                user.is_staff = True
                try:
                    user.user_type = CustomUser.STAFF
                except Exception:
                    pass
                user.college = college
                user.is_active = True
                user.save()

                staff_obj, _ = Staffs.objects.get_or_create(admin=user, defaults={
                    "address": f"Address for {uname}",
                    "college": college,
                    "department": departments[0] if departments else None,
                    "employee_id": f"STF-{college.code}-{i}"
                })
                staff_users.append(staff_obj)

            # create HOD user
            hod_username = f"hod_{college.code.lower()}"
            hod_user, hcreated = User.objects.get_or_create(username=hod_username, defaults={
                "email": f"{hod_username}@example.com",
            })
            if hcreated:
                hod_user.set_password("HodPass123!")
            hod_user.is_staff = True
            try:
                hod_user.user_type = CustomUser.HOD
            except Exception:
                pass
            hod_user.college = college
            hod_user.is_active = True
            hod_user.save()
            AdminHOD.objects.get_or_create(admin=hod_user, defaults={"college": college, "department": departments[0] if departments else None})

            # create students
            students_objs = []
            for i in range(1, 4):
                suname = f"student_{college.code.lower()}_{i}"
                semail = f"{suname}@example.com"
                suser, sucreated = User.objects.get_or_create(username=suname, defaults={
                    "email": semail,
                })
                if sucreated:
                    suser.set_password("Student123!")
                try:
                    suser.user_type = CustomUser.STUDENT
                except Exception:
                    pass
                suser.college = college
                suser.is_active = True
                suser.save()

                student_obj, _ = Students.objects.get_or_create(admin=suser, defaults={
                    "student_id": f"S{college.code}{i:03d}",
                    "roll_no": f"R{college.code}{i:03d}",
                    "college": college,
                    "course": course_cs,
                    "session_year": sy,
                    "address": f"Student address {i}",
                })
                students_objs.append(student_obj)

            # Create attendance and attendance reports for the first course and session
            attendance_date = timezone.now().date()
            attendance_obj, _ = Attendance.objects.get_or_create(course=course_cs, session_year=sy, attendance_date=attendance_date, defaults={"college": college})
            for student in students_objs:
                AttendanceReport.objects.get_or_create(student=student, attendance=attendance_obj, defaults={"status": True, "college": college})

            # Create a result for the first student
            if students_objs:
                StudentResult.objects.get_or_create(student=students_objs[0], subject_name="Mathematics", defaults={
                    "marks": 85.0,
                    "grade": "A",
                    "college": college
                })

            self.stdout.write(self.style.SUCCESS(f"Seeded demo data for college {college.name}"))

        self.stdout.write(self.style.SUCCESS("Demo seeding complete."))
