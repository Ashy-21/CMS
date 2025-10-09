from django import forms
from .models import (
    LeaveReportStaff, LeaveReportStudent, StudentResult,
    FeedbackStudent, Department, Semester
)

class LeaveForm(forms.ModelForm):
    class Meta:
        model = LeaveReportStaff
        fields = ['date', 'message']

class StudentLeaveForm(forms.ModelForm):
    class Meta:
        model = LeaveReportStudent
        fields = ['date', 'message']

class ResultForm(forms.ModelForm):
    class Meta:
        model = StudentResult
        fields = ['subject_name', 'marks', 'grade']

class ApproveLeaveForm(forms.Form):
    decision = forms.ChoiceField(choices=[('approve', 'Approve'), ('reject', 'Reject')], widget=forms.RadioSelect)

class ResultEntryForm(forms.ModelForm):
    class Meta:
        model = StudentResult
        fields = ['student', 'subject_name', 'marks', 'grade']

class StudentFeedbackForm(forms.ModelForm):
    class Meta:
        model = FeedbackStudent
        fields = ['feedback']

# Registration forms (used by registration view)
class StaffRegistrationForm(forms.Form):
    username = forms.CharField()
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    employee_id = forms.CharField(required=True)
    department = forms.ModelChoiceField(queryset=Department.objects.all(), required=True)

class StudentRegistrationForm(forms.Form):
    username = forms.CharField()
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    student_id = forms.CharField(required=True)
    roll_no = forms.CharField(required=False)
    department = forms.ModelChoiceField(queryset=Department.objects.all(), required=True)
    year = forms.ModelChoiceField(queryset=Semester.objects.all(), required=True, label="Year")
    semester = forms.ModelChoiceField(queryset=Semester.objects.all(), required=True)

class HodRegistrationForm(forms.Form):
    username = forms.CharField()
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    department = forms.ModelChoiceField(queryset=Department.objects.all(), required=True)
